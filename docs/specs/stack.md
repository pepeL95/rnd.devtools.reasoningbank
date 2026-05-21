# Recommended Tech Stack

## Goals

The stack should support:

- Markdown-native memory artifacts.
- YAML frontmatter parsing and validation.
- Python implementation.
- Vector retrieval over memory content.
- Simple similarity graph retrieval.
- Offline Memory Gate workflows.
- Local-first development with a clean path to production.
- Langchain for genai work (use gemini models for llm-related work - standby for api key to trigger when done implementing -- same applies to embedding models)

## Language

Use Python for the implementation.

Recommended baseline:

```text
Python 3.12+
```

Useful libraries:

- `pydantic` for data models and validation.
- `pyyaml` or `ruamel.yaml` for frontmatter parsing.
- `python-frontmatter` if a simple markdown/frontmatter parser is preferred.
- `networkx` for early graph experimentation.
- `pytest` for tests.

## Storage

### MVP local/dev storage

Use a repo-local markdown directory plus SQLite/Postgres metadata index.

Artifacts:

```text
.memories/local/{repo}/{yyyy-mm-dd}-{slug}.md
.memories/global/{yyyy-mm-dd}-{slug}.md
```

Metadata/index:

- SQLite for local development.
- Postgres for team/shared deployment.

### Recommended production storage

Use Postgres with `pgvector`.

Reasons:

- Stores metadata, lifecycle state, edge records, and embeddings in one system.
- Supports vector search.
- Easy to operate relative to separate graph/vector databases.
- Good enough for MVP and moderate scale.

## Vector retrieval

Recommended MVP:

```text
Chroma
```

Use embeddings over:

```text
Name: {name}
Description: {description}
Tags: {tags}

{body}
```

The embedding model can be swapped. Keep the embedding provider behind an interface.

## Graph storage

For MVP, do not use a dedicated graph database.

Store edges as a relational table:

```text
similarity_edges(
  from_memory_id,
  to_memory_id,
  score,
  reasons_json,
  created_at,
  updated_at
)
```

This is sufficient for one-hop graph expansion and easier to operate than Neo4j or similar graph systems.

Use `networkx` only for offline diagnostics, graph quality analysis, or experiments.

## Graph retrieval algorithms

MVP retrieval should use:

1. Vector search for base memories.
2. Metadata filters for repo/status/scope/files/tags.
3. One-hop edge expansion through `similarity_edges`.
4. Re-ranking with edge score and locality boosts.

No complex graph algorithms are required for MVP.

Useful later additions:

- Personalized PageRank over memory graph for dense clusters.
- Community detection for hotspot analysis.
- Connected-component summaries for Memory Gate review.
- Time-decayed graph scoring.

Do not add these until one-hop expansion proves insufficient.

## API/service layer

Recommended shape:

- Python package for core logic.
- FastAPI service if runtime agents need network access.
- CLI for local development and Memory Gate workflows.

Suggested modules:

```text
backend/
  artifacts.py
  investigator.py
  synthesizer.py
  store.py
  embeddings.py
  graph.py
  retriever.py
  reader.py
  gate.py
  runtime.py
```

Suggested CLI commands:

```text
reasoningbank validate .memories/
reasoningbank investigate --task TASK_ID
reasoningbank synthesize --decision DECISION_ID
reasoningbank retrieve --repo app-api --task "..." --files src/auth/middleware.ts
reasoningbank read MEMORY_ID
reasoningbank gate review
reasoningbank graph refresh
```

## LLM usage

Use LLMs for:

- Memory investigation.
- Memory synthesis.
- Optional tag suggestion.
- Gate review assistance.

Avoid LLMs for:

- YAML validation.
- Status transitions.
- Edge score computation.
- Lifecycle invariants.

All LLM outputs should pass deterministic validation before persistence.

## CI requirements

Add checks for:

- Markdown frontmatter validity.
- Allowed trigger values.
- Tag normalization.
- Body length limits.
- No empty memory bodies.
- No candidate memory accidentally included in active retrieval fixtures.
- Edge references point to existing memories.

## Observability

Log:

- Memory retrieval requests.
- Retrieved previews.
- Memory activations.
- Candidate creation decisions.
- Gate actions.
- Edge creation and refresh events.

Track metrics from `evaluation.md`.

## Recommended MVP deployment path

Phase 1:

- Markdown files in repo.
- SQLite metadata.
- Local vector index or pgvector.
- CLI workflows.

Phase 2:

- Chroma
- FastAPI service.
- Shared Memory Gate dashboard or review queue.

Phase 3:

- Cross-repo global memories.
- Graph diagnostics.
- Better hotspot/density analysis.

## Notes

- You may find pgvecto mentioned throughout -- ignore, we will be using ChromaDB locally
