# Forge — Setup Guide (Human Architect)

> **Dual-doc notice**: This is the architect-facing half of the setup documentation. The user-facing counterpart covering what Forge is, how to use it, and operational checklists lives in `documentation/setup-agentic.md`.
> Full spec: `documentation/dual-doc-convention.md`

---

## Section 1: Onboarding interrogation — why those 9 questions?

The project-onboarding agent asks exactly 9 questions, one at a time, never bundled. Each question maps to a specific field in `.github/skills/project-context/SKILL.md`. Together these fields form the **context block** that every agent in the stack loads at session start. Getting them right once — up front — eliminates per-session negotiation.

| # | Question asked | SKILL.md field(s) populated | Why it matters to agent runtime |
|---|---|---|---|
| 1 | What is the project name and purpose? | `project_name` + `purpose` | Establishes the identity block all agents load as context; without it, agents have no anchor for relevance filtering |
| 2 | What is the domain or type of project? | `domain` | Helps agents understand the problem space and avoid irrelevant suggestions (e.g. a knowledgebase domain suppresses web-server scaffolding proposals) |
| 3 | What is the tech stack? | `tech_stack` | Gates language-specific tooling decisions — e.g. pytest vs jest, `pathlib` vs `os.path`, requirements.txt vs pyproject.toml |
| 4 | What is the target environment? | `target_environment` | Informs portability requirements; agents enforce Windows 11 + Linux compatibility and cloud-deployability as stated in this field |
| 5 | What are the key services or integrations? | `key_services` | Prevents agents from suggesting alternatives to locked-in dependencies (e.g. avoids proposing GitLab when GitHub API is listed here) |
| 6 | What are the constraints and risks? | `constraints_and_risks` | The four system constraints (ROOT_ISOLATION, PATH_STRICTNESS, PORTABILITY, DEPENDENCY_STRATEGY) are captured here and enforced uniformly by all agents on every sub-project |
| 7 | What is the TDD strength? | `tdd_strength` | Gates whether agents must write tests first; asking up-front avoids per-agent negotiation (`medium` = test-first for new features, tests required for all bug fixes) |
| 8 | What are the workflow preferences? | `workflow_quirks` | Ensures consistent branch naming, commit style, and merge strategy across all agents — no agent invents its own conventions |
| 9 | What are the model preferences? | `model_preferences` | Allows cost/quality routing (Sonnet for complex work, Haiku for mechanical tasks) without per-session negotiation |

### Design note: one question at a time

The onboarding agent is instructed to ask questions **one at a time via the `ask_user` tool, never bundled**. This is deliberate:

- Bundling 9 questions produces vague, rushed answers that degrade every subsequent agent session
- Sequential questions allow the agent to adapt follow-up phrasing based on prior answers
- The increased friction is intentional — onboarding is a one-time ceremony, not a quick form

---

## Section 2: How SKILL.md drives agent behaviour

### The `status` gate

`SKILL.md` carries a front-matter `status` field:

```yaml
---
name: project-context
status: active   # or: bootstrap
---
```

This field is checked by `copilot-instructions.md` at the start of **every session**:

```
At the start of every session, check if .github/skills/project-context/SKILL.md
has status: active.

If it says status: bootstrap (or the file is missing), stop immediately and tell the user:
"Project context hasn't been set up yet. Please run the onboarding agent first."
Do not proceed with any work until onboarding is complete.
```

| Status | Meaning | Runtime effect |
|---|---|---|
| `status: active` | Onboarding is complete | All agents operate normally |
| `status: bootstrap` | Onboarding has not run | **All agents halt** with an explicit message; no work proceeds |

The gate is enforced at the repo level (via `copilot-instructions.md`), not inside each agent. This means new agents added to the stack inherit the gate for free.

### Which fields each agent class reads

All agents load the full `SKILL.md` context block via the skills system. However, different agent classes act primarily on different fields:

| Agent | Primary fields consumed | Why |
|---|---|---|
| **All agents** | `tdd_strength`, `status` | TDD behaviour and onboarding gate are universal |
| `devops-executor` | `constraints_and_risks`, `tech_stack`, `target_environment` | Executor enforces the four system constraints on every implementation task |
| `devops-documenter` | Dual-doc convention (embedded in SKILL.md), `workflow_quirks` | Documenter follows the `-agentic` / `-architect` naming pattern and commit conventions derived from SKILL.md |
| `devops-director` | `purpose`, `domain`, `key_services` | Director uses these to write well-scoped GitHub issues aligned to the project's problem space |
| `devops-lead` | `model_preferences`, `tech_stack`, `constraints_and_risks` | Lead uses model preferences for cost routing and constraints for architecture guardrails |
| `devops-qa` | `tdd_strength`, dual-doc convention | QA checks test coverage against the stated TDD level and verifies both doc artifacts exist |
| `devops-reviewer` | `constraints_and_risks`, `tech_stack` | Reviewer checks for constraint violations (ROOT_ISOLATION, PATH_STRICTNESS, etc.) |
| `devops-producer` | `workflow_quirks` | Producer enforces branch/merge conventions when planning sessions |

### Why SKILL.md is `.md` not JSON/YAML

SKILL.md is intentionally a **prose Markdown file**, not a structured data format. The reasons:

1. **The skills system loads it as a context block** — Copilot's skills mechanism injects the file's content as prose into the agent's context window. It is not parsed programmatically by any tool. A JSON or YAML file would appear as raw syntax in the context window, which degrades readability for the model.

2. **Human-readable by design** — An architect reviewing or editing SKILL.md should be able to read and update it without understanding a schema. The file is a specification *for humans and models equally*.

3. **Mixed content** — Some fields (like the dual-doc convention table) are richer as Markdown tables than as YAML keys. Forcing a schema would lose that expressiveness.

The tradeoff is that SKILL.md fields are not validated programmatically. An agent cannot assert `if skill["tdd_strength"] == "medium"` — it must interpret the prose. This is acceptable because the fields are stable and few, and any ambiguity is resolved at onboarding time.

### The skills system: how Copilot loads SKILL.md

Skills live at `.github/skills/<name>/SKILL.md`. The Copilot CLI skills system:

1. Discovers skill files by scanning `.github/skills/`
2. Surfaces them as available skills in the session UI
3. When a skill is active, **injects its full content** into the agent's context at session start
4. The `description` field in the front-matter (`name: project-context`) is what the agent references when invoking `skill: project-context`

For Forge, there is currently one skill: `project-context`. All agents are instructed to load it. The system is extensible — additional skills (e.g. `testing-conventions`, `api-design`) can be added without modifying existing agents.

---

## Section 3: The self-destruct pattern

### What happens

After populating SKILL.md, the project-onboarding agent removes itself from the repository:

```bash
git rm .github/agents/project-onboarding.agent.md
git commit -m "chore: remove onboarding agent after successful setup"
```

In this repo, the self-destruct commit is **`0db3213`**.

### Why it self-destructs

The self-destruct is a **hard guard against accidental re-runs**:

- Re-running onboarding would overwrite a carefully tuned SKILL.md with fresh (potentially wrong) answers
- The template's README warns that onboarding is a one-time ceremony; removing the agent file makes this physically true
- Agents that no longer exist cannot be invoked — no configuration flag, no `--skip-onboarding`, no human error

### The tradeoff: irreversibility vs recoverability

| Side | Effect |
|---|---|
| **Irreversibility (the benefit)** | Once onboarding runs successfully, it cannot accidentally run again — the file is gone from git history's working tree |
| **Recoverability cost** | If re-onboarding is genuinely needed (e.g. the project pivots significantly), the file must be manually restored |

### How to recover if re-onboarding is needed

