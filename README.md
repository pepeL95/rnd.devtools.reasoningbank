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

## CLI

The CLI now has eight main commands. Two commands manage local setup and default resolution; the rest operate on the memory lifecycle:

- `init`: bootstrap a `.reasoningbank/` store in the current working directory.
- `config`: inspect or write `.reasoningbankconfig` defaults for `root` and `repo_path`. Resolution walks upward from the current directory to `/`, then falls back to `~/.reasoningbankconfig`.
- `validate`: check markdown artifacts for frontmatter/body contract issues without indexing them.
- `index`: ingest one validated markdown artifact into SQLite and Chroma with repo/status/scope metadata.
- `retrieve`: search active memories for a repo task and return preview-only hits.
- `read`: inspect one memory by id; `--detail body` logs an activation and returns the full body.
- `gate`: apply offline lifecycle actions such as `approve`, `reject`, `archive`, `promote_to_global`, or `demote_to_local`.
- `graph-refresh`: recompute similarity edges for one memory.

Run `reasoningbank --help` for the overview, or `reasoningbank <command> --help` for examples and argument details.

### Config Resolution

If you do not pass `--root` or `--repo`, the CLI resolves defaults in this order:

1. The nearest `.reasoningbankconfig` in the current directory or one of its parents.
2. `~/.reasoningbankconfig`.
3. Built-in fallback:
   `root = <cwd>/.reasoningbank`
   `repo_path = <cwd>`

`repo_path` is stored as a path, and the effective repo name is inferred from its basename.
