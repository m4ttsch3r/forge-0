# Forge

**Self-contained mono-repo prototype station and knowledgebase incubator.**

Forge is where ideas and solutions are prepared for real-world use before they graduate to their own repositories or pipelines. Each sub-project lives in an isolated `Project-XX/` folder with strict encapsulation. A full multi-agent Copilot stack orchestrates planning, implementation, review, QA, and documentation.

- **OS-agnostic** — runs on Windows 11 and Linux without modification
- **Pipeline-ready** — every sub-project is easy to plug into an automation pipeline
- **Agentic-first** — agents handle planning, implementation, review, and docs

> **SKILL.md status**: `active` — onboarding completed at root commit `a8ce721`.
> See `documentation/setup-agentic.md` for the full setup guide.

---

## Repository structure

```
forge-0/
├── .github/
│   ├── agents/                   # Agent definition files (.agent.md)
│   ├── skills/project-context/   # SKILL.md — project context loaded by all agents
│   └── copilot-instructions.md   # Repo-level Copilot instructions
├── documentation/                # Repo-wide operational and architectural docs
│   ├── ARCHITECTURE.md
│   ├── dual-doc-convention.md    # Dual-documentation spec
│   ├── setup-agentic.md          # User-facing setup guide
│   ├── setup-architect.md        # Architect-facing design rationale
│   ├── context-mode-integration-agentic.md
│   ├── context-mode-integration-architect.md
│   ├── think-in-code-agentic.md
│   ├── think-in-code-architect.md
│   ├── session-knowledge-store-agentic.md
│   └── session-knowledge-store-architect.md
├── scripts/
│   ├── forge_db.py               # SQLite session + knowledge store interface
│   ├── test_forge_db.py          # Smoke tests for forge_db.py
│   └── seed-labels.sh            # Bash script to seed GitHub labels
├── .gitignore
├── .mcp.json.example             # MCP configuration template (copy to .mcp.json)
├── CHANGELOG.md
└── README.md
```

---

## Agents

| Agent | Purpose |
|-------|---------|
| `devops-director` | Turns ideas and requirements into GitHub issues |
| `devops-producer` | Plans sessions, grooms backlog, closes issues after QA |
| `devops-lead` | Architecture decisions and implementation orchestration |
| `devops-executor` | Hands-on implementation |
| `devops-reviewer` | Security and maintainability review |
| `devops-documenter` | Wiki, CHANGELOG, and user guides |
| `devops-qa` | Validates issue acceptance criteria before closure |

> The `project-onboarding` agent self-destructed after first use — this is by design.
> See `documentation/setup-architect.md` for the rationale.

---

## Workflow

1. Open a session — tell `devops-producer` *"what should we tackle today?"*
2. `devops-producer` grooms the backlog and proposes a session plan
3. `devops-lead` or `devops-executor` implements the work on a `task/<slug>` branch
4. Work squash-merges to `main`; issue is marked `status: ready-for-qa`
5. `devops-producer` runs `devops-qa` to validate acceptance criteria, then closes the issue

**Branch naming**: `task/<kebab-slug>` — e.g. `task/add-project-01`, `task/fix-path-handling`  
**Commits**: [Conventional Commits](https://www.conventionalcommits.org/) style (`feat:`, `fix:`, `docs:`, `chore:`, etc.)

---

## System constraints

These constraints are enforced on every sub-project. Violating them causes QA failures.

| Constraint | Rule |
|---|---|
| **ROOT_ISOLATION** | Sub-projects must not import from the repo root or other sub-projects |
| **PATH_STRICTNESS** | Use `pathlib.Path` exclusively — no hardcoded path strings |
| **PORTABILITY** | Every `Project-XX/` folder must be valid as a standalone Git repo |
| **DEPENDENCY_STRATEGY** | Local `requirements.txt` per `Project-XX/` — no shared root-level deps |

---

## Key integrations

- **context-mode MCP server** — keeps raw data out of the context window; configure via `.mcp.json` (copy from `.mcp.json.example`)
- **SQLite knowledge store** — `data/forge.db` (gitignored); interface via `scripts/forge_db.py`; tables: `sub_projects`, `decisions`, `indexed_files`, `knowledge_index` (FTS5)
- **GitHub API** — issue management, label seeding
- **VS Code API** — Copilot workspace integration

---

## Prerequisites

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) installed and authenticated
- `gh` CLI installed and authenticated (`gh auth login`)
- Node.js 18+ (required for the context-mode MCP server)
- `context-mode` installed globally: `npm install -g context-mode`
- A GitHub personal access token with `repo` scope (for label seeding)

---

## Documentation

| Document | Description |
|---|---|
| `documentation/setup-agentic.md` | Full setup guide — what Forge is, repo structure, workflow, label seeding |
| `documentation/setup-architect.md` | Design rationale — onboarding decisions, SKILL.md field mapping, agent choreography |
| `documentation/dual-doc-convention.md` | Dual-documentation spec (every significant piece of work requires two doc artifacts) |
| `documentation/think-in-code-agentic.md` | Think in Code guide — agents write analysis scripts rather than reading raw data into context |
| `documentation/context-mode-integration-agentic.md` | context-mode MCP server install and tool reference |
| `documentation/session-knowledge-store-agentic.md` | SQLite knowledge store — what gets stored, how to query, how to reset |
| `CHANGELOG.md` | All notable changes |
