
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$HOME/2ndBrain_RAG"
DATA_DIR="${RAG_FOLDER:-$HOME/2ndBrain_RAG}"
PYTHON_BIN="$(which python3 || true)"
[ -z "$PYTHON_BIN" ] && { echo "python3 not found"; exit 1; }

echo "🔧 Creating venv & installing requirements..."
cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "📦 Checking Ollama model (default: $OLLAMA_MODEL or llama3)..."
echo "   Make sure Ollama is running: https://ollama.com"
echo "   e.g., 'ollama pull llama3'"

echo "📄 Rendering LaunchAgent plist..."
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s#__PYTHON_BIN__#$PYTHON_BIN#g"         -e "s#__SCRIPT_PATH__#$PROJECT_DIR/rag_mcp_server.py#g"         -e "s#__DATA_PATH__#$DATA_DIR#g"         -e "s#__WORK_DIR__#$PROJECT_DIR#g"         "$PROJECT_DIR/com.2ndbrain.rag.plist.tmpl" > "$HOME/Library/LaunchAgents/com.2ndbrain.rag.plist"

echo "🚀 Loading LaunchAgent..."
launchctl unload "$HOME/Library/LaunchAgents/com.2ndbrain.rag.plist" 2>/dev/null || true
launchctl load "$HOME/Library/LaunchAgents/com.2ndbrain.rag.plist"

echo "✅ Done. API: http://localhost:8000/docs | Logs: /tmp/2ndBrain_RAG.log"
