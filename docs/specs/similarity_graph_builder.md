# Similarity Graph Builder

## Purpose

The Similarity Graph Builder links memories to nearby memories using a single weighted similarity score. The graph is intentionally simple: edges mean “these memories are meaningfully related.”

The MVP does not use typed semantic edges. There is no `supports`, `contradicts`, `specializes`, or `supersedes` edge type in runtime graph construction.

## Edge model

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SimilarityEdge:
    from_memory_id: str
    to_memory_id: str
    score: float
    reasons: list[str]
    created_at: datetime
    updated_at: datetime
```

Edges should be treated as undirected for retrieval unless implementation simplicity favors storing both directions.

## Similarity function

Use the following blended score:

```python
similarity = (
    0.45 * semantic_similarity
    + 0.25 * file_overlap
    + 0.15 * commit_proximity
    + 0.10 * tag_overlap
    + 0.05 * temporal_proximity
)
```

Do not include symbol overlap in the MVP.

## Signals

### Semantic similarity

Embedding similarity between memory texts.

Embedding input:

```text
Name: {name}
Description: {description}
Tags: {tags}

{body}
```

Normalize to `[0.0, 1.0]`.

### File overlap

Primary locality signal.

Base overlap:

```python
file_overlap = len(files_a & files_b) / len(files_a | files_b)
```

If there is no exact file overlap, compute weaker locality tiers:

- Same file: strong.
- Same directory: medium.
- Same package/root: weak.
- No relationship: zero.

Recommended mapping:

```python
same_exact_file = 1.0
same_directory = 0.6
same_package_or_root = 0.3
none = 0.0
```

When multiple files are present, use the maximum of exact overlap score and locality tier score.

### Commit proximity

Commit context captures memories learned from the same engineering event.

Recommended mapping:

```python
same_commit = 1.0
same_pr_or_branch = 0.7
adjacent_commits = 0.5
same_week_same_repo = 0.2
none = 0.0
```

`adjacent_commits` means commits close in the repo history, ideally within the same branch or PR context. If commit graph access is unavailable, skip adjacent-commit scoring and rely on PR/time signals.

### Tag overlap

Use Jaccard similarity over tags:

```python
tag_overlap = len(tags_a & tags_b) / len(tags_a | tags_b)
```

Tags should be normalized to lowercase kebab-case before comparison.

### Temporal proximity

Weak clustering signal based on creation time.

Recommended mapping:

```python
same_day = 1.0
within_7_days = 0.6
within_30_days = 0.3
older = 0.0
```

Temporal proximity should never dominate. It exists only to cluster related investigations.

## Edge creation process

When a new memory is created or updated:

1. Compute or refresh its embedding.
2. Retrieve top-K candidate memories by semantic similarity.
3. Add candidates with file, tag, commit, or temporal overlap even if semantic similarity is moderate.
4. Compute blended score for all candidates.
5. Keep top N edges.
6. Store reasons for each edge.

Recommended defaults:

```python
candidate_k = 20
max_edges_per_memory = 5
min_edge_score = 0.55
```

If fewer than 3 edges exceed the threshold, keep only those above threshold. Do not force weak edges.

## Reason generation

Each edge should include short reasons based on the largest contributing signals.

Examples:

```python
[
    "high semantic similarity",
    "shared tags: auth, regression",
    "same directory: src/routes/",
    "created in same commit",
]
```

Reason strings are for debugging, review, and trust. They should not be used as the source of truth for scoring.

## Edge refresh

Edges should be recomputed when:

- A memory is created.
- A memory body or frontmatter changes.
- Related files, commit refs, or tags change.
- A memory status changes to `active`.
- Offline graph maintenance is run.

## Candidate and inactive memories

The graph may store edges for candidate memories. Runtime retrieval should ignore candidate memories unless explicitly enabled.

When a candidate becomes active, its edges should be refreshed because the active memory pool may have changed.

## Hotspot and density signals

The graph builder should compute these as derived metadata, not explicit edge types.

### File hotspot

A file is a hotspot if it appears in many active memories.

Use this to boost retrieval, not edge creation, unless the file also contributes to file overlap.

### Memory density

A memory cluster is dense if many active memories are connected by high-scoring edges in the same repo area.

Use this to signal risk and boost retrieval of clusters. Keep implementation simple for MVP: count active memories within one graph hop above a chosen threshold.

## Non-goals

The MVP graph builder should not:

- Create typed edges.
- Infer contradictions.
- Track symbols.
- Perform deep static analysis.
- Rewrite memories.
- Decide whether memories are active.
