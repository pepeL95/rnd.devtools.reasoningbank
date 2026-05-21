# Evaluation

## Purpose

Evaluation ensures the ReasoningBank MVP improves agent behavior without creating noisy, stale, or misleading memories.

The system should be evaluated at three levels:

1. Memory artifact quality.
2. Retrieval quality.
3. Task outcome impact.

## Memory artifact quality

Review candidate and active memories for:

- Specificity.
- Evidence grounding.
- Concision.
- Reusability.
- Correct scope.
- Non-duplication.
- Flowing abstract-style body.

## Artifact quality rubric

Score each memory from 1 to 5 on:

### Specificity

- 1: Generic advice.
- 3: Some repo or domain specificity.
- 5: Clearly tied to a recurring repo-local pattern.

### Evidence grounding

- 1: No concrete evidence.
- 3: Mentions a task or failure.
- 5: Clear evidence refs and concise synthesis of what happened.

### Behavioral usefulness

- 1: Would not change future behavior.
- 3: Might influence planning.
- 5: Clearly changes how the agent should reason.

### Concision

- 1: Too verbose or trace-like.
- 3: Understandable but could be tighter.
- 5: Compact, abstract-like, and complete.

### Scope correctness

- 1: Wrongly global or overly broad.
- 3: Mostly scoped correctly.
- 5: Clearly local or intentionally global.

## Retrieval quality metrics

Track:

- Precision@K: how many retrieved memories are actually useful.
- Activation rate: how often previews are activated.
- Useful activation rate: how often activated memories helped.
- Noise rate: how often retrieved memories were irrelevant.
- Miss rate: how often a useful memory existed but was not retrieved.
- Candidate leakage rate: candidates shown during normal runtime. Should be zero.

Recommended MVP targets:

```text
Precision@5 >= 0.60
Useful activation rate >= 0.50
Candidate leakage rate = 0
Duplicate candidate rate <= 0.15
```

These are starting targets, not hard product requirements.

## Task outcome impact

Measure whether memory improves engineering tasks.

Useful metrics:

- Reduced repeated mistakes.
- Fewer regressions in remembered areas.
- Faster convergence on correct files/tests.
- Better test selection.
- Higher reviewer acceptance.
- Fewer user corrections for previously learned issues.

## A/B evaluation

For selected tasks, compare:

- Agent without memory.
- Agent with memory previews only.
- Agent with preview plus selective body activation.

Measure:

- Final correctness.
- Number of tool calls.
- Test success.
- Reviewer feedback.
- Whether the agent used relevant memories appropriately.

## Memory creation quality

Track investigator performance:

- Candidate creation rate per completed task.
- Gate approval rate.
- Gate rejection reasons.
- Duplicate detection success.
- Average artifact quality score.

A healthy MVP should not create memories for most tasks. Memory candidates should feel earned.

## Graph quality

Track:

- Average edges per memory.
- Isolated active memories.
- Edge precision from sampled reviews.
- Retrieval lift from graph expansion.
- Number of weak/noisy edge reasons.

Recommended defaults:

```text
Average edges per memory: 1 to 5
Max edges per memory: 5
Graph expansion should improve recall without materially hurting precision.
```

## Human review workflow

The Memory Gate Agent or human reviewer should periodically sample:

- Recently created candidates.
- Recently activated active memories.
- Memories with low usefulness.
- Dense clusters.
- Memories frequently retrieved but rarely activated.

## Failure modes to watch

- Memory spam: too many candidates.
- Generic memories: advice that belongs in general coding guidelines.
- Retrieval bloat: too many previews shown.
- Stale memories: repo changed but memory remains active.
- Over-local memories: lessons tied to one obsolete task.
- Over-global memories: local assumptions promoted too broadly.
- Graph noise: weak edges causing irrelevant expansion.

## Launch acceptance criteria

Before enabling broadly, the MVP should demonstrate:

- Valid markdown artifacts are created consistently.
- Candidate memories remain hidden from runtime retrieval.
- Gate agent can approve/reject/edit/promote offline.
- Active memories can be retrieved by repo, task text, files, and tags.
- Similarity graph expansion works one hop.
- Memory body activation is explicit and logged.
- At least one repeated issue is improved by an active memory.
