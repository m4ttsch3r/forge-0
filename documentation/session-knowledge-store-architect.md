# Session & Knowledge Store — Architect Notes

> **Dual-doc notice**: This is the architect-facing half of the session & knowledge store documentation. The user-facing counterpart covering how to use the 8 functions lives in `documentation/session-knowledge-store-agentic.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## Why a unified store?

Every Copilot session starts blind. The context window is empty, no prior decisions are visible, and no knowledge of the repository's evolving state exists — unless something persists it explicitly.

GitHub Issues fills one gap: it tracks planned and completed work. But it has no good answer for:

- *What sub-projects currently exist and where do they live?*
- *Why did a previous agent make this architectural decision?*
- *Which documentation files are relevant to the current task?*

`forge.db` fills these gaps. It is not a replacement for GitHub Issues; it is the complement that gives agents persistent, structured, machine-queryable memory across sessions.

The design deliberately keeps the two concerns separate:

| System | Scope | Owner | Persistence |
|--------|-------|-------|-------------|
| GitHub Issues | Work tracking (planned, in-progress, closed) | Human + agents | GitHub cloud |
| `forge.db` | Knowledge and decisions | Agents + scripts | Local disk |

---

## Two-layer model

The schema is organised into two conceptual layers:

### Layer 1 — Session memory

**Sub-projects** and **decisions** are the "working memory" of the agent system. They answer the question: *"What is the current state of the project and what has been decided?"*

| Table | Role |
|-------|------|
| `sub_projects` | Registry: what projects exist, where they live, what phase they're in |
| `decisions` | Audit trail: what agents decided, with rationale, timestamped |

These tables accumulate over time. They are never purged by `purge_knowledge()` — they represent durable, structured facts about the project.

### Layer 2 — Knowledge index

**Indexed files** and the **FTS5 knowledge_index** are the "long-term knowledge" of the agent system. They answer: *"What do I already know about this topic?"*

| Table | Role |
|-------|------|
| `indexed_files` | Shadow/metadata: path, content hash, doc type, last indexed timestamp |
| `knowledge_index` | FTS5 virtual table: searchable full-text content |

These tables are ephemeral in the sense that they can be fully rebuilt from the filesystem. `purge_knowledge()` clears them without losing any information that isn't already on disk.

---

## Schema walkthrough

### `sub_projects`

```sql
CREATE TABLE sub_projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    path         TEXT NOT NULL,           -- repo-relative, forward-slash
    description  TEXT DEFAULT '',
    status       TEXT DEFAULT 'bootstrapping'
                 CHECK (status IN ('bootstrapping','active','archived')),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Design decisions:**

- `name UNIQUE` — enforces that the same logical project is never registered twice under different identities.
- `path` is repo-relative, forward-slash — satisfies **ROOT_ISOLATION** (no absolute paths escape the repo) and **PATH_STRICTNESS** (normalised form is predictable). Works identically on Windows and Linux.
- `status` CHECK constraint — prevents invalid lifecycle states from entering the database at the SQL layer, not just at the application layer.
- `updated_at` — updated manually by `update_project()`. Not a trigger-maintained field, which keeps the schema portable across SQLite versions.

---

### `decisions`

```sql
CREATE TABLE decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent          TEXT NOT NULL,
    decision       TEXT NOT NULL,
    rationale      TEXT DEFAULT '',
    sub_project_id INTEGER REFERENCES sub_projects(id) ON DELETE SET NULL,
    issue_ref      TEXT    -- e.g. "#6", free-form
);
```

**Design decisions:**

- `sub_project_id` is **nullable** — many architectural decisions (e.g. "defer feature X") apply to the whole repo, not a specific sub-project. Forcing a sub-project association would make the log unusable in the early bootstrapping phase.
- `issue_ref` is a free-form text field rather than an integer FK — GitHub issue numbers are the natural reference but the table should not require a live GitHub connection to remain valid. Free-form text also accommodates references like `"#6 (closed)"` or external trackers.
- No `UPDATE` path — decisions are append-only. If a decision is reversed, a new decision record is added. This preserves the full audit trail.

---

### `indexed_files`

