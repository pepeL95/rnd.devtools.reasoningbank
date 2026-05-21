"""ReasoningBank CLI."""

import argparse
import sys
from pathlib import Path

from gate import MemoryGate
from graph import SimilarityGraphBuilder
from llm import gemini_embeddings
from models import MemoryReadRequest, RetrievalContext
from reader import MemoryReader
from retriever import MemoryRetriever
from store import SQLiteMemoryStore
from vector import ChromaMemoryIndex


def build_store(root: Path) -> SQLiteMemoryStore:
    embeddings = gemini_embeddings()
    vector_index = ChromaMemoryIndex(str(root / "chroma"), embeddings)
    return SQLiteMemoryStore(root, vector_index)


def cmd_validate(args: argparse.Namespace) -> int:
    from artifacts import parse_markdown_file, validate_artifact

    failures = 0
    for path in Path(args.path).rglob("*.md"):
        try:
            parsed = parse_markdown_file(path)
            validate_artifact(parsed.frontmatter, parsed.body)
            print("valid %s" % path)
        except Exception as exc:
            failures += 1
            print("invalid %s: %s" % (path, exc), file=sys.stderr)
    return 1 if failures else 0


def cmd_index(args: argparse.Namespace) -> int:
    store = build_store(Path(args.root))
    record = store.index_existing_artifact(args.path, repo=args.repo, status=args.status, scope=args.scope)
    print(record.id)
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    store = build_store(Path(args.root))
    previews = MemoryRetriever(store).retrieve(
        RetrievalContext(
            repo=args.repo,
            task_text=args.task,
            files_in_scope=args.files or [],
            tags=args.tags or [],
            include_candidate_memories=args.include_candidates,
        )
    )
    for preview in previews:
        print("%s\t%.4f\t%s" % (preview.memory_id, preview.relevance_score, preview.name))
        print("  %s" % preview.description)
        print("  reason: %s" % ", ".join(preview.reasons))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    store = build_store(Path(args.root))
    result = MemoryReader(store).read(
        MemoryReadRequest(
            memory_id=args.memory_id,
            repo=args.repo,
            activation_reason=args.reason,
            detail_level=args.detail,
            task_id=args.task_id,
        )
    )
    print(result.name)
    print(result.description)
    if result.warnings:
        print("warnings: %s" % ", ".join(result.warnings))
    if result.body:
        print()
        print(result.body)
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    store = build_store(Path(args.root))
    graph = SimilarityGraphBuilder(store)
    gate = MemoryGate(store, graph)
    action = getattr(gate, args.action)
    action(args.memory_id, reviewed_by=args.reviewed_by)
    print("%s %s" % (args.action, args.memory_id))
    return 0


def cmd_graph_refresh(args: argparse.Namespace) -> int:
    store = build_store(Path(args.root))
    edges = SimilarityGraphBuilder(store).refresh_for_memory(args.memory_id)
    for edge in edges:
        print("%s -> %s %.4f" % (edge.from_memory_id, edge.to_memory_id, edge.score))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="reasoningbank")
    root.add_argument("--root", default=".reasoningbank", help="store root")
    sub = root.add_subparsers(dest="cmd", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)

    index = sub.add_parser("index")
    index.add_argument("path")
    index.add_argument("--repo", required=True)
    index.add_argument("--status", default="candidate")
    index.add_argument("--scope", default="local")
    index.set_defaults(func=cmd_index)

    retrieve = sub.add_parser("retrieve")
    retrieve.add_argument("--repo", required=True)
    retrieve.add_argument("--task", required=True)
    retrieve.add_argument("--files", nargs="*")
    retrieve.add_argument("--tags", nargs="*")
    retrieve.add_argument("--include-candidates", action="store_true")
    retrieve.set_defaults(func=cmd_retrieve)

    read = sub.add_parser("read")
    read.add_argument("memory_id")
    read.add_argument("--repo", required=True)
    read.add_argument("--reason", required=True)
    read.add_argument("--detail", default="body", choices=["summary", "body"])
    read.add_argument("--task-id", default="manual")
    read.set_defaults(func=cmd_read)

    gate = sub.add_parser("gate")
    gate.add_argument("action", choices=["approve", "reject", "archive", "promote_to_global", "demote_to_local"])
    gate.add_argument("memory_id")
    gate.add_argument("--reviewed-by", default="memory-gate")
    gate.set_defaults(func=cmd_gate)

    graph = sub.add_parser("graph-refresh")
    graph.add_argument("memory_id")
    graph.set_defaults(func=cmd_graph_refresh)

    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
