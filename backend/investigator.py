"""Conservative deterministic investigation pre-gate."""

from models import MemoryInvestigationDecision


def investigate_manual(
    proposed_name: str,
    trigger: str,
    tags: list[str],
    related_files: list[str],
    evidence_refs: list[str],
    rationale: str,
    commit_refs: list[str] | None = None,
) -> MemoryInvestigationDecision:
    should_create = bool(proposed_name.strip() and tags and evidence_refs and rationale.strip())
    return MemoryInvestigationDecision(
        should_create_memory=should_create,
        trigger=trigger if should_create else None,  # type: ignore[arg-type]
        proposed_name=proposed_name if should_create else None,
        proposed_tags=tags,
        related_files=related_files,
        evidence_refs=evidence_refs,
        commit_refs=commit_refs or [],
        rationale=rationale,
        duplicate_of=None,
        confidence="medium" if should_create else "low",
    )
