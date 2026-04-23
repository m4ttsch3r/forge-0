# context-mode Integration — User Guide

> **Dual-doc notice**: This is the user-facing half of the context-mode integration documentation. The architect-facing counterpart covering design rationale and system internals lives in `documentation/context-mode-integration-architect.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## What is context-mode?

**context-mode** is an MCP (Model Context Protocol) server that gives Copilot agents a set of sandboxed execution and indexing tools. Instead of reading raw files into the context window, agents write and run scripts — keeping context lean and results precise. Forge uses context-mode to enforce the "Think in Code" mandate and to maintain session continuity across compactions.

---

## The 6 sandbox tools

| Tool | What it does |
|------|-------------|
| `ctx_execute` | Runs a single shell command or script in an isolated sandbox and returns its output. |
| `ctx_batch_execute` | Runs a list of commands sequentially in the same sandbox session, useful for multi-step workflows. |
| `ctx_execute_file` | Executes a script file that already exists on disk rather than an inline string. |
| `ctx_index` | Indexes a file or directory into the context-mode SQLite store so it can be searched later. |
| `ctx_search` | Performs a BM25 full-text search over the indexed store and returns ranked matching snippets. |
| `ctx_fetch_and_index` | Fetches a URL, extracts its text content, and indexes it in one operation. |

---

## Verifying it's working

In the VS Code Copilot Chat panel, type:

```
ctx stats
```

A healthy response lists the number of indexed documents, the SQLite database path, and the active session ID. If context-mode is not running you will see a "tool not found" error — check that `.vscode/mcp.json` is present and that Node.js / `context-mode` are on your PATH.

---

## Configuration files explained

### `.vscode/mcp.json`

Registers context-mode as an MCP server that VS Code Copilot loads automatically when you open the repo:

```json
{
  "servers": {
    "context-mode": {
      "command": "context-mode"
    }
  }
}
```

VS Code spawns the `context-mode` process on session start. No arguments are needed; the binary auto-configures from the current working directory.

### `.github/hooks/context-mode.json`

Wires context-mode into the Copilot hook system for three lifecycle events:

```json
{
  "hooks": {
    "PreToolUse":  [{ "type": "command", "command": "context-mode hook vscode-copilot pretooluse"  }],
    "PostToolUse": [{ "type": "command", "command": "context-mode hook vscode-copilot posttooluse" }],
    "SessionStart":[{ "type": "command", "command": "context-mode hook vscode-copilot sessionstart"}]
  }
}
```

| Hook | When it fires | What it does |
|------|--------------|-------------|
| `SessionStart` | Once at the start of each Copilot session | Injects routing context so agents know which tools are available |
| `PreToolUse` | Before every tool call | Records the intent and prevents raw-data reads where a script would be cheaper |
| `PostToolUse` | After every tool call | Records the result for session continuity and compaction |

---

## Decision guide — when to use each tool

| Scenario | Recommended tool |
|----------|-----------------|
| Run a one-liner to check a value | `ctx_execute` |
| Run a multi-step build or test sequence | `ctx_batch_execute` |
| Execute a pre-written migration or seed script | `ctx_execute_file` |
| Make a large file searchable without reading it whole | `ctx_index` |
| Find relevant lines in an indexed codebase | `ctx_search` |
| Ingest external documentation or a web page | `ctx_fetch_and_index` |

---

## CHANGELOG

### ops: integrate context-mode MCP server with VS Code Copilot (#4)

- Added `.vscode/mcp.json` — registers context-mode as an MCP server for VS Code Copilot
- Added `.github/hooks/context-mode.json` — PreToolUse / PostToolUse / SessionStart hooks
- Updated `.mcp.json.example` — added VS Code-style `servers` entry alongside existing `mcpServers` entry
- Updated `documentation/setup-agentic.md` — added Node.js 18+ and `npm install -g context-mode` prerequisites
- Added `documentation/context-mode-integration-agentic.md` (this file)
- Added `documentation/context-mode-integration-architect.md`
