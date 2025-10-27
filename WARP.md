# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**2ndBrain_RAG** is a local Retrieval-Augmented Generation (RAG) system with:
- FastAPI server for semantic search and AI-powered Q&A
- Persistent ChromaDB vector database
- Automatic file monitoring and reindexing
- Ollama LLM integration for chat
- MCP protocol support for Claude Desktop integration

## Common Commands

### Development

```bash
# Start development server (with auto-reload)
uvicorn rag_mcp_server:app --reload

# Start production server
uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_loader.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=utils --cov-report=html

# Run single test
pytest tests/test_api.py::test_status_endpoint -v
```

### Code Quality

```bash
# Check code style (linting)
ruff check .

# Format code
black .

# Type checking
mypy rag_mcp_server.py utils/

# Run all quality checks
ruff check . && black --check . && mypy rag_mcp_server.py utils/
```

### API Testing

```bash
# Check status
curl http://localhost:8000/status

# Trigger document indexing
curl -X POST http://localhost:8000/ingest

# Full rebuild (clear and reindex)
curl -X POST "http://localhost:8000/ingest?full_rebuild=true"

# Search documents
curl "http://localhost:8000/search?q=machine+learning&k=5"

# Chat with RAG
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "k": 5}'

# View API documentation (open in browser)
open http://localhost:8000/docs
```

### Ollama Management

```bash
# Start Ollama service
ollama serve

# Pull a model
ollama pull llama3

# List available models
ollama list

# Test Ollama is running
curl http://localhost:11434/api/status
```

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
export RAG_FOLDER=/path/to/documents
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3
export RAG_API_KEY=your-secret-key  # Optional
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_PER_MINUTE=60
```

## Architecture Overview

### System Components

```
FastAPI Application (rag_mcp_server.py)
    ├── API Endpoints: /status, /ingest, /search, /chat, /cache-stats
    ├── Authentication: Optional API key via RAG_API_KEY
    ├── Rate Limiting: Configurable per-minute limits
    └── Thread-safe ChromaDB access (RLock)

Document Pipeline (utils/)
    ├── loader.py: File scanning, parsing, chunking
    │   • RecursiveCharacterTextSplitter (800 char chunks, 120 overlap)
    │   • Supports: txt, md, pdf, doc, docx, ppt, csv, json, py, ipynb
    ├── embedder.py: Vector generation and storage
    │   • HuggingFace sentence-transformers (all-MiniLM-L6-v2)
    │   • ChromaDB upsert operations
    ├── llm.py: Ollama HTTP client
    │   • 300s timeout, configurable model
    ├── watcher.py: File system monitoring
    │   • Watchdog-based auto-reindexing
    ├── cache.py: Query result caching
    │   • In-memory with TTL (1 hour default)
    │   • MD5-based cache keys
    └── ratelimit.py: Request rate limiting
        • Token bucket algorithm
        • Per-client IP tracking
