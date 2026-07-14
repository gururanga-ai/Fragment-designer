#!/bin/bash
# Start MAWM Agent Tools — backend (FastAPI) + frontend (Vite)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure Homebrew bin is in PATH (needed for npm shebang #!/usr/bin/env node)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# ── Find python3 ──────────────────────────────────────────────────────
PYTHON=""
for p in python3.12 python3.11 python3 /usr/local/bin/python3 /usr/bin/python3 /opt/homebrew/bin/python3; do
  if command -v "$p" &>/dev/null; then PYTHON="$p"; break; fi
done
if [ -z "$PYTHON" ]; then
  echo "❌ python3 not found. Install: /opt/homebrew/bin/brew install python"
  exit 1
fi
echo "✓ Python: $($PYTHON --version)"

# ── Find pip3 ─────────────────────────────────────────────────────────
PIP=""
for p in pip3.12 pip3.11 pip3 /usr/local/bin/pip3 /opt/homebrew/bin/pip3; do
  if command -v "$p" &>/dev/null; then PIP="$p"; break; fi
done
[ -z "$PIP" ] && PIP="$PYTHON -m pip"
echo "✓ pip: $PIP"

# ── Find npm ─────────────────────────────────────────────────────────
NPM=""
for p in npm /opt/homebrew/bin/npm /usr/local/bin/npm; do
  if command -v "$p" &>/dev/null || [ -x "$p" ]; then NPM="$p"; break; fi
done
if [ -z "$NPM" ]; then
  echo "❌ Node.js / npm not found. Run: /opt/homebrew/bin/brew install node"
  exit 1
fi
echo "✓ Node: $(node --version)  npm: $($NPM --version)"

echo ""
echo "Starting MAWM Agent Tools..."
echo ""

# ── Backend ───────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/backend"
echo "Installing Python dependencies..."
$PIP install -q -r requirements.txt
echo "Starting FastAPI backend on http://localhost:8000 ..."
$PYTHON main.py &
BACKEND_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"
if [ ! -d node_modules ]; then
  echo "Installing npm packages (first run — ~30 seconds)..."
  "$NPM" install
else
  echo "npm packages already installed."
fi
echo "Starting Vite frontend on http://localhost:5173 ..."
"$NPM" run dev &
FRONTEND_PID=$!

echo ""
echo "════════════════════════════════════════════"
echo "  Open http://localhost:5173 in your browser"
echo "  Press Ctrl+C to stop"
echo "════════════════════════════════════════════"
echo ""

cleanup() {
  echo "Stopping servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

wait $BACKEND_PID $FRONTEND_PID
