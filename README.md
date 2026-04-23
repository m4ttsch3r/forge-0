# {{project-name}}

> Bootstrapped from [copilot-project-template](https://github.com/your-org/copilot-project-template)

A GitHub Copilot CLI project template with a full multi-agent stack, structured methodology, and a self-guided onboarding flow.

## First use

1. Use this template to create a new repo (GitHub: "Use this template" button)
2. Clone your new repo
3. Open in Copilot CLI
4. Run the onboarding agent: tell Copilot **"run the project-onboarding agent"**

The onboarding agent will ask you ~9 questions about your project, then:
- Populate `.github/skills/project-context/SKILL.md` with your project context
- Seed your GitHub issue labels
- Create your first milestone
- Self-destruct (it's a one-time setup tool)

After onboarding, use `devops-producer` to plan sessions and `devops-lead` to implement.

## Agents

| Agent | Purpose |
|-------|---------|
| `devops-director` | Turns ideas into GitHub issues |
| `devops-producer` | Plans sessions, grooms backlog, closes issues |
| `devops-lead` | Architecture, implementation orchestration |
| `devops-executor` | Hands-on implementation |
| `devops-reviewer` | Security & quality review |
| `devops-documenter` | Wiki, CHANGELOG, user guides |
| `devops-qa` | Validates issue acceptance criteria |
| `project-onboarding` | One-time setup — self-destructs after use |

## Workflow

- All work on feature branches (`feature/xyz`, `task/xyz`)
- Changes land on `main` via pull requests
- GitHub issues are the backlog — `devops-producer` manages them
- Sessions open with a grooming pass; sessions close with issues marked `status: ready-for-qa`

## Skills

`.github/skills/project-context/SKILL.md` is the heart of the template — it describes your specific project and tells all agents how to behave. Populated by the onboarding agent.

## Setup requirements

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) installed
- `jq` installed (required by `scripts/seed-labels.sh`)
- A GitHub personal access token with `repo` scope (for label seeding)
