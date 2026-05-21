"""Offline Memory Gate operations."""

from graph import SimilarityGraphBuilder
from store import SQLiteMemoryStore


class MemoryGate:
    def __init__(self, store: SQLiteMemoryStore, graph: SimilarityGraphBuilder) -> None:
        self.store = store
        self.graph = graph

    def approve(self, memory_id: str, reviewed_by: str = "memory-gate") -> None:
        self.store.update_status(memory_id, "active", reviewed_by)
        self.graph.refresh_for_memory(memory_id)

    def reject(self, memory_id: str, reviewed_by: str = "memory-gate") -> None:
        self.store.update_status(memory_id, "rejected", reviewed_by)

    def archive(self, memory_id: str, reviewed_by: str = "memory-gate") -> None:
        self.store.update_status(memory_id, "archived", reviewed_by)

    def promote_to_global(self, memory_id: str, reviewed_by: str = "memory-gate") -> None:
        self.store.update_scope(memory_id, "global", reviewed_by)
        self.graph.refresh_for_memory(memory_id)

    def demote_to_local(self, memory_id: str, reviewed_by: str = "memory-gate") -> None:
        self.store.update_scope(memory_id, "local", reviewed_by)
        self.graph.refresh_for_memory(memory_id)
