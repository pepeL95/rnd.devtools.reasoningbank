# Memory Retriever

## Purpose

The Memory Retriever provides relevant memories to the AI software engineer agent at task time. It should retrieve a small, high-signal set of active memories, then expand one hop through the similarity graph.

The retriever should expose only frontmatter and summaries by default. Full body access is handled by the Memory Reader.

## Inputs

```python
@dataclass
class RetrievalContext:
    repo: str
    task_text: str
    files_in_scope: list[str]
    changed_files: list[str]
    tags: list[str]
    commit_refs: list[str]
    pr_refs: list[str]
    include_candidate_memories: bool = False
```

`files_in_scope` may include files mentioned by the task, files opened by the agent, failing test files, and files changed so far.

## Output

```python
@dataclass
class RetrievedMemoryPreview:
    memory_id: str
    name: str
    description: str
    trigger: str
    tags: list[str]
    relevance_score: float
    reasons: list[str]
    activation_hint: str
```

The preview must not include the full memory body.

## Retrieval pipeline

1. Filter memory pool.
2. Compute base relevance.
3. Select top base memories.
4. Expand one hop through similarity graph.
5. Re-rank combined set.
6. Return compact previews.

## Memory pool filtering

Default runtime pool:

```python
status = "active"
scope in ["local", "global"]
```

For MVP, local memories should dominate. Global memories exist only if the Memory Gate Agent has manually promoted them.

Candidate memories are excluded unless `include_candidate_memories = True`.

## Base relevance score

Recommended base score:

```python
base_relevance = (
    0.50 * task_semantic_similarity
    + 0.25 * file_relevance
    + 0.15 * tag_relevance
    + 0.10 * recency_or_activity_signal
)
```

### Task semantic similarity

Embedding similarity between task context and memory embedding.

Task embedding input:

```text
Task: {task_text}
Repo: {repo}
Files: {files_in_scope}
Tags: {tags}
```

### File relevance

Use the same file locality heuristics as the graph builder:

- Same file: strong.
- Same directory: medium.
- Same package/root: weak.
- No relationship: zero.

### Tag relevance

Jaccard similarity between task tags and memory tags.

If explicit task tags are unavailable, infer lightweight tags from task text and file paths.

### Recency or activity signal

Small signal to avoid stale memories. This should not overpower locality or semantic relevance.

Possible inputs:

- Recently active memory.
- Memory previously useful in similar context.
- Memory updated by gate agent recently.

## Graph expansion

After selecting top base memories:

1. Fetch one-hop neighbors via similarity edges.
2. Keep neighbors with edge score above threshold.
3. Combine base relevance and edge score.

Recommended neighbor score:

```python
neighbor_relevance = (
    0.65 * base_anchor_relevance
    + 0.35 * edge_score
)
```

If the neighbor also has file overlap with current task, apply a small locality boost.

## Ranking policy

Return a small set.

Recommended defaults:

```python
base_limit = 5
neighbor_limit = 5
final_limit = 5
```

The final set should be diverse. Avoid returning several nearly identical memories unless they form a clear hotspot cluster.

## Hotspot and density boosts

### File hotspot boost

If current files appear in many active memories, boost memories touching those files. Also surface an activation hint such as:

```text
This file appears in several active memories; inspect related memories before editing.
```

### Memory density boost

If multiple retrieved memories are connected in the same local graph cluster, boost the cluster slightly and include only the most representative memories.

## Preview format

A preview should be compact:

```text
Name: Auth middleware changes require route-level regression checks
Description: Middleware edits can silently alter route behavior despite passing isolated unit tests.
Tags: auth, middleware, regression, integration-tests
Reason: same repo, same directory, high semantic similarity
Activation hint: Read if modifying auth middleware or route authorization behavior.
```

## Runtime behavior

The coding agent should receive previews first. It may request full body activation for specific memory ids through the Memory Reader.

Do not inject full memory bodies automatically unless:

- There is a very high confidence match.
- The body is short.
- The task is safety-critical for that code area.

Even then, prefer explicit activation to reduce noise.

## Non-goals

The retriever should not:

- Generate new memories.
- Change memory status.
- Promote memories.
- Read raw trajectories.
- Perform offline curation.
