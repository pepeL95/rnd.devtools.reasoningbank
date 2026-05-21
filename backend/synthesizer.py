"""Memory synthesis helpers."""

from datetime import date
from pathlib import Path

from artifacts import default_memory_path
from models import MemoryInvestigationDecision, SynthesizedMemory


def synthesize_from_decision(
    decision: MemoryInvestigationDecision,
    repo: str,
    description: str,
    body: str,
    root: Path | str,
) -> SynthesizedMemory:
    if not decision.should_create_memory:
        raise ValueError("cannot synthesize from rejected investigation decision")
    if decision.trigger is None or decision.proposed_name is None:
        raise ValueError("approved decision must include trigger and proposed_name")
    path = default_memory_path(repo, decision.proposed_name, date.today().isoformat())
    return SynthesizedMemory(
        markdown_path=str(Path(root) / path),
        repo=repo,
        name=decision.proposed_name,
        description=description,
        trigger=decision.trigger,
        tags=decision.proposed_tags,
        body=body,
        related_files=decision.related_files,
        evidence_refs=decision.evidence_refs,
        commit_refs=decision.commit_refs,
    )