```

### Data Flow Patterns

**Indexing Flow:**
1. `load_documents()` scans RAG_FOLDER recursively
2. Files parsed via LangChain's UnstructuredFileLoader
3. Text chunked (800 chars with 120 overlap)
4. Chunks embedded via sentence-transformers
5. Vectors stored in ChromaDB with metadata (source, chunk_id)
6. Database persists to `.chroma/` directory

**Search Flow:**
1. Query vectorized using same embedding model
2. ChromaDB performs k-NN similarity search
3. Top-k results returned with content and metadata
4. Results cached for performance (1 hour TTL)

**Chat Flow:**
1. Search retrieves relevant document chunks (top-k)
2. Context formatted with citations: `[1] content\nSOURCE: file.pdf`
3. RAG prompt constructed: question + context
4. Ollama generates response via HTTP API
5. Response returned with citation list

### Thread Safety

- **Main Thread:** FastAPI/Uvicorn handles HTTP requests
- **Watcher Thread:** Daemon thread monitors file system changes
- **Shared Resource:** ChromaDB accessed through `db_lock` (RLock)
- **Cache:** Thread-safe with internal locking
- File changes trigger full reindexing (all documents reloaded)

### Configuration Points

| Setting | File | Line | Default | Notes |
|---------|------|------|---------|-------|
| Chunk size | utils/loader.py | 20 | 800 | Larger = more context, slower |
| Chunk overlap | utils/loader.py | 20 | 120 | Prevents boundary loss |
| Embedding model | rag_mcp_server.py | 73 | all-MiniLM-L6-v2 | 384-dim vectors |
| Search default k | rag_mcp_server.py | 132 | 5 | Top-k results |
| Cache TTL | utils/cache.py | 162 | 3600s | 1 hour |
| Rate limit | rag_mcp_server.py | 27 | 60/min | Per client IP |
| Ollama timeout | utils/llm.py | - | 300s | HTTP request timeout |

## Key Development Patterns

### Adding New Document Formats

1. Update `SUPPORTED_EXTS` in `utils/loader.py` (lines 6-10)
2. Ensure LangChain UnstructuredFileLoader supports it
3. Test with sample file via `/ingest`

### Modifying Search Behavior

- **Cache settings:** Edit `QueryCache()` initialization in `utils/cache.py`
- **Validation:** Adjust `MAX_QUERY_LENGTH`, `MAX_K_VALUE` in `rag_mcp_server.py` (lines 37-39)
- **Results:** Modify response formatting in `/search` endpoint (lines 149-156)

### Customizing Chat Prompts

- **System prompt:** Edit default in `/chat` endpoint (line 201)
- **RAG template:** Modify prompt formatting (lines 202-211)
- **Citation style:** Adjust context_parts formatting (lines 192-196)

### Error Handling Strategy

- **Loader:** Per-file try/catch; skip failures, continue processing
- **API:** FastAPI raises HTTPException with appropriate status codes
- **Ollama:** Returns error message if service unavailable
- **Watcher:** Catches exceptions, logs, continues monitoring

### Testing Approach

- Unit tests in `tests/` for each utility module
- FastAPI TestClient for API endpoint testing
- Use `tmp_path` fixture for file system tests
- Mock external services (Ollama) in tests

## Important Notes

- **Ollama Required:** Must be running with model pulled (`ollama pull llama3`)
- **Database Persistence:** ChromaDB state stored in `.chroma/` directory
- **File Watcher:** Reindexes ALL documents on any file change (not incremental)
- **API Key:** Optional; if `RAG_API_KEY` set, all endpoints require `X-Api-Key` header
- **Rate Limiting:** Enabled by default (60 req/min); disable with `RATE_LIMIT_ENABLED=false`
- **Cache Invalidation:** Automatic on ingest; manual via reindexing
- **Supported Extensions:** `.txt .md .rtf .pdf .doc .docx .ppt .pptx .html .htm .csv .tsv .json .py .ipynb`

## Troubleshooting

**"Ollama error" in responses:**
```bash
# Verify Ollama is running
ps aux | grep ollama
ollama serve  # If not running

# Check model is available
ollama list
ollama pull llama3  # If missing
```

**No search results after adding files:**
```bash
# Manually trigger reindexing
curl -X POST http://localhost:8000/ingest

# Check indexed count
curl http://localhost:8000/status
```

**Port already in use:**
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn rag_mcp_server:app --port 8001
```

**Database locked errors:**
```bash
# Clear ChromaDB and rebuild
rm -rf .chroma/
curl -X POST http://localhost:8000/ingest
```

## Performance Optimization

- **Reduce chunk overlap** for less memory usage (50 instead of 120)
- **Increase cache size** in `utils/cache.py` for high-traffic scenarios
- **Use lighter Ollama models** (phi, mistral) for faster responses
- **Adjust k parameter** to fetch fewer results per query
- **Monitor cache hit rate** via `/cache-stats` endpoint

## Integration with Claude Desktop

Edit `~/.mcp/config.json`:
```json
{
  "servers": {
    "2ndbrain-rag": {
      "command": "python",
      "args": ["/Users/YOUR_USERNAME/2ndBrain_RAG/rag_mcp_server.py"]
    }
  }
}
```

## Documentation References

- **ARCHITECTURE.md**: Deep technical design details
- **DEVELOPMENT.md**: Contributing guidelines and development workflow
- **QUICK_REF.md**: Fast command lookup
- **CLAUDE_GUIDE.md**: AI assistant integration context
- API Docs: `http://localhost:8000/docs` (when server running)
