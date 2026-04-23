# Dual-Documentation Convention

> **Scope**: Applies to ALL significant work in the Forge repository and every sub-project within it.

## What counts as "significant work"?

A piece of work is **significant** — and therefore requires dual documentation — when it falls into any of these categories:

| Category | Examples |
|----------|----------|
| **New feature** | A new capability added to an existing sub-project or the repo root |
| **New agent** | Any new `.agent.md` file or agentic workflow definition |
| **New sub-project** | A new `Project-XX/` folder introduced to the monorepo |
| **Major refactor** | Structural changes that alter public interfaces, data flows, or agent choreography |

Minor changes (typo fixes, trivial config tweaks, label changes) do **not** require dual documentation.

---

## The two required artifacts

Every significant piece of work must produce **both** of the following documentation artifacts:

| Artifact | Suffix / section | Audience | Required content |
|----------|-----------------|----------|-----------------|
| **Agentic / general-users** | `-agentic.md` or `## For users` | Anyone using Forge or its sub-projects | What was built, how to use it, what changed — standard user-facing docs and a CHANGELOG entry |
| **Human architect** | `-architect.md` or `## For architects` | A human reviewing or extending the agentic system | Why decisions were made, tradeoffs evaluated, agent choreography and reasoning |

Neither artifact is optional. Both must be present before an issue moves to `status: ready-for-qa`.

---

## Naming conventions

You may choose **either** naming pattern per work item. Be consistent within a single work item:

### Option A — Separate files (preferred for larger work items)

```
<topic>-agentic.md
<topic>-architect.md
```

Example:
```
setup-agentic.md     ← user-facing setup guide
setup-architect.md   ← design rationale and agent choreography notes
```

### Option B — Paired H2 sections in a single file (preferred for smaller work items)

```markdown
# <Topic>

## For users
...user-facing content...

## For architects
...design rationale and agent choreography...
```

---

## Where docs live

| Scope | Location |
|-------|----------|
| Sub-project documentation | `<Project-XX>/docs/` |
| Repo-wide / operational documentation | `documentation/` |

Always keep documentation co-located with the work it describes. If a sub-project doc evolves into repo-wide guidance, promote it to `documentation/`.

---

## devops-qa checklist item

When validating any issue that meets the "significant work" threshold, **devops-qa must verify**:

> Verify both agentic and architect doc artifacts exist per `documentation/dual-doc-convention.md`

This check must appear as an explicit row in the QA verdict table before the issue can receive a `✅ Pass`.
