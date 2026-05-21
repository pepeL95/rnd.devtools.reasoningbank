# Memory Reader

## Purpose

The Memory Reader controls progressive disclosure. It lets the runtime agent inspect memory previews first, then intentionally activate selected memory bodies.

This protects the agent from unnecessary details while still making rich memory content available when relevant.

## Inputs

- Memory id.
- Retrieval context.
- Activation reason from the runtime agent.
- Optional requested detail level.

```python
@dataclass
class MemoryReadRequest:
    memory_id: str
    repo: str
    activation_reason: str
    detail_level: Literal["summary", "body"] = "body"
```

## Outputs

```python
@dataclass
class MemoryReadResult:
    memory_id: str
    name: str
    description: str
    tags: list[str]
    body: str | None
    warnings: list[str]
```

## Progressive disclosure policy

### Default view

The agent initially sees only:

- `name`
- `description`
- `trigger`
- `tags`
- retrieval reasons

### Activated view

The agent can read the full markdown body when it has a concrete activation reason, such as:

- It is editing a file covered by the memory.
- The task text matches the memory description.
- A retrieved cluster suggests a hotspot.
- Tests or failures resemble the memory.

## Activation logging

Every body read should be logged.

```python
@dataclass
class MemoryActivationEvent:
    memory_id: str
    task_id: str
    repo: str
    activation_reason: str
    activated_at: datetime
    used_in_final_plan: bool | None
```

This data helps later evaluation and Memory Gate decisions.

## Warnings

The reader should warn when:

- The memory is stale.
- The memory is candidate-only and debug mode is enabled.
- The memory is archived or rejected.
- The memory belongs to a different repo.
- The memory has weak evidence.

Default runtime behavior should block rejected or archived memories.

## Content constraints

The reader should return the body exactly as stored, except for optional rendering or section extraction. Do not summarize or rewrite the body during read, because the markdown artifact is the reviewed source of truth.

## Non-goals

The Memory Reader should not:

- Retrieve memories.
- Create memories.
- Edit memories.
- Promote or demote memories.
- Infer new graph edges.
