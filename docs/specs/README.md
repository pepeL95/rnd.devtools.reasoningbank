# ReasoningBank MVP Implementation Specs

This folder contains implementation-ready markdown specs for the ReasoningBank-inspired memory system for an AI software engineer agent.

The MVP is local-first, markdown-native, graph-backed, and offline-curated. Runtime agents may propose candidate local memories, but promotion, demotion, merging, and archival are handled by a designated Memory Gate Agent offline.

## Files

- `memory_artifact_contract.md` — canonical markdown memory format and metadata contract.
- `memory_investigator.md` — decides whether a trajectory deserves a memory candidate.
- `memory_synthesizer.md` — writes concise, abstract-style memory artifacts.
- `memory_store.md` — persists memory artifacts, metadata, embeddings, and evidence.
- `similarity_graph_builder.md` — creates simple similarity edges between memories.
- `memory_retriever.md` — retrieves relevant memories and graph neighbors at task time.
- `memory_reader.md` — controls progressive disclosure of memory content.
- `memory_gate_agent.md` — offline curator for approval, rejection, promotion, demotion, and graph hygiene.
- `agent_runtime_integration.md` — how the coding agent uses the memory system.
- `evaluation.md` — acceptance criteria and quality metrics.
- `stack.md` — recommended implementation stack.
