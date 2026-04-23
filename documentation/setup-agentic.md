# Forge — Setup Guide (Agentic / General Users)

> **Dual-doc notice**: This is the user-facing half of the setup documentation. The architect-facing counterpart covering design rationale and agent choreography lives in `documentation/setup-architect.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## What is Forge?

**Forge** is a self-contained mono-repo prototype station and knowledgebase incubator. It is the place where ideas and solutions are prepared for real-world use before they graduate to their own repositories or pipelines.

Key characteristics:

- **Knowledgebase / incubator mono-repo** — each sub-project lives in its own `Project-XX/` folder with strict encapsulation
- **OS-agnostic** — designed to run on Windows 11 and Linux without modification
- **Pipeline-ready** — every sub-project is easy to plug into an automation pipeline
- **Agentic-first** — a full multi-agent Copilot CLI stack orchestrates planning, implementation, review, and documentation

---

## System constraints

These four constraints are enforced on **every** sub-project inside the repo. Violating them will cause QA failures.

| Constraint | What it means for you |
|---|---|
| **ROOT_ISOLATION** | Sub-projects must not import from the repo root or from other sub-projects. Each `Project-XX/` folder is a self-contained island. |
| **PATH_STRICTNESS** | Use `pathlib.Path` exclusively. No hardcoded path strings (no `"C:\\stuff"`, no `"/home/user/stuff"`). This is the primary portability guard. |
| **PORTABILITY** | Every `Project-XX/` folder must be valid as a standalone Git repository — it can be extracted and work on its own. |
| **DEPENDENCY_STRATEGY** | Each `Project-XX/` folder carries its own `requirements.txt`. There is no shared root-level dependency file for sub-projects. |

---

## Repository structure

```
forge-0/
├── .github/
│   ├── agents/                  # Agent definition files (.agent.md)
│   ├── skills/project-context/  # SKILL.md — project context loaded by all agents
│   └── copilot-instructions.md  # Repo-level Copilot instructions
├── documentation/               # Repo-wide operational and architectural docs
│   ├── ARCHITECTURE.md
│   ├── dual-doc-convention.md   # Dual-documentation spec (read this)
│   ├── labels.md                # Label taxonomy reference
│   ├── new-project-setup.md     # Setup walkthrough (template-era doc)
│   ├── setup-agentic.md         # ← this file
│   └── setup-architect.md       # Architect-facing counterpart
├── scripts/
│   └── seed-labels.sh           # Bash script to seed GitHub labels
├── .gitignore
├── .mcp.json.example            # MCP configuration template
├── CHANGELOG.md
└── README.md
```

---

## SKILL.md — the project brain

`SKILL.md` lives at `.github/skills/project-context/SKILL.md`. It is the single source of truth that all Copilot agents load at the start of every session.

### Why it matters

Every agent in the Forge stack reads `SKILL.md` before acting. Without it, agents have no project context and will behave generically.

### The `status` field

The front-matter of `SKILL.md` contains a `status` field:

```yaml
---
name: project-context
status: active   # or: bootstrap
---
```

| Status | Meaning | What happens |
|---|---|---|
| `status: active` | Onboarding is complete; all agents are fully operational | Normal Copilot work can proceed |
| `status: bootstrap` | The project-onboarding agent has not run yet | **Do not start any Copilot work.** Run project onboarding first (`/onboarding` in the Copilot CLI chat panel). Agents that read `bootstrap` status should refuse to proceed until onboarding is complete. |

**Current status for this repo**: `active` — onboarding completed at root commit `a8ce721`.

### A note on the onboarding agent

`.github/agents/project-onboarding.agent.md` **no longer exists** in this repository. This is by design: the project-onboarding agent self-destructs after a successful run (commit `0db3213`). It is a one-time setup tool. Do not attempt to recreate it; use the template repo if you need to onboard a fresh project.

---

## Label taxonomy

Labels are defined in `documentation/labels.md`. Every issue must carry exactly one `type:` label and one `priority:` label.

### Summary

| Group | Labels |
|---|---|
| **Type** | `type: bug` · `type: feature` · `type: security` · `type: ops` · `type: docs` · `type: support` |
| **Priority** | `priority: very-low` · `priority: low` · `priority: mid` · `priority: high` · `priority: very-high` |
| **Status** | `status: ready-for-qa` |

### Seeding labels on a new environment

The canonical seeding script requires Bash:

```bash
GITHUB_TOKEN=<your-token> OWNER=m4ttsch3r REPO=forge-0 bash scripts/seed-labels.sh
```

**On Windows (PowerShell)**, use the `gh` CLI directly:

```powershell
# Example — create one label; repeat for each entry in documentation/labels.md
gh label create "type: bug" --color "d73a4a" --description "Something broken / unexpected behaviour" --repo m4ttsch3r/forge-0

