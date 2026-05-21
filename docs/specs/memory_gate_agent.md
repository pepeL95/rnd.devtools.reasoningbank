# Memory Gate Agent

## Purpose

The Memory Gate Agent is the offline curator of the memory system. It reviews candidate memories and graph health outside the runtime coding flow.

Runtime agents may propose candidate local memories. The Memory Gate Agent decides what becomes active, rejected, archived, merged, rewritten, or promoted.

## Responsibilities

- Review candidate memories.
- Approve or reject candidates.
- Edit memory artifacts for clarity and specificity.
- Merge duplicate memories.
- Archive stale or misleading memories.
- Promote local memories to global memories when appropriate.
- Demote or narrow over-broad memories.
- Review similarity graph quality.
- Maintain tag hygiene.

## Inputs

- Candidate memories.
- Existing active memories.
- Similarity edges and reasons.
- Evidence references.
- Activation logs.
- Outcome data from tasks that used memories.
- User or reviewer feedback.

## Output actions

```python
GateAction = Literal[
    "approve",
    "reject",
    "edit",
    "merge",
    "archive",
    "promote_to_global",
    "demote_to_local",
    "retag",
    "refresh_edges",
]
```

## Candidate review criteria

Approve a candidate when:

- The lesson is specific and reusable.
- Evidence is concrete.
- The body is concise and flowy.
- It is not duplicative.
- It would have improved future agent behavior.
- It is correctly scoped as local.

Reject a candidate when:

- It is generic advice.
- It merely summarizes a task.
- Evidence is weak.
- It duplicates an active memory.
- It encourages brittle or outdated behavior.
- It should be documentation rather than agent memory.

## Promotion to global

Promotion is always offline. It is never part of the runtime task loop.

Promote a local memory to global only when:

- The lesson has appeared across multiple repos or projects.
- The repo-specific details can be removed without losing value.
- The memory describes a broadly useful engineering reasoning pattern.
- A human or gate policy confirms it should be available cross-repo.

Promotion should usually produce a new global memory artifact rather than mutating the local memory in place.

## Demotion and archival

Archive memories when:

- They are stale due to codebase changes.
- They are superseded by new repo behavior.
- They repeatedly fail to help.
- They are activated frequently but not useful.

Demote global memories when:

- They turn out to be repo-specific.
- They cause irrelevant retrieval in other repos.
- Their lesson depends on assumptions not broadly true.

## Merge policy

Merge candidates or active memories when they express the same lesson with overlapping evidence.

Merge should preserve:

- The clearest title.
- The best description.
- The strongest evidence refs.
- The most useful tags.
- The most concise body.

After merge, archive or reject the redundant memory and refresh graph edges.

## Graph hygiene

The gate agent should review graph quality periodically.

Look for:

- Edge spam.
- Weak edges above threshold.
- Isolated active memories that should have links.
- Clusters of duplicates.
- Overly broad memories linked to everything.

The gate agent may tune thresholds, remove weak edges, or trigger edge recomputation.

## Review cadence

Recommended MVP cadence:

- Review new candidates daily or per development batch.
- Review graph quality weekly.
- Review global promotions manually and explicitly.

## Acceptance criteria

The Memory Gate Agent is effective when:

- Most active memories are useful at retrieval time.
- Duplicate memories are rare.
- Global memories are few and high quality.
- Candidate backlog does not grow without review.
- Retrieval noise remains low as memory count grows.
