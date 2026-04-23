# Think in Code — Agentic Guide

> **Audience**: Anyone using Forge or working with Forge agents — developers, operators, contributors.

## What it means

"Think in Code" means: **when you need to learn something from data, write a script that extracts and prints only the answer.**

Instead of reading twenty files into context to find the three lines that matter, you write a short Python script that searches those files and prints just the summary. The script runs outside context (in a subprocess or sandbox), and only the result — a few lines — comes back.

This applies to every Forge agent. It is a mandatory operating principle, not an optional optimisation.

---

## When it applies

| Category | Examples |
|----------|---------|
| **File analysis** | Counting functions, finding class definitions, checking import usage, summarising folder structure |
| **Log inspection** | Searching for ERROR lines, extracting timestamps, spotting anomaly patterns |
| **Data counting** | Tallying test cases, counting dependencies, measuring coverage |
| **API response processing** | Filtering GitHub issue lists, extracting fields from JSON, aggregating results |

A good rule of thumb: if you find yourself thinking "I need to read several files to figure out X", you should write a script that finds X instead.

---

## Before and after examples

### 1 — Find errors in logs

**Before (raw read)**
```
# Agent reads 20 log files into context one by one
read("logs/app-2024-01-01.log")
read("logs/app-2024-01-02.log")
# ... 18 more reads ...
# Agent reasons over thousands of lines in context
```

**After (Think in Code)**
```python
from pathlib import Path

log_dir = Path("logs")
errors = []
for log_file in sorted(log_dir.glob("*.log")):
    for line in log_file.read_text(encoding="utf-8").splitlines():
        if "ERROR" in line:
            errors.append(f"{log_file.name}: {line.strip()}")

print(f"Total errors found: {len(errors)}")
for e in errors[:20]:  # print first 20 only
    print(e)
```
→ Context receives: `Total errors found: 4` and four lines. Done.

---

### 2 — List sub-projects and their sizes

**Before (raw read)**
```
# Agent runs ls, reads README for each folder, reads requirements.txt ...
# Hundreds of lines flow into context
```

**After (Think in Code)**
```python
from pathlib import Path

root = Path(".")
for d in sorted(root.iterdir()):
    if d.is_dir() and not d.name.startswith("."):
        req = d / "requirements.txt"
        dep_count = len(req.read_text().splitlines()) if req.exists() else 0
        py_files = len(list(d.rglob("*.py")))
        print(f"{d.name:30s}  {py_files:4d} .py files  {dep_count:3d} deps")
```
→ Context receives: a tidy table. No raw file contents.

---

### 3 — Count functions across a codebase

**Before (raw read)**
```
# Agent reads every .py file, manually counts `def ` occurrences in context
```

**After (Think in Code)**
```python
from pathlib import Path
import re

root = Path(".")
count = sum(
    len(re.findall(r"^\s*def ", f.read_text(encoding="utf-8"), re.MULTILINE))
    for f in root.rglob("*.py")
)
print(f"Function definitions: {count}")
```
→ Context receives: `Function definitions: 247`

---

### 4 — Fetch a webpage and find relevant content

**Before (raw fetch)**
```
# Agent fetches full HTML page → thousands of tokens in context
```

**After (Think in Code / context-mode)**
```
ctx_fetch_and_index("https://example.com/docs")
ctx_search "authentication token"
```
→ Context receives: only the paragraphs that matched.

---

## How to write a good analysis script

1. **Print only the result** — never echo raw input data. If you're about to `print(file_content)`, stop and print a summary instead.
2. **Use `pathlib.Path`** exclusively — no hardcoded path strings. This keeps scripts portable between Windows and Linux.
3. **Keep it self-contained** — only import stdlib modules (or modules already required by the sub-project). The script should run with no setup.
4. **Limit output** — if there might be many results, print the first N and a total count.
5. **Handle missing files gracefully** — check `.exists()` before reading; print a clear message if data is absent.

---

## How to run it

### When context-mode (`ctx_execute`) is available

```
ctx_execute("""
from pathlib import Path
# ... script body ...
print(result)
""")
```

`ctx_execute` runs the script in a sandbox, captures stdout, and returns only that. The script source never enters the main context window.

### When context-mode is not available

Write to a temp file, run it, delete it:

```python
# In a powershell/bash call:
python _tmp_analysis.py
# then: Remove-Item _tmp_analysis.py  (or rm _tmp_analysis.py)
```

Always delete the temp file after use — don't leave analysis scripts in the repo.

---

## Quick reference

| Rule | Detail |
|------|--------|
| Scripts print only the result | Never raw input |
| Use `pathlib.Path` | No hardcoded paths |
| Python preferred | Matches Forge's stack |
| Self-contained | stdlib only unless deps already installed |
| Delete temp files | Keep working tree clean |

---

_See also: `documentation/think-in-code-architect.md` for the rationale and design decisions behind this paradigm._
