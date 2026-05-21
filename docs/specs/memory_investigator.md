# Memory Investigator

## Purpose

The Memory Investigator decides whether a completed agent trajectory deserves a memory candidate. It prevents the system from blindly generating memory artifacts after every task.

The investigator is a gate before synthesis, not a curator of existing memories. It produces a decision and rationale. If approved, the Memory Synthesizer writes the artifact.

## Inputs

The investigator receives:

- Task request.
- Agent trajectory summary.
- Final outcome.
- Files touched.
- Commits, diffs, or patches created.
- Test results and failures.
- User corrections.
- Review feedback.
- Existing nearby memories retrieved by metadata and embedding.

## Output

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class MemoryInvestigationDecision:
    should_create_memory: bool
    trigger: Literal[
        "user_correction",
        "manual_trigger",
        "learning",
        "failure_analysis",
        "review_feedback",
    ] | None
    proposed_name: str | None
    proposed_tags: list[str]
    related_files: list[str]
    evidence_refs: list[str]
    commit_refs: list[str]
    rationale: str
    duplicate_of: str | None
    confidence: Literal["low", "medium", "high"]
```

## Creation criteria

Create a memory candidate only when all of the following are true:

1. The lesson is likely to recur in the same repo or code area.
2. The lesson is not obvious generic software engineering advice.
3. The lesson is grounded in concrete evidence.
4. The lesson would change future agent behavior.
5. The lesson can be expressed concisely.
6. The lesson is not already covered by an active memory.

## Rejection criteria

Do not create a memory when:

- The issue was a one-off task detail.
- The lesson is generic, such as “run tests before submitting”.
- Evidence is weak, ambiguous, or speculative.
- The trajectory was noisy but did not produce a reusable insight.
- Existing active memory already covers the lesson.
- The candidate would merely summarize what happened.
- The candidate would encode project policy that should live in docs instead.

## Duplicate detection

Before approving synthesis, retrieve nearby memories using:

- Similar task text.
- Same repo.
- Overlapping touched files.
- Shared tags.
- Embedding similarity over existing frontmatter and bodies.

If a nearby memory already captures the lesson, return:

```python
should_create_memory = False
duplicate_of = "existing_memory_id"
```

The investigator may optionally recommend that the Memory Gate Agent strengthen or update the existing memory offline.

## Trigger assignment

Use the most specific trigger available:

- User explicitly corrected behavior: `user_correction`.
- Human asked to create memory: `manual_trigger`.
- Failed or regressed task produced the insight: `failure_analysis`.
- Review or CI feedback produced the insight: `review_feedback`.
- Successful or partially successful trajectory revealed a reusable pattern: `learning`.

## Evidence requirements

Every approved candidate must include at least one evidence reference.

Useful evidence:

- Task id.
- Commit hash.
- PR id.
- Diff reference.
- Test run id.
- Failing test name.
- User correction message id.
- Review comment id.

The memory body should summarize evidence; raw evidence should remain referenced externally.

## Investigation prompt shape

The implementation may use an LLM, deterministic rules, or both. The decision prompt should force the investigator to answer:

1. What reusable lesson, if any, was learned?
2. Is the lesson repo-local rather than global?
3. Is this already covered by an existing memory?
4. What concrete evidence supports it?
5. How would it change future agent behavior?
6. Should a memory be created?

## Acceptance criteria

The investigator is working well when:

- Fewer than 20% of completed tasks produce memory candidates.
- Most candidates survive offline Memory Gate review.
- Rejected cases have clear rationale.
- Duplicate memory creation is rare.
- Candidate memories are grounded in evidence, not vibes.
