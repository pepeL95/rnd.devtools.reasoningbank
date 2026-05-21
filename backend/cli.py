"""ReasoningBank CLI."""

import argparse
import sys
from pathlib import Path

from config import (
    config_path_for,
    default_local_config_values,
    discover_config,
    global_config_path,
    resolve_settings,
    write_config,
)
from gate import MemoryGate
from graph import SimilarityGraphBuilder
from llm import gemini_embeddings
from models import MemoryReadRequest, RetrievalContext
from reader import MemoryReader
from retriever import MemoryRetriever
from store import SQLiteMemoryStore
from vector import ChromaMemoryIndex


class RichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Keep command examples readable in help output."""


def build_store(root: Path) -> SQLiteMemoryStore:
    embeddings = gemini_embeddings()
    vector_index = ChromaMemoryIndex(str(root / "chroma"), embeddings)
    return SQLiteMemoryStore(root, vector_index)


def bootstrap_store(root: Path) -> SQLiteMemoryStore:
    vector_index = ChromaMemoryIndex(str(root / "chroma"), embeddings=None)
    return SQLiteMemoryStore(root, vector_index)


def effective_settings(args: argparse.Namespace) -> object:
    return resolve_settings(Path.cwd(), getattr(args, "root", None), getattr(args, "repo", None))


def cmd_init(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    local_root, local_repo_path = default_local_config_values(cwd)
    root = (cwd / local_root).resolve()
    bootstrap_store(root)
    config_path = config_path_for(cwd)
    if not config_path.exists():
        write_config(config_path, root=local_root, repo_path=local_repo_path)
        print("wrote %s" % config_path)
    print("initialized %s" % root)
    return 0


def config_target_path(use_global: bool) -> Path:
    if use_global:
        return global_config_path()
    existing = discover_config(Path.cwd())
    if existing and existing.path != global_config_path():
        return existing.path
    return config_path_for(Path.cwd())


def interactive_config(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    existing = discover_config(Path.cwd())
    target_default = "global" if existing and existing.path == global_config_path() else "local"
    scope = input("Config scope [local/global] (%s): " % target_default).strip().lower() or target_default
    use_global = scope == "global"
    target = config_target_path(use_global)
    local_root, local_repo_path = default_local_config_values(cwd)
    default_root = (
        str(existing.root) if existing and existing.path == target and existing.root else local_root
    )
    default_repo_path = (
        str(existing.repo_path)
        if existing and existing.path == target and existing.repo_path
        else local_repo_path
    )
    root_value = input("Root path [%s]: " % default_root).strip() or default_root
    repo_path_value = input("Repo path [%s]: " % default_repo_path).strip() or default_repo_path
    write_config(target, root=root_value, repo_path=repo_path_value)
    print("wrote %s" % target)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if not args.show and args.root is None and args.repo_path is None:
        return interactive_config(args)

    if args.show:
        existing = discover_config(Path.cwd())
        if existing is None:
            print("source: <none>")
            print("root: <unset>")
            print("repo_path: <unset>")
            print("repo_name: <unset>")
            print("hint: run `reasoningbank init` or `reasoningbank config` to create a local default")
            return 0
        current = resolve_settings(Path.cwd(), None, None, require_config=False)
        print("source: %s" % current.source)
        print("root: %s" % current.root)
        print("repo_path: %s" % current.repo_path)
        print("repo_name: %s" % current.repo_name)
        return 0

    target = config_target_path(args.global_config)
    existing = discover_config(Path.cwd())
    root_value = args.root
    repo_path_value = args.repo_path
    local_root, local_repo_path = default_local_config_values(Path.cwd())
    if existing and existing.path == target:
        if root_value is None:
            root_value = existing.root or local_root
        if repo_path_value is None:
            repo_path_value = existing.repo_path or local_repo_path
    else:
        if root_value is None:
            root_value = local_root
        if repo_path_value is None:
            repo_path_value = local_repo_path
    write_config(target, root=root_value, repo_path=repo_path_value)
    print("wrote %s" % target)
    return 0


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
    settings = effective_settings(args)
    store = build_store(settings.root)
    record = store.index_existing_artifact(args.path, repo=settings.repo_name, status=args.status, scope=args.scope)
    print(record.id)
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    settings = effective_settings(args)
    store = build_store(settings.root)
    previews = MemoryRetriever(store).retrieve(
        RetrievalContext(
            repo=settings.repo_name,
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
    settings = effective_settings(args)
    store = build_store(settings.root)
    result = MemoryReader(store).read(
        MemoryReadRequest(
            memory_id=args.memory_id,
            repo=settings.repo_name,
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
    settings = effective_settings(args)
    store = build_store(settings.root)
    graph = SimilarityGraphBuilder(store)
    gate = MemoryGate(store, graph)
    action = getattr(gate, args.action)
    action(args.memory_id, reviewed_by=args.reviewed_by)
    print("%s %s" % (args.action, args.memory_id))
    return 0


def cmd_graph_refresh(args: argparse.Namespace) -> int:
    settings = effective_settings(args)
    store = build_store(settings.root)
    edges = SimilarityGraphBuilder(store).refresh_for_memory(args.memory_id)
    for edge in edges:
        print("%s -> %s %.4f" % (edge.from_memory_id, edge.to_memory_id, edge.score))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="reasoningbank",
        description=(
            "ReasoningBank manages markdown memory artifacts, their local index, "
            "runtime retrieval, and offline gate decisions."
        ),
        epilog=(
            "Core flow:\n"
            "  1. init a local store, which also writes a local .reasoningbankconfig\n"
            "  2. validate or index artifacts into the local store\n"
            "  3. retrieve previews for a repo task\n"
            "  4. read a memory body only when it is relevant\n"
            "  5. use gate actions to approve, reject, archive, or promote memories\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    root.add_argument(
        "--root",
        default=None,
        help="Override the resolved store root for this invocation.",
    )
    root.add_argument(
        "--repo",
        default=None,
        help="Override the resolved repo path for this invocation. The repo name is inferred from the path basename.",
    )
    sub = root.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser(
        "init",
        help="Bootstrap a .reasoningbank store in the current working directory.",
        description=(
            "Create a store rooted at ./ .reasoningbank in the current working directory, "
            "including SQLite state, a persistent Chroma directory, and a coupled "
            "local .reasoningbankconfig."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank init\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    init.set_defaults(func=cmd_init)

    config = sub.add_parser(
        "config",
        help="Set or inspect hierarchical defaults for root and repo path.",
        description=(
            "Read or write .reasoningbankconfig files. Resolution walks upward from "
            "the current directory to the filesystem root, then falls back to ~/.reasoningbankconfig. "
            "Store-backed commands take their default root and repo path from the nearest discovered config."
        ),
        epilog=(
            "Examples:\n"
            "  reasoningbank config --show\n"
            "  reasoningbank config --root .reasoningbank --repo-path /path/to/repo\n"
            "  reasoningbank config --global --root ~/.reasoningbank/work --repo-path ~/src/app-api\n\n"
            "If you run `reasoningbank config` with no parameters, it starts an interactive setup shell.\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    config.add_argument(
        "--show",
        action="store_true",
        help="Print the currently resolved effective configuration.",
    )
    config.add_argument(
        "--root",
        dest="root",
        default=None,
        help="Root path to store in the config file.",
    )
    config.add_argument(
        "--repo-path",
        default=None,
        help="Repo path to store in the config file. The repo name is derived from its basename.",
    )
    config.add_argument(
        "--global",
        dest="global_config",
        action="store_true",
        help="Write ~/.reasoningbankconfig instead of a local .reasoningbankconfig.",
    )
    config.set_defaults(func=cmd_config)

    validate = sub.add_parser(
        "validate",
        help="Validate markdown memory artifacts without indexing them.",
        description=(
            "Walk a directory of markdown files, parse YAML frontmatter, and enforce "
            "the memory artifact contract. This does not write to SQLite or Chroma."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank validate .memories/\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    validate.add_argument(
        "path",
        help="Directory to scan recursively for .md memory artifacts.",
    )
    validate.set_defaults(func=cmd_validate)

    index = sub.add_parser(
        "index",
        help="Index one artifact into SQLite and Chroma.",
        description=(
            "Read a single markdown artifact, validate it, assign repo/status/scope "
            "metadata, persist it to SQLite, and embed it into Chroma for retrieval."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank index .memories/local/app-api/2026-05-20-auth.md --status active\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    index.add_argument(
        "path",
        help="Path to one markdown artifact to index.",
    )
    index.add_argument(
        "--status",
        default="candidate",
        choices=["candidate", "active", "rejected", "archived"],
        help="Lifecycle status to store with the artifact. Default: %(default)s",
    )
    index.add_argument(
        "--scope",
        default="local",
        choices=["local", "global"],
        help="Retrieval scope for the artifact. Default: %(default)s",
    )
    index.set_defaults(func=cmd_index)

    retrieve = sub.add_parser(
        "retrieve",
        help="Retrieve compact memory previews for a task.",
        description=(
            "Build a retrieval context from repo, task text, files, and tags; run "
            "vector search plus graph expansion; and return preview-only results."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank retrieve --task \"modify auth middleware\" \\\n"
            "    --files src/auth/middleware.ts src/routes/session.ts --tags auth integration-tests\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    retrieve.add_argument(
        "--task",
        required=True,
        help="Natural-language task description used for semantic retrieval.",
    )
    retrieve.add_argument(
        "--files",
        nargs="*",
        help="Files currently in scope for the task. File locality boosts relevant memories.",
    )
    retrieve.add_argument(
        "--tags",
        nargs="*",
        help="Explicit retrieval tags, such as auth, regression, or integration-tests.",
    )
    retrieve.add_argument(
        "--include-candidates",
        action="store_true",
        help="Include candidate memories for debugging or gate workflows. Runtime use should normally omit this.",
    )
    retrieve.set_defaults(func=cmd_retrieve)

    read = sub.add_parser(
        "read",
        help="Read a specific memory, optionally activating its body.",
        description=(
            "Load one indexed memory by id. Summary mode returns metadata only; "
            "body mode logs an activation event and returns the stored markdown body."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank read mem_abc123 --reason \"editing covered auth files\"\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    read.add_argument(
        "memory_id",
        help="Indexed memory id, such as mem_abc123.",
    )
    read.add_argument(
        "--reason",
        required=True,
        help="Concrete activation reason. Required because body reads are intentional, not automatic.",
    )
    read.add_argument(
        "--detail",
        default="body",
        choices=["summary", "body"],
        help="Read only metadata or the full body. Default: %(default)s",
    )
    read.add_argument(
        "--task-id",
        default="manual",
        help="Task identifier stored with the activation log. Default: %(default)s",
    )
    read.set_defaults(func=cmd_read)

    gate = sub.add_parser(
        "gate",
        help="Apply an offline Memory Gate lifecycle action.",
        description=(
            "Change lifecycle or scope for one indexed memory. Approve and promote "
            "actions also refresh similarity edges for the affected memory."
        ),
        epilog=(
            "Actions:\n"
            "  approve            make a candidate retrievable at runtime\n"
            "  reject             mark a candidate as rejected\n"
            "  archive            retire an active memory\n"
            "  promote_to_global  widen retrieval scope beyond one repo\n"
            "  demote_to_local    narrow a global memory back to one repo\n\n"
            "Example:\n"
            "  reasoningbank gate approve mem_abc123 --reviewed-by memory-gate\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    gate.add_argument(
        "action",
        choices=["approve", "reject", "archive", "promote_to_global", "demote_to_local"],
        help="Lifecycle action to apply.",
    )
    gate.add_argument(
        "memory_id",
        help="Indexed memory id to update.",
    )
    gate.add_argument(
        "--reviewed-by",
        default="memory-gate",
        help="Reviewer label recorded with the gate action. Default: %(default)s",
    )
    gate.set_defaults(func=cmd_gate)

    graph = sub.add_parser(
        "graph-refresh",
        help="Recompute similarity edges for one memory.",
        description=(
            "Run the similarity graph builder for a specific memory and print the "
            "resulting one-hop edges with scores."
        ),
        epilog=(
            "Example:\n"
            "  reasoningbank graph-refresh mem_abc123\n"
        ),
        formatter_class=RichHelpFormatter,
    )
    graph.add_argument(
        "memory_id",
        help="Indexed memory id whose graph edges should be rebuilt.",
    )
    graph.set_defaults(func=cmd_graph_refresh)

    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
