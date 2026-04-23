---
name: project-context
description: Core context for this project. Always load this skill at the start of every session.
status: active
---

# project-context

## Project overview
**Name**: Forge
**Purpose**: Self-contained mono-repo prototype station and knowledgebase incubator. Prepares ideas and solutions for real-world use with strict encapsulation, OS-agnostic design (Windows 11 + Linux), and automation-pipeline readiness.
**Domain**: Knowledgebase design, creation, and management. Prototype / incubator environment.
**Status**: Active

## Tech stack
- **Primary language**: Python
- All solutions must run on Windows 11 and Linux without modification (or with trivial adaptation)
- Solutions must be easy to plug into automation pipelines
- Each sub-project keeps its own logs and documentation inside its own folder structure
- Use `pathlib.Path` exclusively — no hardcoded path strings

## Target environment
- **Primary**: Local machine (Windows 11 + Linux)
- **Ideal**: Cloud-deployable; adaptability to cloud environments is a design goal
- **CI/CD**: Solutions should be pipeline-friendly

## Key services / integrations
- GitHub API
- VS Code API (Extension / workspace integration)

## Constraints and risks
**System constraints (enforced on every sub-project):**
1. **ROOT_ISOLATION** — Sub-projects must NOT depend on root-level imports
2. **PATH_STRICTNESS** — Use `pathlib.Path`; no hardcoded path strings
3. **PORTABILITY** — Every sub-folder must be valid as a standalone Git repo
4. **DEPENDENCY_STRATEGY** — Local `requirements.txt` per `Project-XX` folder

## Development methodology
**TDD strength**: `medium`
- Test-first for new features
- Tests required for all bug fixes
- Critical paths must have regression coverage

## Workflow preferences
- Default workflow: task branches (`task/<kebab-slug>`), squash-merge to `main`, delete branch after merge
- Commit messages follow conventional commits style
- Default model allocation applies (Sonnet for complex, Haiku for simple)

## Model preferences
default — Sonnet for complex/architectural work, Haiku for simple/mechanical tasks

## Skills maintained for this project
| Skill | Description |
|-------|-------------|
| `project-context` | This file — core project context |

## Update protocol
Update this skill whenever: the stack changes, new services are added, methodology is adjusted, or important discoveries are made about the codebase.
