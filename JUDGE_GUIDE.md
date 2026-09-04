# CodeGate Judge Guide

## One-Line Explanation

CodeGate is a path-sensitive static analyzer for Python that detects resource leaks, explains the exact control-flow path causing the leak, and can generate a safer fix.

It checks files, sockets, databases, HTTP clients, and processes.

## The Problem

A basic linter may only check whether an `open()` call and a `.close()` call exist somewhere in the function. That is not enough:

```python
def read_file(path):
    f = open(path)
    data = f.read()
    if not data:
        return None       # f is leaked on this path
    f.close()
    return data
```

The close call exists, but it is not guaranteed to execute. CodeGate checks every reachable control-flow path.

## High-Level Architecture

```text
Python source
     |
     v
Frontend editor
     |
     v
Node API bridge
     |
     v
Python Web API
     |
     +--> Python AST parsing
     +--> Match-statement desugaring
     +--> Scalpel control-flow graph
     +--> Resource and alias tracking
     +--> Path-sensitive DFS analysis
     +--> Exception-safety analysis
     +--> LibCST autofix
     |
     v
JSON result: report + AST + CFG + trajectory + fix
```

## Repository Structure

### Root Files

- `README.md`: Project overview, supported leaks, CLI usage, and GitHub Action usage.
- `ARCHITECTURE.md`: Detailed design decisions and division of responsibility between Scalpel, LibCST, and CodeGate.
- `pyproject.toml`: Python package metadata, dependencies, and CLI entry point.
- `action.yml`: Reusable GitHub Action configuration for CI/CD scanning.
- `demos/`: Vulnerable and safe examples used for demonstrations.
- `tests/`: Automated tests and Python fixtures.
- `frontend/`: React user interface and Node server.
- `codegate/`: Python analysis engine.

## Python Backend: `codegate/`

### Entry Points

- `cli.py`: Command-line interface. Supports file or directory analysis, JSON output, CFG output, autofix, and ensemble mode.
- `webapi.py`: One-shot JSON API used by the graphical interface. It accepts source code and returns the complete analysis result.
- `__main__.py`: Allows the package to run with `python -m codegate`.

### Main Analysis

- `analyzer.py`: Core leak-detection engine. It tracks resource acquisition, cleanup, aliases, reassignment, branches, loops, returns, ownership transfers, and exception paths.
- `config.py`: Defines tracked resource APIs and their release methods.

Examples:

```text
open()                    -> close()
socket.socket()           -> close()
sqlite3.connect()         -> close()
subprocess.Popen()        -> wait(), kill(), terminate()
httpx.AsyncClient()       -> aclose()
```

- `imports.py`: Resolves imported and aliased names so calls such as `io.open()` can be recognized.
- `scalpel_patch.py`: Builds the Scalpel control-flow graph and applies local fixes for Scalpel edge cases.
- `desugar.py`: Converts `match` statements into an easier-to-analyze branching form.

### Reporting and Explainability

- `report.py`: Formats terminal and JSON reports.
- `artifacts.py`: Converts the Python AST and Scalpel CFG into JSON for the frontend.
- `trajectory.py`: Records the analysis stages and timing:

```text
parse -> desugar -> cfg -> resources -> paths -> exceptions -> fix
```

This makes the verdict explainable instead of presenting only a yes/no result.

### Autofix

- `fix.py`: Uses LibCST to generate formatting-preserving fixes.

Example transformation:

```python
f = open(path)
data = f.read()
f.close()
```

becomes:

```python
with open(path) as f:
    data = f.read()
```

LibCST is used because it preserves comments and source formatting better than plain text replacement.

### Ensemble Verification

- `ensemble.py`: Combines Semgrep and Ruff as fast pre-filters, then uses CodeGate's CFG analysis to verify their findings.
- `semgrep/rules.yml`: Semgrep rules for possible resource leaks.

The ensemble can classify a finding as:

- Confirmed path leak
- Confirmed exception-unsafe code
- Refuted as safe
- Unverified