gh label create "priority: high" --color "f66a0a" --description "Do in the next session" --repo m4ttsch3r/forge-0

gh label create "status: ready-for-qa" --color "8b5cf6" --description "Implementation complete; pending QA before closure" --repo m4ttsch3r/forge-0
```

See `documentation/labels.md` for the full list of names, colors, and descriptions.

---

## Task-branch workflow

All work happens on short-lived task branches that squash-merge to `master` (or `main`).

```
1. git checkout master && git pull
2. git checkout -b task/<kebab-slug>
3. ... make changes, commit normally ...
4. git checkout master
5. git merge --squash task/<kebab-slug>
6. git commit -m "type: description (#issue-number)"
7. git push origin master
8. git branch -d task/<kebab-slug>
9. git push origin --delete task/<kebab-slug>
```

**Branch naming**: `task/<kebab-slug>` — use lowercase words separated by hyphens. Examples:
- `task/setup-agentic-doc`
- `task/add-project-01`
- `task/fix-path-handling`

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) style (`feat:`, `fix:`, `docs:`, `chore:`, etc.).

---

## Dual-documentation convention (brief intro)

Every **significant** piece of work in Forge requires two documentation artifacts:

| Artifact | Audience | What it covers |
|---|---|---|
| `<topic>-agentic.md` (or `## For users` section) | Users and agents | What was built, how to use it, CHANGELOG entry |
| `<topic>-architect.md` (or `## For architects` section) | Human architects | Why decisions were made, tradeoffs, agent choreography |

Neither artifact is optional. Both must exist before an issue can be labelled `status: ready-for-qa`.

> **Full spec**: `documentation/dual-doc-convention.md`

---

## Replicating the setup in a new environment

Use this checklist when setting up Forge (or a Forge-derived project) from scratch.

### Prerequisites

- Git installed
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) installed
- `gh` CLI installed and authenticated (`gh auth login`)
- A GitHub personal access token with `repo` and `workflow` scopes (for label seeding)
- GitHub Copilot subscription

### Steps

```bash
# 1. Create the repository (or use the GitHub template button)
gh repo create my-project --template m4ttsch3r/forge-0 --private
gh repo clone my-project && cd my-project

# 2. Configure git identity
git config user.name "Your Name"
git config user.email "your@email.com"

# 3. Copy and configure MCP settings
cp .mcp.json.example .mcp.json
# Edit .mcp.json for your environment

# 4. Run project onboarding (one-time)
# In the Copilot CLI chat panel:
#   /onboarding
# The agent will ask ~9 questions, populate SKILL.md, seed labels,
# create a milestone, then self-destruct.

# 5. Seed labels (if onboarding didn't do it, or on Windows)
# See the "Seeding labels" section above

# 6. Verify SKILL.md status is "active" before starting work
```

### Initial commit (if starting from scratch without a template)

```bash
git init
git config user.name "Your Name"
git config user.email "your@email.com"
git add .
git commit -m "chore: initial commit"
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin master
```

---

## Quick-reference: repo facts for this instance

| Item | Value |
|---|---|
| GitHub repo | https://github.com/m4ttsch3r/forge-0 |
| Root commit | `a8ce721` |
| Git identity | m4ttsch3r / m4tt.mir1@gmail.com |
| SKILL.md status | `active` |
| Issues filed | #1 (docs), #2, #3 — with full label taxonomy |
| Onboarding agent | Self-destructed in commit `0db3213` — by design |
