"""Similarity graph builder."""

import os
from datetime import datetime
from typing import List, Sequence, Set, Tuple

from models import MemoryRecord, SimilarityEdgeRecord
from store import SQLiteMemoryStore, utcnow


def jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a = set(left)
    b = set(right)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def file_overlap(left: Sequence[str], right: Sequence[str]) -> float:
    a = set(left)
    b = set(right)
    if not a or not b:
        return 0.0
    exact = len(a & b) / len(a | b)
    tier = 0.0
    for lhs in a:
        for rhs in b:
            if lhs == rhs:
                tier = max(tier, 1.0)
            elif os.path.dirname(lhs) and os.path.dirname(lhs) == os.path.dirname(rhs):
                tier = max(tier, 0.6)
            elif lhs.split("/", 1)[0] == rhs.split("/", 1)[0]:
                tier = max(tier, 0.3)
    return max(exact, tier)


def commit_proximity(left: MemoryRecord, right: MemoryRecord) -> float:
    if set(left.commit_refs) & set(right.commit_refs):
        return 1.0
    if set(left.pr_refs) & set(right.pr_refs):
        return 0.7
    delta = abs((left.created_at - right.created_at).days)
    if delta <= 7 and left.repo == right.repo:
        return 0.2
    return 0.0


def temporal_proximity(left: datetime, right: datetime) -> float:
    delta = abs((left - right).days)
    if delta == 0:
        return 1.0
    if delta <= 7:
        return 0.6
    if delta <= 30:
        return 0.3
    return 0.0


def edge_reasons(
    semantic_similarity: float,
    files: float,
    commits: float,
    tags: Set[str],
    temporal: float,
) -> List[str]:
    reasons: List[str] = []
    if semantic_similarity >= 0.75:
        reasons.append("high semantic similarity")
    if files >= 1.0:
        reasons.append("same file")
    elif files >= 0.6:
        reasons.append("same directory")
    elif files >= 0.3:
        reasons.append("same package or root")
    if commits >= 1.0:
        reasons.append("same commit")
    elif commits >= 0.7:
        reasons.append("same pr")
    if tags:
        reasons.append("shared tags: %s" % ", ".join(sorted(tags)))
    if temporal >= 1.0:
        reasons.append("created same day")
    return reasons[:4]


class SimilarityGraphBuilder:
    def __init__(
        self,
        store: SQLiteMemoryStore,
        min_edge_score: float = 0.55,
        max_edges_per_memory: int = 5,
    ) -> None:
        self.store = store
        self.min_edge_score = min_edge_score
        self.max_edges_per_memory = max_edges_per_memory

    def refresh_for_memory(self, memory_id: str) -> List[SimilarityEdgeRecord]:
        anchor = self.store.get_memory(memory_id)
        body = self.store.get_memory_body(memory_id)
        query_text = "Name: %s\nDescription: %s\nTags: %s\n\n%s" % (
            anchor.name,
            anchor.description,
            ", ".join(anchor.tags),
            body,
        )
        vector_rows = self.store.vector_index.query(query_text, limit=20)
        by_id = {row["memory_id"]: row for row in vector_rows}
        candidates = [
            record
            for record in self.store.list_memories(repo=anchor.repo, statuses=["active", "candidate"])
            if record.id != anchor.id
        ]
        scored: List[Tuple[float, SimilarityEdgeRecord]] = []
        now = utcnow()
        for candidate in candidates:
            semantic = float(by_id.get(candidate.id, {}).get("similarity", 0.0))
            files = file_overlap(anchor.related_files, candidate.related_files)
            commits = commit_proximity(anchor, candidate)
            tags = jaccard(anchor.tags, candidate.tags)
            temporal = temporal_proximity(anchor.created_at, candidate.created_at)
            score = (
                0.45 * semantic
                + 0.25 * files
                + 0.15 * commits
                + 0.10 * tags
                + 0.05 * temporal
            )
            shared_tags = set(anchor.tags) & set(candidate.tags)
            reasons = edge_reasons(semantic, files, commits, shared_tags, temporal)
            if score >= self.min_edge_score:
                edge = SimilarityEdgeRecord(
                    from_memory_id=anchor.id,
                    to_memory_id=candidate.id,
                    score=round(score, 4),
                    reasons=reasons,
                    created_at=now,
                    updated_at=now,
                )
                scored.append((score, edge))

        self.store.delete_edges_for(anchor.id)
        edges = [edge for _, edge in sorted(scored, key=lambda item: item[0], reverse=True)]
        for edge in edges[: self.max_edges_per_memory]:
            self.store.upsert_edge(edge)
        return edges[: self.max_edges_per_memory]
