# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Setup documentation** (`documentation/setup-agentic.md`): user-facing guide covering what Forge is, system constraints (ROOT_ISOLATION, PATH_STRICTNESS, PORTABILITY, DEPENDENCY_STRATEGY), repository structure, SKILL.md and its `status` field, label taxonomy and seeding on Windows, the task-branch workflow, dual-doc convention overview, and how to replicate the setup in a new environment (#1)
- **Setup documentation — architect version** (`documentation/setup-architect.md`): design-rationale guide covering the 9 onboarding questions and why each SKILL.md field matters to agent runtime, the `status: active` / `status: bootstrap` gate, which fields each agent class reads, why SKILL.md is prose not JSON/YAML, the self-destruct pattern and how to recover from it, and the full agent choreography sequence from onboarding through QA (#2)
