#!/usr/bin/env python3
"""Live smoke test for Gemini embeddings plus Chroma retrieval.

Requires GOOGLE_API_KEY in the environment.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from gate import MemoryGate
from graph import SimilarityGraphBuilder
from llm import gemini_embeddings
from models import MemoryReadRequest, RetrievalContext, SynthesizedMemory
from reader import MemoryReader
from retriever import MemoryRetriever
from store import SQLiteMemoryStore
from vector import ChromaMemoryIndex


def main() -> int:
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY is required", file=sys.stderr)
        return 2

    root = ROOT / ".live_gemini_smoke"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()

    vector = ChromaMemoryIndex(str(root / "chroma"), gemini_embeddings())
    store = SQLiteMemoryStore(root, vector)
    graph = SimilarityGraphBuilder(store)
    gate = MemoryGate(store, graph)

    record = store.create_candidate_memory(
        SynthesizedMemory(
            markdown_path=str(root / ".memories/local/app-api/2026-05-20-live-gemini-auth.md"),
            repo="app-api",
            name="Auth middleware edits require route-level validation",
            description="Auth middleware changes should be checked through route behavior, not only local implementation review.",
            trigger="learning",
            tags=["auth", "middleware", "regression", "integration-tests"],
            related_files=["src/auth/middleware.ts", "src/routes/session.ts"],
            evidence_refs=["live-gemini-smoke"],
            body=(
                "Authentication middleware affects correctness through the routes that consume its decisions. "
                "When modifying this area, future reasoning should include route-level accepted and rejected "
                "paths, because isolated middleware inspection can miss assumptions encoded at the session "
                "or authorization boundary. This live smoke memory validates that Gemini embeddings can index "
                "and retrieve a concrete memory through Chroma."
            ),
        )
    )
    gate.approve(record.id)

    results = MemoryRetriever(store).retrieve(
        RetrievalContext(
            repo="app-api",
            task_text="change auth middleware and verify route authorization behavior",
            files_in_scope=["src/auth/middleware.ts"],
            tags=["auth", "integration-tests"],
        )
    )
    if not results:
        print("no retrieval results", file=sys.stderr)
        return 1

    read = MemoryReader(store).read(
        MemoryReadRequest(
            memory_id=results[0].memory_id,
            repo="app-api",
            activation_reason="live smoke is verifying Gemini-backed retrieval",
            task_id="live-gemini-smoke",
        )
    )
    if not read.body:
        print("body activation failed", file=sys.stderr)
        return 1

    print("live gemini smoke ok")
    print("top memory:", results[0].memory_id, results[0].name)
    print("score:", results[0].relevance_score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