## Frontend: `frontend/`

### React Application

- `client/src/App.tsx`: Defines application routes such as `/`, `/dashboard`, `/graph`, and `/codegate`.
- `client/src/pages/Codegate.tsx`: Main CodeGate workspace. It supports editing code, demo selection, file upload, analysis, autofix, and ensemble verification.

### Result Visualizations

The components in `client/src/components/codegate/` show different views of the same backend result:

- `ReportTab.tsx`: Human-readable leak cards and findings.
- `TrajectoryTab.tsx`: Step-by-step backend analysis timeline.
- `AstTreeTab.tsx`: Parsed Python abstract syntax tree.
- `CfgGraphTab.tsx`: Control-flow graph with leak and safe-path highlighting.
- `EnsembleTab.tsx`: Ruff and Semgrep results verified by CodeGate.

### API Communication

- `client/src/lib/codegate.ts`: TypeScript response types, API client, and demo snippets.
- `server/codegate-api.ts`: Node bridge between the frontend and Python analyzer.

The request flow is:

```text
Browser
  -> POST /api/codegate/analyze
  -> Node server
  -> python -m codegate.webapi -
  -> JSON analysis result
  -> Browser visualizations
```

## How the Analyzer Works

1. **Parse**: Python source is converted into an AST.
2. **Desugar**: Constructs such as `match` are normalized into branch-like logic.
3. **Build CFG**: Scalpel creates basic blocks and edges for functions.
4. **Find resources**: CodeGate identifies calls such as `open()` and `socket.socket()`.
5. **Track state**: The analyzer tracks which resource is live and which variables refer to it.
6. **Explore paths**: A DFS walks the CFG and evaluates branches, loops, returns, and cleanup calls.
7. **Handle aliases**: `g = f; g.close()` is recognized as closing the original resource.
8. **Check ownership**: Returning or transferring a resource can be treated as giving ownership to another component.
9. **Check exceptions**: A resource can still leak if an intermediate call raises before cleanup.
10. **Report and fix**: CodeGate returns evidence and can generate a `with`-statement fix.

## Important Differentiator

The key difference from a simple pattern-based linter is path sensitivity:

> CodeGate does not only ask whether a close call exists. It asks whether cleanup is guaranteed on every reachable path while the resource is still owned.

That allows it to detect:

- Early-return leaks
- Branch-specific leaks
- Loop leaks
- Reassignment leaks
- Alias-based leaks
- Exception-unsafe cleanup
- Multiple resource interactions
- Safe `with` and `try/finally` patterns

## Judge Presentation Script

> Our project is CodeGate, a path-sensitive static analyzer for Python resource leaks.
>
> The problem is that traditional pattern-based tools may see both an acquire call and a close call, but they do not always understand whether the close is reachable on every execution path. CodeGate builds a control-flow graph using Scalpel and performs its own data-flow analysis over that graph.
>
> We track resources, aliases, ownership, reassignment, branches, loops, and exception paths. For example, if `g = f` and then `g.close()` is called, CodeGate understands that the original resource was closed. If a function returns early before closing the resource, CodeGate reports the exact leaking path.
>
> The frontend sends source code through a Node bridge to the Python Web API. The result contains a report, AST, CFG, analysis trajectory, and optional autofix. The CFG view shows where the leak happens, while the trajectory explains how the backend reached the verdict.
>
> For fixes, we use LibCST so comments and formatting are preserved while unsafe code can be converted into a safer `with` statement. We also support an ensemble mode where Ruff and Semgrep provide fast candidate findings and CodeGate verifies whether those findings are real leaks.

## Useful Demo Commands

```bash
# Install the Python package
pip install -e .

# Analyze one file
python -m codegate.cli demos/vuln.py

# Show JSON output
python -m codegate.cli demos/vuln.py --json

# Generate an autofix
python -m codegate.cli demos/vuln.py --fix

# Run the test suite
python -m pytest tests -q
```
