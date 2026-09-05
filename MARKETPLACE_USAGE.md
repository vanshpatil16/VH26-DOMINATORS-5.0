## 📋 How to Use from GitHub Marketplace

The GitHub Marketplace shows only the **step snippet** (starting with `- name:`).
You need the **complete workflow file** below.

### Step 1 — Create this file in your repo:
📁 `.github/workflows/leakguard.yml`

### Step 2 — Paste this complete YAML:

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
    permissions:
      contents: read

    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: LeakGuard CodeGate Analyzer
        uses: vanshpatil16/VH26-DOMINATORS-5.0@v1.0.1
        with:
          targets: .
          ensemble: 'true'
          changed-only: 'false'
```

That's it! Commit and push — LeakGuard will automatically scan on every push/PR.