```sql
CREATE TABLE indexed_files (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    path           TEXT NOT NULL UNIQUE,  -- repo-relative, forward-slash
    content_hash   TEXT NOT NULL,          -- SHA-256 hex digest
    sub_project_id INTEGER REFERENCES sub_projects(id) ON DELETE SET NULL,
    doc_type       TEXT DEFAULT 'other'
                   CHECK (doc_type IN ('readme','skill','log','doc','code','other')),
    last_indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Why does this shadow table exist?**

The FTS5 `knowledge_index` virtual table stores content but provides no cheap way to answer: *"Has this file changed since I last indexed it?"* The `indexed_files` table solves this with a SHA-256 content hash. `index_file()` computes the hash of the file on disk, looks it up in `indexed_files`, and skips the insert if the hash matches. Re-indexing an unchanged file is always a no-op — O(1) hash comparison versus a full FTS insert.

This matters in practice because:
- Agent sessions that re-index the whole `documentation/` folder on startup would be slow without deduplication
- FTS5 does not deduplicate — inserting the same content twice would double-weight it in BM25 scoring

**Other decisions:**

- `path UNIQUE` — one row per file; the update path replaces the row when the hash changes.
- `sub_project_id` nullable — top-level repo files (e.g. `documentation/ARCHITECTURE.md`) are not owned by any sub-project.
- `doc_type` CHECK constraint — `readme`, `skill`, `log`, `doc`, `code`, `other`. Agents use this to scope searches (e.g. `search("auth", doc_type="skill")` skips code files).

---

### `knowledge_index` (FTS5 virtual table)

```sql
CREATE VIRTUAL TABLE knowledge_index USING fts5(
    file_id    UNINDEXED,
    path       UNINDEXED,
    sub_project UNINDEXED,
    doc_type   UNINDEXED,
    content,                        -- tokenized; porter + unicode61
    tokenize = 'porter unicode61'
);
```

**Why FTS5?**

FTS5 ships with SQLite (no extension needed) and supports BM25 ranking — the standard information-retrieval scoring function that weights term frequency against inverse document frequency. For Forge's use case (keyword search over markdown, Python source, and logs), BM25 produces significantly better ranking than simple `LIKE '%term%'` queries.

**Why `porter unicode61`?**

- `porter` — applies Porter stemming: "indexed", "indexing", "indexer" all match a query for "index". This dramatically improves recall for natural-language documentation.
- `unicode61` — normalises unicode characters so accented characters, ligatures, and em-dashes do not create spurious mismatches. Essential for cross-platform portability.

**Why `UNINDEXED` for metadata columns?**

`file_id`, `path`, `sub_project`, and `doc_type` are stored in the FTS table for retrieval convenience but are marked `UNINDEXED` so they do not participate in BM25 scoring. Stemming a file path (`"documentation/setup"` → `"document/setup"`) would produce nonsensical results. Only `content` is tokenized.

---

## context-mode separation

`forge.db` and context-mode are **not alternatives** to each other. They serve entirely different purposes:

| Property | `forge.db` | context-mode (`ctx_index`/`ctx_search`) |
|----------|------------|----------------------------------------|
| **Lifetime** | Durable — persists across all sessions | Ephemeral — session-scoped, reset on new session |
| **Availability** | Always available (stdlib SQLite) | VS Code only (Node.js MCP server) |
| **Purpose** | Structured agent memory + knowledge base | Context window compression for current session |
| **Purge** | Explicit `purge_knowledge()` call | Automatic on session end |
| **Scope** | Cross-session, cross-agent | Single session, single agent |

**The key design decision**: forge.db must work in CI, in headless scripts, and in any agent environment — not just VS Code. Binding it to the context-mode MCP server would break all non-VS Code invocations. The two systems can be used together in a VS Code session (context-mode for live session compression, forge.db for durable storage) but they have no fallback relationship and no dependency on each other.

---

## Constraints compliance

| Constraint | How `forge.db` / `forge_db.py` satisfies it |
|------------|---------------------------------------------|
| **ROOT_ISOLATION** | Database path is `{repo_root}/data/forge.db` via `pathlib`. All stored paths are repo-relative. No absolute paths are stored or constructed from user input. |
| **PATH_STRICTNESS** | All paths normalised to forward-slash before storage. `pathlib.Path` handles OS-specific separators transparently on both Windows and Linux. |
| **PORTABILITY** | Pure Python stdlib — `sqlite3`, `pathlib`, `hashlib`. No pip dependencies. Works on W11 and Linux identically. No Node.js, no native extensions. |
| **DEPENDENCY_STRATEGY** | Zero new dependencies. SQLite ships with CPython 3.x. FTS5 is compiled into the standard SQLite binary on all modern platforms. |

---

## TDD approach

`test_forge_db.py` was written before `forge_db.py` (red-green-refactor). The test file covers all 8 public functions:

| Function | What the test asserts |
|----------|-----------------------|
| `get_connection` | Returns a valid `sqlite3.Connection`; all 4 tables exist |
| `register_project` | Row appears in `sub_projects`; `name UNIQUE` raises on duplicate |
| `update_project` | Field values updated; `updated_at` changes |
| `list_projects` | Returns all rows; `status=` filter works |
| `log_decision` | Row appears in `decisions`; nullable fields accepted |
| `get_decisions` | Returns rows; `agent=` and `sub_project_id=` filters work; `limit=` respected |
| `index_file` | Row in `indexed_files`; content in `knowledge_index`; re-index of unchanged file is no-op |
| `search` | Returns ranked results; `doc_type=` and `sub_project_id=` filters narrow results; empty query returns empty list |
| `purge_knowledge` | Clears `knowledge_index` and `indexed_files`; `sub_projects` and `decisions` unaffected |

Tests use an in-memory SQLite database (`:memory:`) so they run in isolation with no filesystem side effects.

---

## What was deferred and why

### `active_tasks` table

An `active_tasks` table was proposed to track in-flight GitHub Issues directly in `forge.db`. This was deliberately deferred because:

1. **No sync strategy** — GitHub is the source of truth for issue state. Any local `active_tasks` table diverges from GitHub state the moment an issue is closed, labelled, or moved outside the agent. Resolving that conflict requires a bi-directional sync strategy that has not been designed.
2. **Premature schema lock-in** — building the table before the sync strategy is understood would force a schema migration later. Schema migrations in SQLite are painful (no `ALTER TABLE DROP COLUMN` in older versions).
3. **Issues API available** — the GitHub MCP server already provides `list_issues` and `search_issues`. Agents can query GitHub directly; the local cache is only worth building when the API is unavailable or too slow.

### Async interface

All functions are synchronous. An async wrapper (e.g. `aiosqlite`) was considered but deferred because:
- The primary consumers are CLI scripts and synchronous agent tool calls, not async web servers
- `sqlite3` in WAL mode handles concurrent reads without blocking; the bottleneck is never I/O
- Adding `asyncio` would break the zero-external-dependency constraint

### Schema versioning / migrations

A `schema_version` table and migration runner were considered. Deferred because:
- The schema is young and subject to change
- `get_connection()` currently handles idempotent `CREATE TABLE IF NOT EXISTS` — sufficient for the bootstrapping phase
- A proper migration system (e.g. Alembic-style versioned scripts) should be added before the schema reaches v2

---

_Agent: devops-documenter · Model: claude-sonnet-4.6 · Skills: project-context_
