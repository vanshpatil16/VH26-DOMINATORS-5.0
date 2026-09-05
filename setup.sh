#!/bin/bash
# CodeGate Full Setup Script for AWS Ubuntu
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
SCALPEL_DIR="$FRONTEND_DIR/Scalpel"

echo "=========================================="
echo " CodeGate Setup — $REPO_ROOT"
echo "=========================================="

# 1. System dependencies
echo "[1/7] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y gcc build-essential python3-dev python3-pip python3-venv graphviz libgraphviz-dev git curl

# 2. Node.js v20
echo "[2/7] Setting up Node.js..."
if ! command -v node &>/dev/null || [[ "$(node -v)" != v20* ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
echo "  Node: $(node -v)  NPM: $(npm -v)"

# 3. Scalpel
echo "[3/7] Cloning Scalpel..."
if [ ! -d "$SCALPEL_DIR/src/scalpel" ]; then
  rm -rf "$SCALPEL_DIR"
  git clone https://github.com/SMAT-Lab/Scalpel.git "$SCALPEL_DIR"
  echo "  Scalpel cloned."
else
  echo "  Scalpel already present."
fi

# 4. Fix vite.config.ts using Python script file
echo "[4/7] Fixing vite.config.ts and package.json..."
python3 "$REPO_ROOT/scripts/fix_vite.py" "$FRONTEND_DIR"

# 5. npm install + build
echo "[5/7] Building frontend..."
cd "$FRONTEND_DIR"
npm install --legacy-peer-deps
npm run build
echo "  Built: $FRONTEND_DIR/dist/"

# 6. Python venv + packages
echo "[6/7] Setting up Python venv..."
cd "$REPO_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -q astor networkx graphviz pyyaml libcst requests httpx python-dotenv fastapi "uvicorn[standard]"
if [ -f requirements.txt ]; then
  pip install -q -r requirements.txt --ignore-requires-python 2>/dev/null || true
fi
pip install -q -e "$SCALPEL_DIR" --no-deps 2>/dev/null || true

# 7. Write .env
echo "[7/7] Writing .env..."
VENV_PYTHON="$REPO_ROOT/.venv/bin/python3"
ENV_FILE="$FRONTEND_DIR/.env"
grep -q "CODEGATE_PYTHON" "$ENV_FILE" 2>/dev/null || echo "CODEGATE_PYTHON=$VENV_PYTHON" >> "$ENV_FILE"
grep -q "PYTHONPATH" "$ENV_FILE" 2>/dev/null || echo "PYTHONPATH=$SCALPEL_DIR/src" >> "$ENV_FILE"
echo "  Written: $ENV_FILE"

# Smoke test
echo ""
echo "Running smoke test..."
cd "$REPO_ROOT"
RESULT=$(PYTHONPATH="$SCALPEL_DIR/src" "$REPO_ROOT/.venv/bin/python3" -m codegate.webapi - <<< 'f = open("a.txt")' 2>/dev/null || echo '{"ok":false}')
echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK - leaks:', d.get('summary',{}).get('leakCount','?')) if d.get('ok') else print('FAILED')" 2>/dev/null || echo "Smoke test inconclusive"

echo ""
echo "=========================================="
echo " Done! Run the app:"
echo "   cd $FRONTEND_DIR && npm run dev"
echo " Build Docker:"
echo "   cd $REPO_ROOT && docker build -t codegate ."
echo "=========================================="
