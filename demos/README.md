# Demos

- `vuln.py` — core leak example from spec (`read_file` with early return)
- `socket_leak.py` — `socket.socket()` leak with branch

Run:

```bash
codegate demos/vuln.py
codegate demos/vuln.py --fix-dry
codegate demos/socket_leak.py --json
codegate tests/fixtures --json
```
