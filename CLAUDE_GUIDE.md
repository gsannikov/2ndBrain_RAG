# Claude Integration Guide - 2ndBrain_RAG

## Overview for Claude AI

You are assisting with **2ndBrain_RAG**, a local Retrieval-Augmented Generation (RAG) system built with Python and FastAPI. This document provides you with essential context to make informed decisions and contributions.

---

## What This Project Does

**2ndBrain_RAG** allows users to:
1. **Index Local Documents** - Convert personal files into a searchable vector database
2. **Semantic Search** - Find relevant content using AI-powered similarity matching
3. **Ask Questions** - Get AI-generated answers grounded in their documents with citations
4. **Auto-Sync** - Automatically reindex when files change on disk
5. **Integrate with Claude** - Expose RAG capabilities via MCP protocol to Claude Desktop

**Use Case**: Users can maintain a "second brain" of personal knowledge (PDFs, notes, research) that Claude can query intelligently.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client (Claude Desktop / HTTP)                         │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   FastAPI App (Port 8000)   │
        │  rag_mcp_server.py          │
        └──────────┬────────┬─────────┘
                   │        │
         ┌─────────▼─┐    ┌─▼─────────────────────┐
         │ ChromaDB  │    │ Ollama LLM Integration│
         │ Vector DB │    │ (localhost:11434)     │
         └───────────┘    └───────────────────────┘

    ┌─────────────────────────────────┐
    │  File System Watcher            │
    │  (utils/watcher.py)             │
    │  ▶ Detects file changes         │
    │  ▶ Triggers reindexing          │
    └─────────────────────────────────┘

    ┌──────────────────────────────────┐
    │  Document Pipeline               │
    │  utils/loader.py                 │
    │  ▶ Load & Parse Files            │
    │  ▶ Chunk Text                    │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │  Embedding Pipeline              │
    │  utils/embedder.py               │
    │  ▶ Convert chunks → vectors      │
    │  ▶ Store in ChromaDB             │
    └──────────────────────────────────┘
```

---

## Key Technologies & Why

| Tech | Purpose | Alternative | Notes |
|------|---------|-------------|-------|
| **FastAPI** | REST API framework | Flask, Django | Modern, async-ready, auto-docs |
| **ChromaDB** | Vector database | Pinecone, Weaviate | Local, no API key needed, persistent |
| **LangChain** | Document/LLM tools | LlamaIndex, RAG frameworks | Mature, extensive format support |
| **Ollama** | Local LLM | vLLM, LM Studio | Easy setup, no GPU required |
| **sentence-transformers** | Embeddings | OpenAI, Cohere | FOSS, deterministic, fast |
| **Watchdog** | File monitoring | os.walk polling | Event-driven, efficient |

---

## Request/Response Flows

### Flow 1: Indexing Documents
```
1. PUT /ingest?full_rebuild=true
2. loader.py: scan RAG_FOLDER recursively
3. loader.py: parse each file (PDF, txt, md, etc.)
4. loader.py: chunk with 800 char chunks, 120 char overlap
5. embedder.py: generate embeddings via sentence-transformers
6. embedder.py: store in ChromaDB with metadata (source, chunk_id)
7. Return: { status: ok, indexed_chunks: N }
```

### Flow 2: Search Documents
```
1. GET /search?q="machine learning"&k=5
2. Vectorize query using same embedding model
3. ChromaDB: find top-5 most similar chunks
4. Return: matching documents with content, source, chunk_id
```

### Flow 3: RAG Chat
```
1. POST /chat { query: "...", k: 5, system: "...", model: "..." }
2. Execute search (Flow 2) to get context documents
3. Format context into RAG prompt with citations
4. Call Ollama API with prompt + system message
5. Stream/return LLM response with source citations
```

### Flow 4: File Monitoring (Background)
```
1. watcher.py: observes RAG_FOLDER for changes
2. On any file event: create/modify/delete
3. Reload ALL documents from RAG_FOLDER
4. Reindex into ChromaDB (incremental via upsert)
5. Log: "🔄 Change detected: ..."
```

---

## Code Organization by Concern

### Entry Point & API Routes
**File**: `rag_mcp_server.py`
- Initializes FastAPI app
- Configures ChromaDB + embeddings
- Defines 4 HTTP endpoints
- Spawns file watcher thread
- Environment-based configuration

### Document Processing Pipeline
**Files**: `utils/loader.py`, `utils/embedder.py`
- `loader.py`:
  - Recursively finds supported files
  - Parses via LangChain UnstructuredFileLoader
  - Chunks text (800 chars, 120 overlap)
  - Attaches metadata
- `embedder.py`:
  - Upserts chunks into ChromaDB
  - Resets/clears index
  - Manages persistence

### LLM Integration
**File**: `utils/llm.py`
- HTTP client to Ollama API
- Configurable model + host
- Error handling for unavailable Ollama
- 300-second timeout

### Real-Time Sync
**File**: `utils/watcher.py`
- File system event handler (watchdog)
- Triggers full reindexing on changes
- Runs as daemon thread
- Prints status messages

---

## Configuration & Customization

### Environment Variables
```bash
# Document folder
RAG_FOLDER=/path/to/docs