1. **Restore the agent file** from the template repository:
   ```bash
   # Fetch the file from the template repo's master branch
   gh repo clone m4ttsch3r/forge-0 /tmp/forge-template
   cp /tmp/forge-template/.github/agents/project-onboarding.agent.md \
      .github/agents/project-onboarding.agent.md
   ```
   Or: copy it from any other Forge-derived repo that hasn't yet been onboarded.

2. **Reset SKILL.md status to `bootstrap`**:
   ```yaml
   ---
   name: project-context
   status: bootstrap
   ---
   ```
   This re-activates the onboarding gate — all agents will halt until onboarding completes again.

3. **Commit both changes**, run onboarding, let it self-destruct again.

> **Warning**: Resetting to `bootstrap` halts all agents immediately. Do not do this in the middle of an active session.

---

## Section 4: Agent choreography during setup

This section documents the exact sequence of events that produced the current state of this repository. It is both a historical record and a replicable template.

### Full setup sequence

```
1.  User invokes `project-onboarding` agent
     └─ Agent asks 9 questions via ask_user (one at a time, never bundled)

2.  Agent writes .github/skills/project-context/SKILL.md
     └─ Sets status: active; populates all 9 field groups

3.  Agent runs `git rm .github/agents/project-onboarding.agent.md` + commits
     └─ Self-destructs → commit 0db3213
     └─ Onboarding is now irreversible

4.  User invokes `devops-director`
     └─ Director interviews user about documentation requirements
     └─ Drafts 3 GitHub issues (#1 setup-agentic, #2 setup-architect, #3 dual-doc-convention)
     └─ Issues NOT filed yet — repo doesn't exist remotely

5.  GitHub repo created + code pushed
     └─ `gh repo create m4ttsch3r/forge-0 --public --source=. --remote=origin --push`
     └─ Issues filed via `gh issue create` for each of the 3 documentation items

6.  User invokes `devops-producer` to plan the first session
     └─ Producer reviews open issues, proposes session plan:
        Phase 0: Seed labels (ops prerequisite)
        Phase 1: Issue #3 (dual-doc convention — must exist before #1 and #2 can reference it)
        Phase 2: Issues #1 and #2 in parallel (setup docs)

7.  Labels seeded via `gh label create` (PowerShell)
     └─ Bash unavailable on Windows; scripts/seed-labels.sh not usable directly
     └─ Each label created individually via gh CLI in PowerShell
     └─ See documentation/labels.md for the full taxonomy

8.  `devops-documenter` implements each issue on task branches
     └─ Branch pattern: task/<kebab-slug> from master
     └─ One squash-merge commit per issue
     └─ Issue labelled `status: ready-for-qa` after implementation

9.  `devops-qa` validates acceptance criteria
     └─ Posts verdict comment on each issue
     └─ `devops-producer` closes issues after QA pass
```

### What the onboarding agent intentionally does NOT do

The onboarding agent is deliberately minimal — it answers "what is this project?" and no more. The following are **out of scope for onboarding** and belong in the ops backlog:

| Not done at onboarding | Rationale |
|---|---|
| Create GitHub issues | The repo may not exist yet at onboarding time; issues require a remote |
| Seed labels | Label seeding requires `gh` CLI auth and a remote repo; platform-specific (Bash vs PowerShell) |
| Set up CI/CD | Pipeline design is project-specific and typically requires more than 9 questions to specify correctly |
| Create milestones | Milestones are session-planning artifacts, owned by `devops-producer`, not setup tooling |

Keeping onboarding minimal means it is fast, reliable, and unlikely to fail mid-run — critical for a one-shot tool.

---

## Cross-reference

| Document | Audience | Content |
|---|---|---|
| `documentation/setup-agentic.md` | Users and agents | What Forge is, how to use it, operational checklists, label seeding, task-branch workflow |
| `documentation/setup-architect.md` | Human architects | This file — why decisions were made, agent choreography, SKILL.md internals |
| `documentation/dual-doc-convention.md` | All | The spec that requires both of the above to exist |
