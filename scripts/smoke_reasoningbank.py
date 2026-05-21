#!/usr/bin/env python3
"""Offline smoke test for the flat backend implementation."""

import hashlib
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from gate import MemoryGate
from graph import SimilarityGraphBuilder
from models import MemoryReadRequest, RetrievalContext, SynthesizedMemory
from reader import MemoryReader
from retriever import MemoryRetriever
from store import SQLiteMemoryStore
from vector import ChromaMemoryIndex


class SmokeEmbeddings:
    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text):
        vector = [0.0] * 32
        for token in text.lower().replace("/", " ").replace("-", " ").split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[digest[0] % len(vector)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def main() -> int:
    root = ROOT / ".smoke_reasoningbank"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()

    vector = ChromaMemoryIndex(str(root / "chroma"), SmokeEmbeddings())
    store = SQLiteMemoryStore(root, vector)
    graph = SimilarityGraphBuilder(store)
    gate = MemoryGate(store, graph)

    first = store.create_candidate_memory(
        SynthesizedMemory(
            markdown_path=str(root / ".memories/local/app-api/2026-05-20-auth-route-regressions.md"),
            repo="app-api",
            name="Auth middleware changes require route-level regression checks",
            description="Middleware edits can silently alter route behavior despite passing isolated unit tests.",
            trigger="learning",
            tags=["auth", "middleware", "regression", "integration-tests"],
            related_files=["src/auth/middleware.ts", "src/routes/session.ts"],
            evidence_refs=["smoke-task-1"],
            body=(
                "Changes to authentication middleware often appear localized, but their real impact emerges "
                "at route boundaries where authorization decisions are enforced. Future work in this area "
                "should reason outward from middleware internals to accepted and rejected route behavior. "
                "This smoke memory is grounded by a synthetic task reference and validates the candidate, "
                "gate, retrieval, and reader flow without storing noisy execution details."
            ),
        )
    )

    candidate_results = MemoryRetriever(store).retrieve(
        RetrievalContext(
            repo="app-api",
            task_text="change auth middleware route behavior",
            files_in_scope=["src/auth/middleware.ts"],
            tags=["auth"],
        )
    )
    assert candidate_results == [], "candidate memories leaked into default retrieval"

    gate.approve(first.id)

    second = store.create_candidate_memory(
        SynthesizedMemory(
            markdown_path=str(root / ".memories/local/app-api/2026-05-20-session-fixtures.md"),
            repo="app-api",
            name="Session fixture edits require route authorization checks",
            description="Session fixture changes can alter auth route assumptions across integration paths.",
            trigger="learning",
            tags=["auth", "fixtures", "regression", "integration-tests"],
            related_files=["src/routes/session.ts", "tests/session-fixtures.ts"],
            evidence_refs=["smoke-task-2"],
            body=(
                "Session fixtures are part of the behavior surface for authorization flows because routes "
                "may encode assumptions that are not visible in isolated fixture builders. When changing "
                "fixtures around authenticated sessions, future reasoning should include route-level accepted "
                "and rejected paths. This smoke memory exists to validate graph linking for related active "
                "memories without preserving command-by-command task chronology."
            ),
        )
    )
    gate.approve(second.id)
    edges = graph.refresh_for_memory(second.id)
    assert edges, "expected at least one similarity edge"

    active_results = MemoryRetriever(store).retrieve(
        RetrievalContext(
            repo="app-api",
            task_text="modify auth middleware and session route tests",
            files_in_scope=["src/auth/middleware.ts"],
            tags=["auth", "integration-tests"],
        )
    )
    assert active_results, "expected active retrieval results"

    read = MemoryReader(store).read(
        MemoryReadRequest(
            memory_id=active_results[0].memory_id,
            repo="app-api",
            activation_reason="smoke test is editing a covered auth route file",
            task_id="smoke",
        )
    )
    assert read.body, "expected activated body"

    print("smoke ok")
    print("retrieved:", ", ".join(item.memory_id for item in active_results))
    print("edges:", len(edges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
