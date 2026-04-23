# Copilot Instructions

## Tool selection hierarchy

When working in this project, prefer tools that avoid flooding context with raw output.

1. **Batch & index first** — run multiple commands, index output, search for what you need
2. **Targeted reads** — use view/read tools when you need to edit; use sandbox execution when you need to analyse
3. **Chain commands** — `&&` over separate calls; suppress verbose output with `--quiet`, `--no-pager`, `| head`

---

# Workspace Workflow

## Task branch workflow

Every task must happen on its own branch:

1. **Start of task**: `git checkout -b task/<kebab-slug>` from `main`
2. **All commits** go on the task branch
3. **Close**: squash-merge to `main` → single commit → push → delete branch → open PR if working collaboratively

Use a descriptive slug that matches the task (e.g. `task/add-auth`, `task/fix-login-redirect`).

## User availability

The user is **always available** unless the session is running in autopilot mode.

- **Always use `ask_user` with multi-choice options** for design decisions, ambiguity, and scope questions
- **Never assume past unclear decisions** — interrogate the user instead
- Autopilot mode is the only exception — proceed autonomously and note decisions in the brief

## Onboarding check

**At the start of every session**, check if `.github/skills/project-context/SKILL.md` has `status: active`.

If it says `status: bootstrap` (or the file is missing), stop immediately and tell the user:

> "Project context hasn't been set up yet. Please run the onboarding agent first: tell me 'run the project-onboarding agent'."

Do **not** proceed with any work until onboarding is complete.

## TDD

Apply TDD principles proportionally to the `tdd_strength` field in `project-context/SKILL.md`:

| Value | Meaning |
|-------|---------|
| `none` | No tests required |
| `light` | Tests for critical paths and regressions only |
| `medium` | Test-first for new features; tests for all bug fixes |
| `strong` | Strict red-green-refactor; no untested code merged |

## Skills system

Project-specific context lives in `.github/skills/`. Load the relevant skill(s) at the start of work.

**Maintenance obligations** (applies to all agents):
- **New technology encountered** → propose a new skill in `.github/skills/<name>/SKILL.md`
- **New learning about existing technology** → update the relevant `SKILL.md` immediately before closing
- Skills are the source of truth for service-specific knowledge

---

# Agent roles quick reference

| Agent | Role | Closes issues? |
|-------|------|----------------|
| `devops-producer` | Session planner, backlog groomer, **sole issue closer** | ✅ Yes (after QA) |
| `devops-director` | Intake interviewer → GitHub issues | ❌ Never |
| `devops-lead` | Architecture, planning, orchestration | ❌ Marks ready-for-qa only |
| `devops-executor` | Hands-on implementation | ❌ Never |
| `devops-reviewer` | Security/maintainability review | ❌ Never |
| `devops-documenter` | Wiki, CHANGELOG, user guides | ❌ Never |
| `devops-qa` | Validates acceptance criteria; posts verdict comments | ❌ Never |

---

# GitHub issue backlog

GitHub issues are the **primary backlog** for all project work.

**Workflow:**
- **Session open** — fetch open issues; surface relevant ones as context
- **Session close** — mark resolved issues `status: ready-for-qa` and post an implementation summary comment; **do not close issues directly** — devops-producer runs devops-qa and closes after validation

**Issue format** — prefix titles with area: `feature:`, `bug:`, `docs:`, `ops:`, `security:`

## Agent signature block convention

Every agent appends this block to every GitHub issue or comment it authors:

```
---
_Agent: devops-<name> · Model: <model-in-use> · Skills: <active-skills>_
```

Provides traceability for every automated action — who did it, which model, what context was active.
