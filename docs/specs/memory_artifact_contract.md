# Memory Artifact Contract

## Purpose

A memory artifact is the canonical unit of learned reasoning. It is stored as a markdown file with YAML frontmatter. The frontmatter is the discovery and retrieval interface. The markdown body is the activated memory content.

Runtime agents should initially interface only with frontmatter and retrieval metadata. The body should be read only after the agent intentionally activates the memory.

## Required markdown format

```markdown
---
name: [brief, substantiated title for the memory]
description: [short description of the memory]
trigger: [user_correction | manual_trigger | learning | failure_analysis | review_feedback]
tags:
  - [tag]
  - [tag]
---

[flowing, concise memory content]
```

## Required frontmatter fields

### `name`

A short, specific title that states the learned insight.

Requirements:

- Must be human-readable.
- Must be specific enough to distinguish this memory from nearby memories.
- Should describe the reasoning lesson, not merely the task.
- Should avoid generic titles such as `Testing lesson` or `Bug fix memory`.

Good:

```yaml
name: Auth middleware changes require route-level regression checks
```

Bad:

```yaml
name: Remember auth stuff
```

### `description`

A one-sentence summary used for retrieval and initial agent inspection.

Requirements:

- Should capture the practical consequence of the memory.
- Should be understandable without reading the body.
- Should not include implementation details better suited for the body.

Example:

```yaml
description: Middleware edits can silently alter route behavior despite passing isolated unit tests.
```

### `trigger`

The event type that caused the memory to be proposed.

Allowed values:

```python
Trigger = Literal[
    "user_correction",
    "manual_trigger",
    "learning",
    "failure_analysis",
    "review_feedback",
]
```

Definitions:

- `user_correction`: user corrected the agent or clarified an expected behavior.
- `manual_trigger`: human explicitly requested a memory candidate.
- `learning`: agent or system identified a reusable lesson from a successful or partially successful task.
- `failure_analysis`: postmortem or failed trajectory produced a reusable lesson.
- `review_feedback`: code review, CI review, or evaluator feedback produced the lesson.

### `tags`

A compact set of retrieval tags.

Requirements:

- 3 to 8 tags is preferred.
- Use lowercase kebab-case.
- Include domain tags, failure mode tags, and testing/process tags when relevant.
- Avoid overly broad tags unless useful for retrieval.

Examples:

```yaml
tags:
  - auth
  - middleware
  - regression
  - integration-tests
```

## Optional metadata outside the markdown file

The markdown artifact should stay simple. Implementation-specific metadata should be stored in the memory index, not necessarily in the markdown frontmatter.

Recommended index metadata:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass
class MemoryRecord:
    id: str
    repo: str
    path: str
    name: str
    description: str
    trigger: Literal[
        "user_correction",
        "manual_trigger",
        "learning",
        "failure_analysis",
        "review_feedback",
    ]
    tags: list[str]
    status: Literal["candidate", "active", "rejected", "archived"]
    scope: Literal["local", "global"]
    related_files: list[str]
    evidence_refs: list[str]
    commit_refs: list[str]
    pr_refs: list[str]
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
```

For MVP, all runtime-generated memories should use:

```python
scope = "local"
status = "candidate"
```

Only the Memory Gate Agent may change `status` or promote `scope` to `global`.

## Body style

The body should be a concise, abstract-style reasoning note.

It should not be a rigid checklist unless the lesson is inherently procedural. Prefer coherent paragraphs that explain:

1. The pattern.
2. Why it matters.
3. How future reasoning should adjust.
4. What concrete evidence grounded the lesson.

The body should be rich enough to change agent behavior but short enough to read quickly.

Target length:

- Preferred: 150 to 300 words.
- Hard maximum for MVP: 500 words unless manually approved.

## Body content requirements

Every body should answer the following implicitly or explicitly:

- When does this memory apply?
- What reasoning mistake, risk, or useful pattern does it capture?
- How should the agent adjust its future behavior?
- What evidence grounds the memory?

## Example

```markdown
---
name: Auth middleware changes require route-level regression checks
description: Middleware edits can silently alter route behavior despite passing isolated unit tests.
trigger: learning
tags:
  - auth
  - middleware
  - regression
  - integration-tests
---

Changes to authentication middleware often appear localized, but their real impact emerges at the route level, where authorization decisions are actually enforced. In practice, this means that even well-covered unit tests can miss regressions introduced by subtle shifts in request handling or session validation.

When working in this area, reasoning should expand outward from the modified code to its callsites. Routes depending on the middleware should be treated as the true surface of correctness, and both accepted and rejected request paths should be validated. This typically requires leaning on integration or route-level tests rather than relying solely on isolated function coverage.

This pattern was observed in a case where middleware refactoring passed all unit tests but altered downstream route behavior due to implicit assumptions in session handling. The key signal is any change that affects control flow or request context, even if the change seems internal.

In general, treat middleware as infrastructure whose correctness is defined by its effects, not its implementation.
```

## Validation rules

A memory artifact is invalid if:

- Required frontmatter is missing.
- `trigger` is not one of the allowed values.
- `tags` is empty.
- Body is empty.
- Body is merely a task summary.
- Body contains raw chain-of-thought or unnecessary trajectory logs.
- Body gives ungrounded advice without evidence.

## Privacy and trace handling

Memory bodies should synthesize conclusions, not preserve raw traces. Store trace references in metadata and evidence systems. Avoid copying full logs, private reasoning traces, or noisy tool transcripts into the artifact.
