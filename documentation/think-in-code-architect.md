# Think in Code — Architect's Guide

> **Audience**: Human architects reviewing or extending the Forge agentic system.

## Context economics: why raw data in context is expensive

Every token in an LLM context window has a cost — not just financially, but cognitively. When a large block of raw data occupies the context:

1. **Token cost** — reading 20 log files might consume 40,000–100,000 tokens. At current model pricing that is significant, but more importantly it crowds out reasoning capacity.
2. **Compaction risk** — long contexts trigger compaction. Compaction summarises earlier turns, and the model may lose critical details that were in those turns. A session that started with a clear understanding of a constraint may lose that constraint to compaction midway through a task.
3. **Reasoning degradation** — LLMs perform better on focused prompts. A context polluted with raw data forces the model to "find the needle" inside its own window rather than receiving a pre-filtered signal. The quality of reasoning drops measurably as irrelevant tokens accumulate.

The Think in Code paradigm eliminates this class of problem by ensuring that **only the answer** ever enters the main context, not the raw data used to derive it.

---

## The paradigm as a forcing function

Agents are code generators, not data processors. This is the core insight.

An LLM is extremely capable of writing a Python script that walks a directory tree and prints a summary. It is less capable of accurately processing the contents of that directory tree when everything is dumped into its context. The LLM's strength is in code generation and structured reasoning, not in being a search engine over raw bytes.

Think in Code operationalises this insight:

- The agent generates a precise, targeted script
- The script runs outside the model, in a real Python interpreter
- The interpreter returns only the result
- The agent reasons over the result

This is the correct division of labour. Python is not inside the LLM; the LLM writes Python that runs outside itself.

---

## How hooks enforce it (context-mode)

In context-mode, the Forge environment installs a `PreToolUse` hook that intercepts raw Read and Shell tool calls:

```
PreToolUse: Read → check if this is an analysis read
  if file > N lines AND purpose is "to find X": nudge → ctx_execute
  else: allow (e.g. small config read, single-line check)

PreToolUse: Shell → check if output is large
  if stdout > N lines AND purpose is "to inspect Y": nudge → ctx_execute
  else: allow (e.g. git status, pip install)
```

The hook does not block — it nudges. It adds a note to the model's next prompt: "Consider using ctx_execute instead of reading this file directly." Models respond well to this nudge because the instructions have already primed them with the paradigm.

`ctx_execute` is a sandbox tool:
- Accepts a Python string
- Runs it in an isolated subprocess
- Returns only stdout (capped at N lines / M tokens)
- The script source itself is never placed in the main context window

This means the script generation and the result retrieval are both context-efficient.

---

## Forge-specific rationale

Forge is Python-first. Every sub-project uses Python, `pathlib.Path`, and stdlib tools. This makes script generation trivially natural:

- The model already knows Python well
- Forge conventions (`pathlib.Path`, no hardcoded paths) map directly to good script hygiene
- Scripts generated for analysis can often be lightly adapted into production utilities

The `pathlib.Path` + `subprocess` pattern is the standard approach:

```python
from pathlib import Path
import subprocess

root = Path(__file__).parent
result = subprocess.run(
    ["python", "-m", "pytest", "--collect-only", "-q"],
    cwd=root,
    capture_output=True,
    text=True
)
print(result.stdout.split("\n")[-2])  # print only the summary line
```

Scripts written this way are OS-agnostic (Windows and Linux), self-contained, and easy to reason about.

---

## Trade-offs

### Script overhead vs context savings

Writing a script has overhead: the model must generate it, it must be executed, and the result must be returned. For very small reads, this overhead may exceed the savings.

**Guidance**: Apply Think in Code when:
- The data source has more than ~50 lines, OR
- More than two files/endpoints would need to be read, OR
- The read is inside a loop or repeated pattern

**It is acceptable to read a file directly when:**
- The file is a small config (< 30 lines) and the full content is needed for editing
- A single-line check is sufficient (`head -1`, `tail -1`)
- The model needs to see the exact content to make a targeted `edit` call (e.g. reading before editing)

The key distinction: **reading to understand** (should be a script) vs **reading to edit** (direct read is appropriate).

### False positives from the hook

The `PreToolUse` nudge may fire on legitimate small reads. The model should evaluate the nudge and override it when the read is genuinely appropriate. The nudge is advisory, not mandatory.

---

## Relationship to other Forge principles

| Principle | Relationship |
|-----------|-------------|
| `PATH_STRICTNESS` (`pathlib.Path` only) | Think in Code scripts must follow this — same rule applies inside scripts |
| `ROOT_ISOLATION` | Scripts that analyse sub-projects must not import from root; use `subprocess` if cross-boundary |
| `PORTABILITY` | Scripts should run on Windows and Linux — `pathlib.Path` ensures this |
| Dual-doc convention | This file is the architect half; `think-in-code-agentic.md` is the user half |

---

## Design decision log

| Decision | Rationale |
|----------|-----------|
| Python-only (not shell scripts) | Python is cross-platform; shell scripts differ between Windows/Linux. Python is already the project language. |
| Print-only output (not return values) | Scripts run in subprocesses; stdout is the universal return channel. Keeps the interface simple. |
| Temp file approach when no ctx_execute | Lowest common denominator — works in any environment without special tooling |
| Nudge (not block) in PreToolUse hook | Hard blocks create friction and false positives. Nudges are lighter and trust the model to make the right call after being reminded. |

---

_See also: `documentation/think-in-code-agentic.md` for the practical usage guide._
