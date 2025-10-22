# Quick Reference Guide

**Fast lookup for common commands and configurations**

---

## Quick Start (30 seconds)

```bash
# 1. Install
bash scripts/install.sh

# 2. Start server
source .venv/bin/activate
uvicorn rag_mcp_server:app

# 3. Add documents
cp your_files.pdf ~/2ndBrain_RAG/

# 4. Search (in another terminal)
curl "http://localhost:8000/search?q=your+topic"

# 5. Ask questions
curl -X POST http://localhost:8000/chat \
  -d '{"query": "What is...?"}' \
  -H "Content-Type: application/json"
```

---

## API Endpoints

### GET /status
Check indexing status
```bash
curl http://localhost:8000/status

# Response:
{
  "rag_path": "/Users/you/2ndBrain_RAG",
  "db_path": "/Users/you/2ndBrain_RAG/.chroma",
  "documents_indexed": 42
}
```

### POST /ingest
Load and index documents
```bash
# Initial indexing
curl -X POST http://localhost:8000/ingest

# Full rebuild (clears old index first)
curl -X POST "http://localhost:8000/ingest?full_rebuild=true"

# Response:
{
  "status": "ok",
  "indexed_chunks": 150,
  "source_path": "/Users/you/2ndBrain_RAG"
}
```

### GET /search
Semantic document search
```bash
curl "http://localhost:8000/search?q=machine+learning&k=5"

# Parameters:
# q (required): search query
# k (optional, default=5): number of results

# Response:
{
  "query": "machine learning",
  "k": 5,
  "results": [
    {
      "source": "/path/to/file.pdf",
      "chunk_id": "/path/to/file.pdf::chunk_5",
      "content": "Machine learning is..."
    }
  ]
}
```

### POST /chat
RAG-based question answering
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main principles?",
    "k": 5,
    "system": "You are an expert",
    "model": "llama3"
  }'

# All fields except query are optional
# Response:
{
  "answer": "Based on the documents, [1]... [2]...",
  "citations": [
    {"index": 1, "source": "/path/to/file1.md"},
    {"index": 2, "source": "/path/to/file2.pdf"}
  ]
}
```

---

## Configuration

### Environment Variables
```bash
export RAG_FOLDER=/path/to/documents
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=mistral
```

### Common Tweaks (in code)

| Change | File | Line | Current | Typical |
|--------|------|------|---------|---------|
| Chunk size | utils/loader.py | 20 | 800 | 500-1200 |
| Chunk overlap | utils/loader.py | 20 | 120 | 50-200 |
| Embedding model | rag_mcp_server.py | 32 | all-MiniLM-L6-v2 | all-mpnet-base-v2 |
| Default k | rag_mcp_server.py | 53 | 5 | 1-20 |
| Server port | (CLI) | - | 8000 | 8000-8999 |

---

## Installation

### macOS (Automated)
```bash
cd ~/2ndBrain_RAG
bash scripts/install.sh
# Creates venv, installs deps, sets up LaunchAgent
```

### Manual (Any OS)
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Ollama (Required)
```bash
# Install from https://ollama.com
brew install ollama  # macOS

# Start service
ollama serve

# In another terminal, pull model
ollama pull llama3  # or: mistral, phi, neural-chat, etc.
```

---

## Common Commands

### Start Server
```bash
# Development (with auto-reload)
uvicorn rag_mcp_server:app --reload

# Production
uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000

# Different port
uvicorn rag_mcp_server:app --port 8001
```

### Test All Endpoints
```bash
# Status
curl http://localhost:8000/status

# Index
curl -X POST http://localhost:8000/ingest

# Search
curl "http://localhost:8000/search?q=test"

# Chat
curl -X POST http://localhost:8000/chat \
  -d '{"query":"test?"}' -H "Content-Type: application/json"

# API docs (in browser)
open http://localhost:8000/docs
```

### Manage Documents
```bash
# Add files
cp *.pdf ~/2ndBrain_RAG/
cp *.md ~/2ndBrain_RAG/
cp *.txt ~/2ndBrain_RAG/

# Trigger reindex (auto or manual)
curl -X POST http://localhost:8000/ingest

# Clear index
curl -X POST "http://localhost:8000/ingest?full_rebuild=true"

# Remove file
rm ~/2ndBrain_RAG/oldfile.pdf
# (Watcher will reindex automatically)
```

### Check Logs
```bash
# Server logs (if running in terminal)
# Scroll up in terminal

# macOS LaunchAgent logs
tail -f /tmp/2ndBrain_RAG.log

# Check if LaunchAgent is running
launchctl list | grep 2ndbrain
```

---

## Troubleshooting

### "Ollama error" in responses
```bash
# Make sure Ollama is running
ps aux | grep ollama

# If not, start it
ollama serve

# Check model is available
ollama list

# If missing, pull it
ollama pull llama3
```

### Port already in use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or use different port
uvicorn rag_mcp_server:app --port 8001
```

### No search results
```bash
# Check if documents are indexed
curl http://localhost:8000/status
# If documents_indexed is 0, run:

curl -X POST http://localhost:8000/ingest

# Check file format is supported
ls ~/2ndBrain_RAG/
# Look for .txt, .md, .pdf, .docx, etc.

# Try exact phrase search
curl "http://localhost:8000/search?q=exact+phrase"
```

### File changes not triggering reindex
```bash
# Check file extension
ls -la ~/2ndBrain_RAG/yourfile.XXX

# Supported: txt, md, rtf, pdf, doc, docx, ppt, pptx, html, csv, tsv, json, py, ipynb

# Manual reindex
curl -X POST http://localhost:8000/ingest

# Check permissions
ls -la ~/2ndBrain_RAG/
# Should be readable by your user
```

