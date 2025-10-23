
# 🧠 2ndBrain_RAG (+Local Ollama chat)

Local Retrieval-Augmented search with:
- Persistent ChromaDB
- Auto reindex on file changes (watchdog)
- Ollama-powered **/chat** endpoint (default model: `llama3`)
- MCP-ready FastAPI server
- macOS LaunchAgent autostart via installer script

## Install
```bash
unzip 2ndBrain_RAG_ollama.zip -d ~/
cd ~/2ndBrain_RAG
bash scripts/install.sh
```

Ensure **Ollama** is installed and running:
- Install: https://ollama.com
- Pull model: `ollama pull llama3` (or set `export OLLAMA_MODEL=mistral` and pull it)

## Run
```bash
# manual
source .venv/bin/activate
uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000
# or wait for LaunchAgent autostart on reboot/login
```

## Endpoints
- `GET /status`
- `POST /ingest?full_rebuild=true|false`
- `GET /search?q=...&k=5`
- `POST /chat` body:
  ```json
  { "query": "What's in the standard?", "k": 5 }
  ```

## Claude Desktop (MCP)
Edit `~/.mcp/config.json`:
```json
{
  "servers": {
    "local-rag": {
      "command": "python",
      "args": ["/Users/YOUR_USER/2ndBrain_RAG/rag_mcp_server.py"]
    }
  }
}
```
