# Label taxonomy

This project uses a standardised label set. Labels are seeded by `scripts/seed-labels.sh`.

Every issue **must** have exactly one `type:` label and one `priority:` label.

## Type labels

| Label | Color | Use for |
|-------|-------|---------|
| `type: bug` | `#d73a4a` | Something broken / unexpected behaviour |
| `type: feature` | `#0075ca` | New capability or user-visible improvement |
| `type: security` | `#e8843a` | Vulnerability, hardening, access control |
| `type: ops` | `#0e8a16` | Operational / infrastructure task |
| `type: docs` | `#cfd3d7` | Documentation gap or inaccuracy |
| `type: support` | `#f9d0c4` | Support / investigation request |

## Priority labels

| Label | Color | Meaning |
|-------|-------|---------|
| `priority: very-low` | `#c2e0c6` | Nice to have |
| `priority: low` | `#a2d96a` | Pick up when convenient |
| `priority: mid` | `#f9a825` | Should be done this sprint |
| `priority: high` | `#f66a0a` | Do in the next session |
| `priority: very-high` | `#b60205` | Blocking / immediate action |

## Status labels

| Label | Color | Meaning |
|-------|-------|---------|
| `status: ready-for-qa` | `#8b5cf6` | Implementation complete; pending QA before closure |

## Seeding labels

```bash
GITHUB_TOKEN=<your-token> OWNER=<repo-owner> REPO=<repo-name> bash scripts/seed-labels.sh
```
