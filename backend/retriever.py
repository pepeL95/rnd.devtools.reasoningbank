"""Runtime retrieval with preview-only output."""

import os
from typing import Dict, List

from graph import file_overlap, jaccard
from models import RetrievalContext, RetrievedMemoryPreview
from store import SQLiteMemoryStore


def query_text(context: RetrievalContext) -> str:
    return "Task: %s\nRepo: %s\nFiles: %s\nTags: %s" % (
        context.task_text,
        context.repo,
        ", ".join(context.files_in_scope + context.changed_files),
        ", ".join(context.tags),
    )


def status_pool(context: RetrievalContext) -> List[str]:
    if context.include_candidate_memories:
        return ["active", "candidate"]
    return ["active"]


def activation_hint(record_files: List[str], task_files: List[str]) -> str:
    if file_overlap(record_files, task_files) > 0:
        return "Read if editing files covered by this memory."
    return "Read if the task risk matches this memory."


class MemoryRetriever:
    def __init__(self, store: SQLiteMemoryStore) -> None:
        self.store = store

    def retrieve(self, context: RetrievalContext, final_limit: int = 5) -> List[RetrievedMemoryPreview]:
        task_files = context.files_in_scope + context.changed_files
        vector_rows = self.store.vector_index.query(
            query_text(context),
            limit=10,
            where={"repo": context.repo},
        )
        vector_scores: Dict[str, float] = {
            row["memory_id"]: float(row["similarity"]) for row in vector_rows
        }
        records = self.store.list_memories(repo=context.repo, statuses=status_pool(context))
        previews: Dict[str, RetrievedMemoryPreview] = {}

        for record in records:
            semantic = vector_scores.get(record.id, 0.0)
            files = file_overlap(record.related_files, task_files)
            tags = jaccard(record.tags, context.tags)
            recency = 0.1
            score = 0.50 * semantic + 0.25 * files + 0.15 * tags + 0.10 * recency
            if score <= 0 and not (set(record.tags) & set(context.tags)):
                continue
            reasons = []
            if semantic > 0:
                reasons.append("semantic match")
            if files > 0:
                reasons.append("file locality")
            if tags > 0:
                reasons.append("shared tags")
            previews[record.id] = RetrievedMemoryPreview(
                memory_id=record.id,
                name=record.name,
                description=record.description,
                trigger=record.trigger,
                tags=record.tags,
                relevance_score=round(score, 4),
                reasons=reasons or ["metadata match"],
                activation_hint=activation_hint(record.related_files, task_files),
            )

        base_ids = [
            preview.memory_id
            for preview in sorted(previews.values(), key=lambda item: item.relevance_score, reverse=True)[:5]
        ]
        for base_id in base_ids:
            base = previews[base_id]
            for edge in self.store.edges_for(base_id, min_score=0.55):
                neighbor_id = edge.to_memory_id if edge.from_memory_id == base_id else edge.from_memory_id
                if neighbor_id in previews:
                    continue
                neighbor = self.store.get_memory(neighbor_id)
                if neighbor.status not in status_pool(context):
                    continue
                locality = file_overlap(neighbor.related_files, task_files)
                score = 0.65 * base.relevance_score + 0.35 * edge.score + 0.05 * locality
                previews[neighbor.id] = RetrievedMemoryPreview(
                    memory_id=neighbor.id,
                    name=neighbor.name,
                    description=neighbor.description,
                    trigger=neighbor.trigger,
                    tags=neighbor.tags,
                    relevance_score=round(score, 4),
                    reasons=["graph neighbor"] + edge.reasons[:2],
                    activation_hint=activation_hint(neighbor.related_files, task_files),
                )

        return sorted(previews.values(), key=lambda item: item.relevance_score, reverse=True)[:final_limit]
