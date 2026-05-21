# Memory Store

## Purpose

The Memory Store persists memory artifacts, metadata, embeddings, evidence references, and similarity edges. It is the source of truth for retrieval and offline curation.

The markdown file is the canonical human-readable artifact. The database/index is the canonical machine-readable retrieval layer.

## Responsibilities

- Store markdown memory artifacts.
- Parse and validate frontmatter.
- Store normalized metadata.
- Store embeddings for retrieval.
- Store similarity edges.
- Track lifecycle status.
- Provide query APIs for runtime retrieval and offline review.

## Memory lifecycle

Allowed statuses:

```python
MemoryStatus = Literal["candidate", "active", "rejected", "archived"]
```

Allowed scopes:

```python
MemoryScope = Literal["local", "global"]
```

MVP runtime behavior:

- New memories are always `candidate` and `local`.
- Runtime retrieval uses `active` memories by default.
- Candidate memories are visible only to Memory Gate workflows or explicit debug modes.
- Only the Memory Gate Agent may change status or scope.

## Recommended logical data model

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass
class MemoryRecord:
    id: str
    repo: str
    scope: Literal["local", "global"]
    status: Literal["candidate", "active", "rejected", "archived"]

    markdown_path: str
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

    related_files: list[str]
    evidence_refs: list[str]
    commit_refs: list[str]
    pr_refs: list[str]

    body_hash: str
    embedding_id: str | None

    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    created_by: str
    reviewed_by: str | None
```

```python
@dataclass
class SimilarityEdgeRecord:
    from_memory_id: str
    to_memory_id: str
    score: float
    reasons: list[str]
    created_at: datetime
    updated_at: datetime
```

## Artifact storage

Recommended default:

- Store markdown files in the repo under `.memories/` for local development and review.
- Mirror/index metadata in a database for retrieval.

Path convention:

```text
.memories/local/{repo}/{yyyy-mm-dd}-{slug}.md
.memories/global/{yyyy-mm-dd}-{slug}.md
```

For MVP, runtime generation should only write to `.memories/local/{repo}/`.

## Indexing behavior

On create or update:

1. Parse frontmatter.
2. Validate contract.
3. Compute body hash.
4. Store normalized metadata.
5. Create or refresh embedding over `name + description + body`.
6. Invoke Similarity Graph Builder.

## Embedding text

Use this canonical embedding input:

```text
Name: {name}
Description: {description}
Tags: {tags}

{body}
```

Do not embed raw traces or full diffs.

## Evidence references

Evidence refs should point to external systems or durable artifacts:

- Task ids.
- Commit hashes.
- PR ids.
- CI/test run ids.
- Review comment ids.
- User correction message ids.

The store should not require evidence bodies to be embedded in memory content.

## Query APIs

Minimum APIs:

```python
def create_candidate_memory(memory: SynthesizedMemory) -> MemoryRecord: ...

def get_memory(memory_id: str) -> MemoryRecord: ...

def get_memory_body(memory_id: str) -> str: ...

def search_memories(
    repo: str,
    query: str,
    files: list[str],
    tags: list[str],
    statuses: list[str] = ["active"],
    limit: int = 10,
) -> list[MemoryRecord]: ...

def update_status(memory_id: str, status: str, reviewed_by: str) -> None: ...

def update_scope(memory_id: str, scope: str, reviewed_by: str) -> None: ...
```

## Invariants

- Every record must point to a valid markdown artifact.
- Every active memory must have a valid embedding.
- Every edge must reference existing memories.
- Edge scores must be in `[0.0, 1.0]`.
- Runtime agents may create candidates but must not activate them.