# Ollama configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Code-Level Tweaks

**Text Chunking** (utils/loader.py:20)
- Increase chunk_size for longer context windows
- Increase chunk_overlap to reduce info gaps
- Current: 800/120 is balanced for Q&A

**Embedding Model** (rag_mcp_server.py:32)
- Current: `all-MiniLM-L6-v2` (lightweight, fast)
- Alternative: `all-mpnet-base-v2` (better quality, 3x slower)

**Search Behavior** (rag_mcp_server.py:53-62)
- `k` parameter controls top-k results
- Adjust in API calls or set default

**Chat Prompt** (rag_mcp_server.py:68-77)
- System message: "You are a helpful assistant..."
- Context formatting: "[n] content\nSOURCE: ..."
- Citation style: "[1], [2]"

---

## Common Tasks for Claude

### Task 1: Add Support for New Document Format
**Location**: `utils/loader.py:6-10` (SUPPORTED_EXTS)
**Steps**:
1. Add extension to SUPPORTED_EXTS set
2. Verify LangChain UnstructuredFileLoader handles it
3. Test with sample file

### Task 2: Modify RAG Chat Prompt
**Location**: `rag_mcp_server.py:68-77`
**Steps**:
1. Edit the prompt template string
2. Adjust context formatting
3. Update citation style if needed

### Task 3: Change Embedding Model
**Location**: `rag_mcp_server.py:32`
**Steps**:
1. Replace model_name parameter
2. Restart server (old embeddings incompatible)
3. Re-run `/ingest?full_rebuild=true`

### Task 4: Optimize Performance
**Options**:
- Reduce `chunk_overlap` (faster indexing)
- Use smaller embedding model
- Use smaller Ollama model (e.g., mistral)
- Limit search results (`k` parameter)

### Task 5: Add Authentication
**Location**: Wrap FastAPI endpoints
**Steps**:
1. Add dependency for API key check
2. Validate in each route
3. Return 401 if unauthorized

---

## Dependencies & Versions

```
fastapi            # REST framework
uvicorn            # ASGI server
langchain          # Document/LLM tools
chromadb           # Vector DB
sentence-transformers  # Embeddings
unstructured       # Document parsing
pdfminer.six       # PDF extraction (via unstructured)
watchdog           # File monitoring
requests           # HTTP client
```

All are pip-installable, no compiled dependencies required (except on Mac with Apple Silicon - may need specific builds for some packages).

---

## Error Modes & Resilience

| Error | Likely Cause | Recovery |
|-------|-------------|----------|
| "Ollama error" response | Ollama not running | Start Ollama: `ollama serve` |
| Port 8000 in use | Another service using it | Use `--port` flag or kill process |
| ChromaDB locked | Concurrent access | Restart server, check file locks |
| "Skipping file" warnings | Parsing failure | Check file format, check console for errors |
| Slow search | Large document set | Reduce k, optimize chunk_size |
| File watcher not triggering | Permission issue | Check folder permissions, restart watcher |

