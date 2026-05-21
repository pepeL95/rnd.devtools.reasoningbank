"""SQLite-backed memory store."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from artifacts import body_hash, embedding_text, memory_id_for_path, parse_markdown_file, render_markdown
from models import ALLOWED_SCOPES, ALLOWED_STATUSES, MemoryRecord, SimilarityEdgeRecord, SynthesizedMemory
from vector import ChromaMemoryIndex


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def dt_to_text(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def dt_from_text(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def encode_list(values: Iterable[str]) -> str:
    return json.dumps(list(values), separators=(",", ":"))


def decode_list(value: str) -> List[str]:
    data = json.loads(value or "[]")
    return [str(item) for item in data]


class SQLiteMemoryStore:
    def __init__(self, root: Path | str, vector_index: ChromaMemoryIndex) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "reasoningbank.sqlite3"
        self.vector_index = vector_index
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.migrate()

    def migrate(self) -> None:
        self.conn.executescript(
            """
            create table if not exists memories (
              id text primary key,
              repo text not null,
              scope text not null,
              status text not null,
              markdown_path text not null unique,
              name text not null,
              description text not null,
              trigger text not null,
              tags_json text not null,
              related_files_json text not null,
              evidence_refs_json text not null,
              commit_refs_json text not null,
              pr_refs_json text not null,
              body_hash text not null,
              embedding_id text,
              created_at text not null,
              updated_at text not null,
              reviewed_at text,
              created_by text not null,
              reviewed_by text
            );

            create table if not exists similarity_edges (
              from_memory_id text not null,
              to_memory_id text not null,
              score real not null,
              reasons_json text not null,
              created_at text not null,
              updated_at text not null,
              primary key (from_memory_id, to_memory_id)
            );

            create table if not exists activation_events (
              id integer primary key autoincrement,
              memory_id text not null,
              task_id text not null,
              repo text not null,
              activation_reason text not null,
              activated_at text not null,
              used_in_final_plan integer
            );
            """
        )
        self.conn.commit()

    def create_candidate_memory(self, memory: SynthesizedMemory) -> MemoryRecord:
        artifact_path = Path(memory.markdown_path)
        if not artifact_path.is_absolute():
            artifact_path = artifact_path.resolve()
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_text = render_markdown(
            memory.name,
            memory.description,
            memory.trigger,
            memory.tags,
            memory.body,
        )
        artifact_path.write_text(artifact_text, encoding="utf-8")
        parsed = parse_markdown_file(artifact_path)
        now = utcnow()
        stored_path = str(artifact_path)
        memory_id = memory_id_for_path(stored_path)
        record = MemoryRecord(
            id=memory_id,
            repo=memory.repo,
            scope="local",
            status="candidate",
            markdown_path=stored_path,
            name=str(parsed.frontmatter["name"]),
            description=str(parsed.frontmatter["description"]),
            trigger=parsed.frontmatter["trigger"],
            tags=[str(tag) for tag in parsed.frontmatter["tags"]],
            related_files=memory.related_files,
            evidence_refs=memory.evidence_refs,
            commit_refs=memory.commit_refs,
            pr_refs=memory.pr_refs,
            body_hash=body_hash(parsed.body),
            embedding_id=memory_id,
            created_at=now,
            updated_at=now,
            reviewed_at=None,
            created_by=memory.created_by,
            reviewed_by=None,
        )
        self._upsert_record(record)
        self._index_record(record, parsed.body)
        return record

    def index_existing_artifact(
        self,
        path: Path | str,
        repo: str,
        status: str = "candidate",
        scope: str = "local",
        created_by: str = "import",
    ) -> MemoryRecord:
        if status not in ALLOWED_STATUSES:
            raise ValueError("invalid status: %s" % status)
        if scope not in ALLOWED_SCOPES:
            raise ValueError("invalid scope: %s" % scope)
        artifact_path = Path(path)
        if not artifact_path.is_absolute():
            artifact_path = artifact_path.resolve()
        parsed = parse_markdown_file(artifact_path)
        now = utcnow()
        stored_path = str(artifact_path)
        record = MemoryRecord(
            id=memory_id_for_path(stored_path),
            repo=repo,
            scope=scope,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            markdown_path=stored_path,
            name=str(parsed.frontmatter["name"]),
            description=str(parsed.frontmatter["description"]),
            trigger=parsed.frontmatter["trigger"],
            tags=[str(tag) for tag in parsed.frontmatter["tags"]],
            related_files=[],
            evidence_refs=[],
            commit_refs=[],
            pr_refs=[],
            body_hash=body_hash(parsed.body),
            embedding_id=memory_id_for_path(stored_path),
            created_at=now,
            updated_at=now,
            reviewed_at=now if status != "candidate" else None,
            created_by=created_by,
            reviewed_by=created_by if status != "candidate" else None,
        )
        self._upsert_record(record)
        self._index_record(record, parsed.body)
        return record

    def get_memory(self, memory_id: str) -> MemoryRecord:
        row = self.conn.execute("select * from memories where id = ?", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return self._row_to_record(row)

    def get_memory_body(self, memory_id: str) -> str:
        record = self.get_memory(memory_id)
        parsed = parse_markdown_file(self._artifact_path(record.markdown_path))
        return parsed.body

    def list_memories(
        self,
        repo: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> List[MemoryRecord]:
        query = "select * from memories"
        clauses = []
        params: List[str] = []
        if repo:
            clauses.append("(repo = ? or scope = 'global')")
            params.append(repo)
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            clauses.append("status in (%s)" % placeholders)
            params.extend(statuses)
        if clauses:
            query += " where " + " and ".join(clauses)
        query += " order by updated_at desc"
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def update_status(self, memory_id: str, status: str, reviewed_by: str) -> None:
        if status not in ALLOWED_STATUSES:
            raise ValueError("invalid status: %s" % status)
        now = utcnow()
        self.conn.execute(
            """
            update memories
            set status = ?, reviewed_at = ?, reviewed_by = ?, updated_at = ?
            where id = ?
            """,
            (status, dt_to_text(now), reviewed_by, dt_to_text(now), memory_id),
        )
        self.conn.commit()

    def update_scope(self, memory_id: str, scope: str, reviewed_by: str) -> None:
        if scope not in ALLOWED_SCOPES:
            raise ValueError("invalid scope: %s" % scope)
        now = utcnow()
        self.conn.execute(
            """
            update memories
            set scope = ?, reviewed_at = ?, reviewed_by = ?, updated_at = ?
            where id = ?
            """,
            (scope, dt_to_text(now), reviewed_by, dt_to_text(now), memory_id),
        )
        self.conn.commit()

    def upsert_edge(self, edge: SimilarityEdgeRecord) -> None:
        self.conn.execute(
            """
            insert into similarity_edges (
              from_memory_id, to_memory_id, score, reasons_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?)
            on conflict(from_memory_id, to_memory_id) do update set
              score = excluded.score,
              reasons_json = excluded.reasons_json,
              updated_at = excluded.updated_at
            """,
            (
                edge.from_memory_id,
                edge.to_memory_id,
                edge.score,
                encode_list(edge.reasons),
                dt_to_text(edge.created_at),
                dt_to_text(edge.updated_at),
            ),
        )
        self.conn.commit()

    def delete_edges_for(self, memory_id: str) -> None:
        self.conn.execute(
            "delete from similarity_edges where from_memory_id = ? or to_memory_id = ?",
            (memory_id, memory_id),
        )
        self.conn.commit()

    def edges_for(self, memory_id: str, min_score: float = 0.0) -> List[SimilarityEdgeRecord]:
        rows = self.conn.execute(
            """
            select * from similarity_edges
            where (from_memory_id = ? or to_memory_id = ?) and score >= ?
            order by score desc
            """,
            (memory_id, memory_id, min_score),
        ).fetchall()
        return [self._row_to_edge(row) for row in rows]

    def log_activation(self, memory_id: str, task_id: str, repo: str, activation_reason: str) -> None:
        self.conn.execute(
            """
            insert into activation_events(memory_id, task_id, repo, activation_reason, activated_at)
            values (?, ?, ?, ?, ?)
            """,
            (memory_id, task_id, repo, activation_reason, dt_to_text(utcnow())),
        )
        self.conn.commit()

    def _upsert_record(self, record: MemoryRecord) -> None:
        self.conn.execute(
            """
            insert into memories (
              id, repo, scope, status, markdown_path, name, description, trigger,
              tags_json, related_files_json, evidence_refs_json, commit_refs_json,
              pr_refs_json, body_hash, embedding_id, created_at, updated_at,
              reviewed_at, created_by, reviewed_by
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
              repo = excluded.repo,
              scope = excluded.scope,
              status = excluded.status,
              markdown_path = excluded.markdown_path,
              name = excluded.name,
              description = excluded.description,
              trigger = excluded.trigger,
              tags_json = excluded.tags_json,
              related_files_json = excluded.related_files_json,
              evidence_refs_json = excluded.evidence_refs_json,
              commit_refs_json = excluded.commit_refs_json,
              pr_refs_json = excluded.pr_refs_json,
              body_hash = excluded.body_hash,
              embedding_id = excluded.embedding_id,
              updated_at = excluded.updated_at,
              reviewed_at = excluded.reviewed_at,
              reviewed_by = excluded.reviewed_by
            """,
            (
                record.id,
                record.repo,
                record.scope,
                record.status,
                record.markdown_path,
                record.name,
                record.description,
                record.trigger,
                encode_list(record.tags),
                encode_list(record.related_files),
                encode_list(record.evidence_refs),
                encode_list(record.commit_refs),
                encode_list(record.pr_refs),
                record.body_hash,
                record.embedding_id,
                dt_to_text(record.created_at),
                dt_to_text(record.updated_at),
                dt_to_text(record.reviewed_at),
                record.created_by,
                record.reviewed_by,
            ),
        )
        self.conn.commit()

    def _index_record(self, record: MemoryRecord, body: str) -> None:
        text = embedding_text(record.name, record.description, record.tags, body)
        self.vector_index.upsert(
            record.id,
            text,
            {
                "repo": record.repo,
                "scope": record.scope,
                "status": record.status,
                "tags": ",".join(record.tags),
            },
        )

    def _artifact_path(self, stored_path: str) -> Path:
        path = Path(stored_path)
        if path.is_absolute():
            return path
        return self.root / path

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            repo=row["repo"],
            scope=row["scope"],
            status=row["status"],
            markdown_path=row["markdown_path"],
            name=row["name"],
            description=row["description"],
            trigger=row["trigger"],
            tags=decode_list(row["tags_json"]),
            related_files=decode_list(row["related_files_json"]),
            evidence_refs=decode_list(row["evidence_refs_json"]),
            commit_refs=decode_list(row["commit_refs_json"]),
            pr_refs=decode_list(row["pr_refs_json"]),
            body_hash=row["body_hash"],
            embedding_id=row["embedding_id"],
            created_at=dt_from_text(row["created_at"]) or utcnow(),
            updated_at=dt_from_text(row["updated_at"]) or utcnow(),
            reviewed_at=dt_from_text(row["reviewed_at"]),
            created_by=row["created_by"],
            reviewed_by=row["reviewed_by"],
        )

    def _row_to_edge(self, row: sqlite3.Row) -> SimilarityEdgeRecord:
        return SimilarityEdgeRecord(
            from_memory_id=row["from_memory_id"],
            to_memory_id=row["to_memory_id"],
            score=float(row["score"]),
            reasons=decode_list(row["reasons_json"]),
            created_at=dt_from_text(row["created_at"]) or utcnow(),
            updated_at=dt_from_text(row["updated_at"]) or utcnow(),
        )
