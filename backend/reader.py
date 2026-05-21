"""Memory body activation."""

from models import MemoryReadRequest, MemoryReadResult
from store import SQLiteMemoryStore


class MemoryReader:
    def __init__(self, store: SQLiteMemoryStore) -> None:
        self.store = store

    def read(self, request: MemoryReadRequest) -> MemoryReadResult:
        record = self.store.get_memory(request.memory_id)
        warnings = []
        if record.repo != request.repo and record.scope != "global":
            warnings.append("memory belongs to a different repo")
        if record.status == "candidate":
            warnings.append("candidate memory; debug/gate use only")
        if record.status in {"rejected", "archived"}:
            raise ValueError("cannot read %s memory during runtime" % record.status)

        body = None
        if request.detail_level == "body":
            if not request.activation_reason.strip():
                raise ValueError("activation_reason is required for body reads")
            body = self.store.get_memory_body(record.id)
            self.store.log_activation(
                record.id,
                request.task_id,
                request.repo,
                request.activation_reason,
            )

        return MemoryReadResult(
            memory_id=record.id,
            name=record.name,
            description=record.description,
            tags=record.tags,
            body=body,
            warnings=warnings,
        )