### Out of memory
```bash
# Reduce chunk overlap (fewer docs in memory)
# Edit utils/loader.py:20
# Change chunk_overlap from 120 to 50

# Use smaller embedding model
# Edit rag_mcp_server.py:32
# Change to: all-MiniLM-L6-v2  (currently used, smallest)

# Use lighter Ollama model
export OLLAMA_MODEL=phi  # instead of llama3
```

### Database locked
```bash
# Clear ChromaDB cache
rm -rf ~/.chroma/

# Restart server
# Re-run ingest
curl -X POST http://localhost:8000/ingest
```

---

## Performance Tips

### Faster Search
- Reduce `k` parameter (fewer results to return)
- Use smaller chunk_overlap (fewer loaded chunks)
- Use lightweight embedding model

### Faster Indexing
- Use smaller Ollama model (mistral vs llama3)
- Reduce chunk_size (fewer embeddings needed)
- Exclude large binary files

### Faster Chat
- Use fast Ollama model (phi, mistral < llama3)
- Reduce `k` (less context to read)
- Reduce chunk_size (shorter prompts)

### Save Memory
- Disable file watcher (restart without watching)
- Use smaller embedding model
- Clear .chroma periodically

---

## File Locations

| Item | Location |
|------|----------|
| Documents | ~/2ndBrain_RAG/ |
| Vector DB | ~/2ndBrain_RAG/.chroma/ |
| Python venv | ~/2ndBrain_RAG/.venv/ |
| LaunchAgent (macOS) | ~/Library/LaunchAgents/com.2ndbrain.rag.plist |
| LaunchAgent logs (macOS) | /tmp/2ndBrain_RAG.log |

---

## Supported File Formats

| Category | Formats |
|----------|---------|
| Documents | .txt, .md, .rtf |
| Office | .pdf, .doc, .docx, .ppt, .pptx |
| Web | .html, .htm |
| Data | .csv, .tsv, .json |
| Code | .py, .ipynb |

---

## Ollama Models

```bash
# Quick models (fast, lower quality)
ollama pull phi              # ~3s per query
ollama pull mistral          # ~4s per query

# Balanced (recommended)
ollama pull neural-chat      # ~6s per query
ollama pull llama3-mini      # ~8s per query

# Quality models (slow, higher quality)
ollama pull llama3           # ~15s per query
ollama pull llama3-70b       # ~60s per query (needs 64GB RAM)

# Set default
export OLLAMA_MODEL=mistral

# Switch in API calls
curl -X POST http://localhost:8000/chat \
  -d '{"query": "test?", "model": "mistral"}'
```

---

## Integration with Claude Desktop

### Setup
```bash
# Edit ~/.mcp/config.json or ~/.mcp.json
{
  "servers": {
    "2ndbrain-rag": {
      "command": "python",
      "args": ["/Users/YOUR_USERNAME/2ndBrain_RAG/rag_mcp_server.py"]
    }
  }
}

# Restart Claude Desktop
# Now Claude can call: /search, /chat, /status, /ingest
```

### Example Prompt
```
Search my knowledge base for "machine learning"
and answer: What are the key concepts?
```

Claude will:
1. Call /search with your query
2. Call /chat with context
3. Return sourced answer

---

## Development

### Run Tests
```bash
# Install test deps
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test
pytest tests/test_loader.py -v

# With coverage
pytest --cov=utils
```

### Code Quality
```bash
# Format code
pip install black
black .

# Lint
pip install ruff
ruff check .

# Type check
pip install mypy
mypy rag_mcp_server.py
```

### Debug Mode
```python
# Add to rag_mcp_server.py:
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Then use in code:
logger.debug(f"Query: {q}")
logger.info(f"Found {n} results")
logger.error(f"Error: {e}")
```

---

## Key Files & Lines

| File | Lines | Purpose |
|------|-------|---------|
| rag_mcp_server.py | 1-86 | Main API server |
| rag_mcp_server.py | 35-42 | /status endpoint |
| rag_mcp_server.py | 44-50 | /ingest endpoint |
| rag_mcp_server.py | 52-62 | /search endpoint |
| rag_mcp_server.py | 64-80 | /chat endpoint |
| rag_mcp_server.py | 28-33 | Configuration |
| utils/loader.py | 6-10 | Supported formats |
| utils/loader.py | 20 | Chunking params |
| utils/embedder.py | 5-13 | Upsert logic |
| utils/llm.py | 4-5 | Ollama config |
| utils/watcher.py | 14-20 | Reindex trigger |

---

## One-Liners

```bash
# Rebuild index from scratch
curl -X POST "http://localhost:8000/ingest?full_rebuild=true"

# Search and show results
curl "http://localhost:8000/search?q=topic&k=3" | jq '.results[].content'

# Get all indexed documents
curl http://localhost:8000/status | jq '.documents_indexed'

# Kill server on port 8000
kill $(lsof -t -i :8000)

# Check ChromaDB size
du -sh ~/.chroma/

# Watch server logs
tail -f /tmp/2ndBrain_RAG.log

# List all supported file types
grep SUPPORTED_EXTS utils/loader.py

# Check Ollama status
curl http://localhost:11434/api/status

# See embedding model info
python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('all-MiniLM-L6-v2'); print(m.get_sentence_embedding_dimension())"
```

---

**Quick Reference Version**: 1.0
**Last Updated**: October 22, 2025
**For questions**: See CLAUDE_GUIDE.md or ARCHITECTURE.md
