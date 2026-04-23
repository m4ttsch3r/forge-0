# New project setup

## Prerequisites

- GitHub account
- GitHub personal access token with `repo` and `workflow` scopes
- GitHub Copilot subscription (for agentic features)
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/copilot-in-the-cli) installed

## Steps

### 1. Create repo from template

On GitHub, click **Use this template** → **Create a new repository**.

Or via CLI:
```bash
gh repo create my-project --template <owner>/copilot-project-template --private
gh repo clone my-project && cd my-project
```

### 2. Copy and configure MCP settings

```bash
cp .mcp.json.example .mcp.json
```

Edit `.mcp.json` and update the values for your environment.

### 3. Run project onboarding

Open GitHub Copilot CLI in this directory and invoke the onboarding agent:

```
/onboarding
```

Or in the Copilot chat panel:
```
@workspace run project onboarding
```

The onboarding agent will:
- Ask you ~9 questions about your project
- Populate `.github/skills/project-context/SKILL.md`
- Seed GitHub labels
- Create your first milestone
- Self-destruct (remove itself from the repo)

### 4. Start working

```bash
# Plan your first session
# In Copilot: use devops-producer to plan

# Start a task
git checkout -b task/my-first-feature

# After implementing
git checkout main
git merge --squash task/my-first-feature
git commit -m "feat: my first feature"
git push
```

## Daily workflow

1. **Session open**: invoke `devops-producer` to groom the backlog and get a session plan
2. **Implementation**: `devops-lead` plans, `devops-executor` implements
3. **Review**: `devops-reviewer` checks significant changes
4. **Session close**: `devops-producer` runs QA and closes resolved issues

## Branch conventions

| Pattern | Purpose |
|---------|---------|
| `main` | Stable, always deployable |
| `task/<slug>` | Work in progress |
| `fix/<slug>` | Bug fixes |
| `docs/<slug>` | Documentation only |
