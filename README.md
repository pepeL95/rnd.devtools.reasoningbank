# ReasoningBank

Local-first, markdown-native memory system for AI software engineering agents.

The implementation follows the specs in `docs/specs/`:

- Markdown artifacts are canonical human-readable memory records.
- SQLite is the local machine-readable index.
- Runtime retrieval returns compact previews and hides candidate memories by default.
- Full body reads are explicit and logged.
- Gate workflows are the only path to activate, reject, archive, or promote memories.
- Chroma is the vector store.
- LangChain Gemini is the LLM and embedding integration.

## Smoke Test

```bash
python3 scripts/smoke_reasoningbank.py
```

This creates a temporary Chroma + SQLite memory store, synthesizes a candidate, confirms candidate leakage is blocked, approves the memory through the gate, retrieves it, activates its body, and refreshes graph edges. The smoke test uses a local test embedding object so it does not consume a Gemini API key; the CLI/runtime path uses LangChain Gemini embeddings.

For a live Gemini-backed smoke test:

```bash
export GOOGLE_API_KEY="..."
/opt/homebrew/Caskroom/miniforge/base/envs/reasoningbank/bin/python scripts/live_gemini_smoke.py
```

## Gemini Credentials

Do not commit API keys. For CLI/runtime usage, set the standard LangChain Google credential environment variable:

```bash
export GOOGLE_API_KEY="..."
```

For local development, an ignored `.env` file may also be used by your shell tooling; keep `.env.example` as the committed template only.
