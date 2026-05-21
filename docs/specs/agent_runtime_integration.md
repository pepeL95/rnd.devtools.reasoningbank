# Agent Runtime Integration

## Purpose

This document defines how the AI software engineer agent should use the ReasoningBank MVP during normal coding tasks.

The runtime loop is local-first, retrieval-driven, and conservative about creating memories.

## Runtime phases

```text
Task starts
  ↓
Build retrieval context
  ↓
Retrieve memory previews
  ↓
Agent selectively activates relevant memories
  ↓
Agent performs task
  ↓
Trajectory is summarized
  ↓
Memory Investigator decides whether to propose candidate
  ↓
Memory Synthesizer writes candidate if approved
  ↓
Store indexes candidate and graph edges
```

## Task start

At the beginning of a task, build a `RetrievalContext` from:

- User request.
- Repo name.
- Files mentioned by the user.
- Files opened by the agent.
- Failing tests, if known.
- Current branch, PR, or commit metadata, if known.
- Lightweight inferred tags.

## Memory preview injection

The agent should receive a compact memory preview section before planning.

Example:

```text
Potentially relevant memories:

1. Auth middleware changes require route-level regression checks
   Middleware edits can silently alter route behavior despite passing isolated unit tests.
   Reason: same repo, same directory, high semantic similarity.

2. Route tests encode implicit session assumptions
   Auth-related route tests may depend on seeded session fixtures not visible in middleware unit tests.
   Reason: graph neighbor, shared tags auth/regression.
```

Do not inject full bodies automatically by default.

## Memory activation

The agent may activate a memory when it is materially relevant to its plan.

Acceptable activation reasons:

- “I am editing a file covered by this memory.”
- “The current failure mode matches this memory.”
- “This memory is in a dense hotspot cluster for the files I am changing.”
- “The task requires reasoning about the same domain and risk.”

The agent should not activate every retrieved memory.

## During task execution

Activated memories should be treated as advisory context, not instructions that override code or tests.

Priority order:

1. Current user instruction.
2. Current repo code and tests.
3. Active project documentation.
4. Activated memories.
5. General model knowledge.

If a memory conflicts with current code evidence, the agent should trust the current code and optionally flag the memory for gate review.

## Post-task memory proposal

After task completion, generate a trajectory summary suitable for investigation. The summary should include:

- What changed.
- What files were involved.
- What failed or surprised the agent.
- What tests or review feedback mattered.
- Whether any user correction occurred.
- Whether an activated memory helped or misled.

The Runtime Agent must not directly create an active memory. It may only pass data to the Memory Investigator.

## Candidate creation

If the Memory Investigator approves creation, the Memory Synthesizer writes a candidate artifact.

The candidate is stored with:

```python
status = "candidate"
scope = "local"
```

The candidate is not available to normal runtime retrieval until the Memory Gate Agent approves it.

## Failure and correction handling

User corrections are high-value memory signals but still require investigation. A user correction should not automatically become a memory unless it is reusable and repo-grounded.

When a memory misleads the agent:

- Log the activation.
- Include the failure in the trajectory summary.
- Suggest Memory Gate review.

## Non-goals

Runtime integration should not:

- Promote memories to global.
- Activate candidate memories by default.
- Edit existing memories.
- Delete memories.
- Overload prompts with full memory bodies.
