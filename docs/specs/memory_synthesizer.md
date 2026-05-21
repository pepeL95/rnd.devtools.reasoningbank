# Memory Synthesizer

## Purpose

The Memory Synthesizer turns an approved investigation decision into a markdown memory artifact. It does not decide whether a memory should exist; it only writes the candidate once the Memory Investigator has approved creation.

The synthesized memory must follow the artifact contract and remain local, concise, evidence-grounded, and useful for future agent reasoning.

## Inputs

- `MemoryInvestigationDecision` with `should_create_memory = True`.
- Task summary.
- Relevant trajectory summary.
- Relevant diff summary.
- Test or review evidence.
- Existing nearby memories for style and duplicate avoidance.

## Output

A markdown file matching `memory_artifact_contract.md`.

The output should also include parsed metadata for indexing:

```python
@dataclass
class SynthesizedMemory:
    markdown_path: str
    name: str
    description: str
    trigger: str
    tags: list[str]
    related_files: list[str]
    evidence_refs: list[str]
    commit_refs: list[str]
```

## Writing requirements

The memory body should read like a compact abstract, not a checklist.

It should include:

- The recurring pattern or risk.
- Why the pattern matters in this repo or code area.
- How the agent should adjust reasoning next time.
- Brief evidence grounding the lesson.

It should avoid:

- Raw logs.
- Verbose task chronology.
- Chain-of-thought traces.
- Overly generic advice.
- Step-by-step instructions unless the lesson is inherently procedural.

## Style target

Preferred body length: 150 to 300 words.
Maximum default body length: 500 words.

Tone:

- Clear.
- Specific.
- Evidence-grounded.
- Flowing.
- Written for a competent software engineering agent.

## Frontmatter rules

The synthesizer must produce:

```yaml
---
name: ...
description: ...
trigger: ...
tags:
  - ...
---
```

Do not include noisy implementation metadata in the frontmatter unless explicitly added to the contract later. Store file refs, commit refs, evidence refs, status, and scope in the memory index.

## Name generation

The `name` should be a brief lesson statement.

Good pattern:

```text
[code area] changes require [future reasoning adjustment]
```

Examples:

- `Auth middleware changes require route-level regression checks`
- `Pricing model edits require fixture and snapshot validation`
- `Migration generator changes can invalidate seeded test data`

## Description generation

The `description` should summarize the operational consequence.

Example:

```yaml
description: Middleware edits can silently alter route behavior despite passing isolated unit tests.
```

## Tag generation

Tags should include:

- Domain area, such as `auth`, `billing`, `migrations`.
- Artifact type, such as `middleware`, `fixtures`, `snapshots`.
- Failure mode, such as `regression`, `flaky-test`, `integration-failure`.
- Process/testing cue, such as `integration-tests`, `review-feedback`.

Use lowercase kebab-case.

## Evidence grounding

The body should briefly mention evidence, but not dump evidence.

Good:

```text
This pattern was observed after a middleware refactor passed unit tests but changed route behavior because session assumptions were encoded at the route boundary.
```

Bad:

```text
At 10:31 the agent ran command X, then command Y failed, then it tried Z...
```

## File naming

Recommended path format:

```text
.memories/local/{repo}/{yyyy-mm-dd}-{slug}.md
```

Example:

```text
.memories/local/app-api/2026-05-20-auth-middleware-route-regressions.md
```

The slug should be derived from `name` and remain stable after creation unless the Memory Gate Agent renames it.

## Validation before write

Before writing, validate that:

- Frontmatter parses as YAML.
- Required fields exist.
- Trigger is allowed.
- Tags are non-empty.
- Body is non-empty.
- Body is not too long.
- Body does not contain raw traces or chain-of-thought.

## Status after synthesis

All synthesized memories enter the system as:

```python
status = "candidate"
scope = "local"
```

The Runtime Agent must not promote, activate, archive, or delete memories directly.
