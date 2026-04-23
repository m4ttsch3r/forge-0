# context-mode Integration — Architect Notes

> **Dual-doc notice**: This is the architect-facing half of the context-mode integration documentation. The user-facing counterpart lives in `documentation/context-mode-integration-agentic.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## Why context saving matters

Every token an agent reads into the context window is a token it cannot use for reasoning. For file-heavy workflows this becomes a hard constraint: a raw Playwright trace weighs ~56 KB; after context-mode indexes and compacts it to a BM25-retrievable store the retrieval payload is ~1.2 KB — a **98% reduction**. At that ratio, agents that previously had to summarise-and-discard can now retrieve-and-reason across the full session history without exhausting the context budget.

The practical implication for Forge: sub-projects that involve large test artefacts, generated code, or external documentation can stay tractable inside a single agent session instead of requiring manual chunking.

---

## How the hook system works

context-mode inserts itself into the Copilot agent lifecycle via three hooks defined in `.github/hooks/context-mode.json`.

### `SessionStart`

Fires once when VS Code starts a Copilot session. It injects a routing preamble that tells the agent which MCP tools are available and how to prefer them over raw file reads. **No changes to `copilot-instructions.md` are needed** — the routing is injected at runtime by the hook, so the base instruction file stays clean and portable.

### `PreToolUse`

Fires before every tool call. context-mode inspects the pending call; if the agent is about to read a large file verbatim, the hook can substitute a `ctx_index` + `ctx_search` pattern instead. This is the primary enforcement point for the "Think in Code" mandate (see below).

### `PostToolUse`

Fires after every tool call. The hook records the tool name, arguments, and a hash of the output into the session event log (SQLite). This record is what enables compaction — when the context window approaches capacity, context-mode can summarise past events using BM25 retrieval rather than truncation.

---

## Session continuity: SQLite + FTS5

context-mode maintains a local SQLite database with an FTS5 (full-text search) virtual table. Every `ctx_index` call writes chunks into this table. Every `ctx_search` call queries it using BM25 ranking.

The session event log (also SQLite) stores a timestamped entry for each tool invocation. On compaction, context-mode replays the event log, retrieves the top-k chunks for each query, and produces a compact summary that fits within a configurable token budget. The original indexed content is retained on disk and remains searchable in future sessions.

Key design properties:
- **Deterministic retrieval**: BM25 scores are stable across compactions; the same query returns the same top-k results.
- **No external dependencies**: SQLite ships with Node.js via `better-sqlite3`; no database server is needed.
- **Portable**: the database path defaults to `.context-mode/` inside the repo root, which is gitignored.

---

## The "Think in Code" mandate

Forge enforces a rule: **agents write scripts, not raw-data reads**. Instead of calling `view` on a 3000-line file, an agent should:

1. `ctx_index` the file once
2. `ctx_search` for the relevant symbol or section
3. Operate on the returned ~50-line snippet

This is not a style preference — it is enforced by the `PreToolUse` hook at runtime. Agents that bypass it will find their raw-read results silently replaced with a prompt to use the indexed path.

The mandate keeps individual tool-call outputs small, preserves context budget for reasoning, and makes sessions reproducible (the same search query returns the same ranked results).

---

## Design decision: Node.js MCP over a Python alternative

Several MCP server implementations exist in Python (e.g. `mcp` via `pip`). context-mode is Node.js. The reasons Forge chose Node.js:

| Factor | Node.js (context-mode) | Python alternative |
|--------|------------------------|-------------------|
| **Ecosystem maturity** | context-mode is the reference MCP implementation; it tracks the MCP spec closely | Python wrappers lag the spec by days to weeks |
| **SQLite bindings** | `better-sqlite3` is synchronous, mature, and ships pre-built binaries for all platforms | `sqlite3` / `aiosqlite` are async-only or require a compile step on Windows |
| **VS Code integration** | `servers` key in `.vscode/mcp.json` is the officially documented VS Code MCP format | Python servers require additional `type: stdio` configuration |
| **PATH simplicity** | `winget install OpenJS.NodeJS.LTS` puts `node` and `npm` on the system PATH automatically | Python PATH management on Windows requires manual `PATHEXT` or virtual-env activation |
| **Subprocess model** | context-mode runs as a detached subprocess; VS Code manages its lifecycle | Python servers need explicit `uvicorn` or `asyncio` process management |

The tradeoff: Node.js adds a runtime dependency that pure-Python shops may not have. This is accepted because Node.js 18+ is a standard component of the modern development environment and `winget` makes the install trivial on Windows.

---

## Forge-specific notes

- **context-mode as subprocess**: VS Code spawns `context-mode` via `.vscode/mcp.json` using the `command: "context-mode"` form (no `args`). This means the `context-mode` binary must be on the system PATH. The verified install method is `npm install -g context-mode` after `winget install OpenJS.NodeJS.LTS`.
- **Confirmed PATH availability**: on the Forge dev machine (Windows 11), `context-mode --version` outputs `v1.0.89` from any working directory after the global npm install.
- **`.mcp.json.example`**: updated to include both the legacy `mcpServers` entry (for Copilot CLI / `mcp-config.json` users) and the new `servers` entry (for VS Code `.mcp.json` / `.vscode/mcp.json` users). Operators should copy the relevant block for their client.
- **gitignore**: `.context-mode/` (the local SQLite store) should be added to `.gitignore` if not already present. It contains machine-local session data.