---

## Testing Strategies

### Manual API Testing
```bash
# Check health
curl http://localhost:8000/status

# Test indexing
curl -X POST http://localhost:8000/ingest

# Test search
curl "http://localhost:8000/search?q=test&k=3"

# Test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test?", "k": 5}'
```

### File Watcher Testing
```bash
# Add file to RAG_FOLDER
echo "test content" > ~/2ndBrain_RAG/test.txt

# Monitor logs (watch for 🔄 and ✅ messages)
# Server should automatically reindex
```

### Load Testing
```bash
# Use tools like Apache Bench
ab -n 100 -c 10 http://localhost:8000/status

# Or for POST
ab -n 50 -p request.json -T application/json http://localhost:8000/chat
```

---

## Known Limitations & Future Improvements

### Current Limitations
- ❌ No authentication/authorization
- ❌ No query result caching
- ❌ No batch API for multiple queries
- ❌ Reindexing blocks on large document sets
- ❌ Single embedding model (no multi-modal)
- ❌ No streaming responses

### Potential Improvements
- ✅ Add API key authentication
- ✅ Implement Redis caching for searches
- ✅ Add async reindexing
- ✅ Support for image/table extraction
- ✅ Multiple embedding models
- ✅ Streaming chat responses
- ✅ WebSocket support for real-time updates
- ✅ Admin dashboard for index management

---

## Integration with Claude Desktop

### How It Works
1. Configure `.mcp.json` with path to server
2. Claude Desktop starts server as subprocess
3. Claude calls server endpoints via HTTP
4. Results returned to Claude for processing

### Example Claude Prompt
```
"Search my knowledge base for information about
[TOPIC] and summarize the key points with sources."
```

Claude will:
1. Call GET /search?q=[TOPIC]
2. Call POST /chat with context
3. Return sourced answer to user

---

## File Reference Map

```
2ndBrain_RAG/
├── rag_mcp_server.py          → Entry point, API routes, initialization
├── utils/
│   ├── loader.py              → Document loading, parsing, chunking
│   ├── embedder.py            → ChromaDB operations, persistence
│   ├── llm.py                 → Ollama API integration
│   └── watcher.py             → File system monitoring
├── scripts/
│   └── install.sh             → Setup automation, LaunchAgent config
├── requirements.txt           → Python dependencies
├── README.md                  → User quickstart
├── CLAUDE_GUIDE.md            → This file
└── .chroma/                   → ChromaDB data (generated)
```

---

## Performance Characteristics

| Operation | Typical Duration | Factors |
|-----------|------------------|---------|
| Index 100 docs (1MB total) | 5-10s | CPU speed, file format diversity |
| Search query | 100-200ms | k value, database size |
| Chat response | 3-30s | Ollama model size, prompt length |
| File watch detection | <1s | OS file system |
| Reindex on file change | 5-10s | Total document size |

---

## Security Considerations

⚠️ **Current Security Posture**: Development/internal use only

### Security Gaps
- No authentication on API
- No input validation/sanitization
- Local file system read without restrictions
- Ollama API called without verification

### Recommendations for Production
1. Add API key authentication
2. Validate input query length
3. Restrict document folder access
4. Run behind reverse proxy (nginx)
5. Use HTTPS/TLS
6. Rate limiting
7. Query result sanitization

---

## For Claude: Decision Points

When asked to modify this project, consider:

1. **Impact on Performance**: Will change affect indexing speed or search latency?
2. **Backward Compatibility**: Can existing document databases still be used?
3. **Dependency Risk**: Does change require new external dependencies?
4. **Security**: Does change introduce new vulnerabilities?
5. **MCP Compatibility**: Will change break Claude Desktop integration?

---

**Last Updated**: October 22, 2025
**Claude Context Version**: 1.0
