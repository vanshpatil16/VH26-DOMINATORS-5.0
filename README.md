# CodeGate — Static Resource-Leak Analyzer for Python

> **Hackathon MVP — 30h build on Scalpel + LibCST**

CodeGate answers: *“After a resource is acquired, is cleanup guaranteed on every reachable path while it remains locally owned?”*

```python
def read_file(path):
    f = open(path)
    data = f.read()
    if not data:
        return None      # ← LEAK: f not closed on this path
    f.close()
    return data
```

Scalpel says `open` + `close` → maybe safe. CodeGate reasons about **control flow**:

```
open → read → if not data → return   (LEAK)
               └→ close → return      (SAFE)
→ DEFINITE LEAK
```

## Architecture

```
Python source
     |
 +---+---+
 |       |
 v       v
Scalpel  LibCST
(CFG)    (CST, scopes, formatting)
 |       |
 +---+---+
     |
     v
CodeGate: alias tracking + liveness DFS + ownership + fix
```

See `ARCHITECTURE.md` for full division of responsibility.

## Quick Start

```bash
pip install -e .   # or pip install libcst networkx astor astunparse graphviz
# analyze a file
python -m codegate.cli demos/vuln.py --fix   # or: codegate demos/vuln.py
python -m codegate.cli tests/fixtures/ --json
```

## What it detects

- `open(path)` / `socket.socket()` / `subprocess.Popen` / … → `close()` leaks
- Alias: `g = f; g.close()` counts as closing `f`
- Reassign: `f = open(); f = open()` leaks first
- Branches: every `if`/`else` return path checked
- Loops: post-loop close is safe, missing close is leak
- Ownership escape: `return f` considered transferred (configurable)

## What it fixes

LibCST with-transform preserves comments & formatting:

```python
# before
f = open(path)
data = f.read()
f.close()

# after
with open(path) as f:
    data = f.read()
```

## Tests

```bash
python -m pytest tests -q
python tests/test_analyzer.py
```

---

## 🚀 Ready-to-Use GitHub Action Workflow

To use LeakGuard in **any Python repository on GitHub**, create `.github/workflows/leakguard.yml` and copy-paste the full workflow below:

```yaml
name: LeakGuard Security Audit

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  leakguard-scan:
    name: CodeGate Resource Leak Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: LeakGuard CodeGate Analyzer
        uses: vanshpatil16/VH26-DOMINATORS-5.0@v1.0.0
        with:
          license-key: ${{ secrets.LEAKGUARD_LICENSE_KEY }}
          ensemble: 'true'
```

> **Note on GitHub Marketplace Snippet:** GitHub Marketplace automatically generates a single-step snippet (`- name:`). If creating a *new* file in `.github/workflows/`, use the complete `name / on / jobs / steps` YAML above!

### Action Inputs
| Input | Description | Default |
| :--- | :--- | :--- |
| `license-key` | LeakGuard License Key (Community, Team, Business, Enterprise) | `community` |
| `targets` | Files or directories to scan | `.` |
| `ensemble` | Include ruff + CodeGate ensemble verification | `true` |
| `changed-only` | Scan only changed files against base ref | `false` |
