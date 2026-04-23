# Session & Knowledge Store — User Guide

> **Dual-doc notice**: This is the user-facing half of the session & knowledge store documentation. The architect-facing counterpart covering design rationale and system internals lives in `documentation/session-knowledge-store-architect.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## What is forge.db?

`forge.db` is the **durable memory of the Forge agent system**. Every Copilot session starts fresh — no agent automatically remembers what happened last session. `forge.db` changes that by providing:

- A **sub-project registry** so agents always know what projects exist and where they live
- A **decision log** so every significant agent decision is recorded with its rationale
- A **searchable knowledge index** so agents can retrieve relevant documentation, code, or notes without reading whole files into context

The database lives at `data/forge.db` inside the repo root and is gitignored — it holds machine-local, runtime state that should not be version-controlled.

---

## What gets stored

| What | Where | Why |
|------|-------|-----|
| Sub-project names, paths, descriptions, and lifecycle status | `sub_projects` table | Agents can discover and route to projects without reading the directory tree |
| Agent decisions with rationale and timestamps | `decisions` table | Builds an auditable trail of what was decided and why |
| File metadata: path, content hash, doc type | `indexed_files` table | Enables deduplication — unchanged files are never re-indexed |
| Full-text content, searchable via FTS5 | `knowledge_index` virtual table | Powers fast keyword + stemmed search across all indexed knowledge |

---

## Database location

```
{repo_root}/data/forge.db
```

- The `data/` directory is created automatically at runtime if it does not exist.
- `data/forge.db` is listed in `.gitignore` — it will never be committed.
- You can delete `data/forge.db` at any time to start fresh; the next agent session will recreate it.

---

## The 8 functions in `scripts/forge_db.py`

All functions live in `scripts/forge_db.py` and use only Python standard library (`sqlite3`, `pathlib`, `hashlib`). No external dependencies are required.

### `get_connection()`

Opens (and if necessary creates) the SQLite database at `data/forge.db`, runs schema migrations, and returns the `sqlite3.Connection` object. All other functions call this internally.

```python
from scripts.forge_db import get_connection
conn = get_connection()
```

---

### `register_project(name, path, description="", status="bootstrapping")`

Adds a new sub-project to the registry. `path` must be repo-relative and use forward slashes.

```python
from scripts.forge_db import register_project
register_project(
    name="project-alpha",
    path="Project-01",
    description="Experimental RAG pipeline",
    status="active"
)
```

Valid `status` values: `bootstrapping`, `active`, `archived`.

---

### `update_project(name, **kwargs)`

Updates one or more fields on an existing sub-project record. Pass only the fields you want to change.

```python
from scripts.forge_db import update_project
update_project("project-alpha", status="archived", description="Retired after Phase 2")
```

---

### `list_projects(status=None)`

Returns all registered sub-projects as a list of `sqlite3.Row` objects. Pass `status` to filter.

```python
from scripts.forge_db import list_projects

# All projects
all_projects = list_projects()

# Only active ones
active = list_projects(status="active")
for p in active:
    print(p["name"], p["path"])
```

---

### `log_decision(agent, decision, rationale, sub_project=None, issue_ref=None)`

Records a timestamped agent decision with its rationale. `sub_project` and `issue_ref` are optional but strongly encouraged when context is available.

```python
from scripts.forge_db import log_decision
log_decision(
    agent="devops-lead",
    decision="Defer active_tasks table",
    rationale="No GitHub sync strategy agreed yet; premature implementation would lock in wrong schema.",
    issue_ref="#6"
)
```

---

### `get_decisions(sub_project=None, agent=None, limit=20)`

Retrieves logged decisions, optionally filtered by sub-project or agent, most recent first.

```python
from scripts.forge_db import get_decisions

# All recent decisions
recent = get_decisions(limit=10)

# Decisions by a specific agent
lead_decisions = get_decisions(agent="devops-lead")

# Decisions scoped to a sub-project
project_decisions = get_decisions(sub_project="project-alpha")
```

---

### `index_file(path, sub_project=None, doc_type="other")`

Reads a file, computes its SHA-256 content hash, stores metadata in `indexed_files`, and inserts the content into the FTS5 `knowledge_index`. If the file's hash is unchanged since the last index, the call is a no-op.

```python
from scripts.forge_db import index_file
index_file(
    path="documentation/setup-agentic.md",
    sub_project=None,
    doc_type="doc"
)
```

Valid `doc_type` values: `readme`, `skill`, `log`, `doc`, `code`, `other`.

---

### `search(query, sub_project=None, doc_type=None, limit=10)`

Performs a full-text search over `knowledge_index` using FTS5 BM25 ranking (porter stemming + unicode61). Returns a list of matching rows with `file_id`, `path`, `sub_project`, `doc_type`, and a `snippet` of matching content.

```python
from scripts.forge_db import search

# Broad keyword search
results = search("sqlite schema migration")

# Scoped to a doc type
docs = search("setup guide", doc_type="doc")

# Scoped to a sub-project
project_hits = search("auth token", sub_project="project-alpha", limit=5)

for r in results:
    print(r["path"], r["snippet"])
```

---

### `purge_knowledge(sub_project=None)`

Removes content from the knowledge index. If `sub_project` is provided, only entries for that sub-project are removed. If omitted, **all** indexed content is deleted.

```python
from scripts.forge_db import purge_knowledge

# Purge a single sub-project's knowledge
purge_knowledge(sub_project="project-alpha")

# Full reset — clears all indexed files and FTS content
purge_knowledge()
```

> ⚠️ `purge_knowledge()` with no argument is irreversible. It does **not** delete `sub_projects` or `decisions` records.

---

## Common workflows

### Index all documentation on session start

```python
from pathlib import Path
from scripts.forge_db import index_file

for md in Path("documentation").glob("**/*.md"):
    index_file(str(md), doc_type="doc")
```

### Find relevant prior decisions before starting a new task

```python
from scripts.forge_db import search
hits = search("database schema")
for h in hits:
    print(f"[{h['path']}] {h['snippet']}")
```

### Check what sub-projects are active before routing work

```python
from scripts.forge_db import list_projects
for p in list_projects(status="active"):
    print(p["name"], "→", p["path"])
```

---

## Resetting the store

| Goal | Command |
|------|---------|
| Reset knowledge index only | `purge_knowledge()` |
| Reset one project's knowledge | `purge_knowledge(sub_project="<name>")` |
| Full wipe (decisions + projects + knowledge) | Delete `data/forge.db` and restart |

---

## CHANGELOG entry

### Added — Issue #6: Unified SQLite session + knowledge store

- Added `scripts/forge_db.py` — pure-Python stdlib module providing 8 functions: `get_connection`, `register_project`, `update_project`, `list_projects`, `log_decision`, `get_decisions`, `index_file`, `search`, `purge_knowledge`
- Added `data/` directory (gitignored, created at runtime) — stores `forge.db`
- Added `documentation/session-knowledge-store-agentic.md` (this file)
- Added `documentation/session-knowledge-store-architect.md`

---

_Agent: devops-documenter · Model: claude-sonnet-4.6 · Skills: project-context_
