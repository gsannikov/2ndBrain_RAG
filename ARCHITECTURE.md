# Architecture & Design Documentation

## High-Level System Design

### System Boundaries
```
┌──────────────────────────────────────────────────────────────┐
│                      2ndBrain_RAG System                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              API Layer (FastAPI)                       │  │
│  │  /status  /ingest  /search  /chat                      │  │
│  └─────┬──────────────────────────────────┬───────────────┘  │
│        │                                  │                  │
│  ┌─────▼──────────────────┐    ┌──────────▼──────────────┐   │
│  │  Document Processing   │    │  Vector Storage Layer   │   │
│  │  • Load Files          │    │  • ChromaDB Vector DB   │   │
│  │  • Parse Content       │    │  • Persistence Manager  │   │
│  │  • Chunk Text          │    │  • Similarity Search    │   │
│  └────────────────────────┘    └─────────────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         Integration Layer                              │  │
│  │  • Embedding Generation (sentence-transformers)        │  │
│  │  • LLM Integration (Ollama)                            │  │
│  │  • File System Monitoring (Watchdog)                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘

External Dependencies:
  • Ollama Service (localhost:11434)
  • File System (~/2ndBrain_RAG folder)
  • HuggingFace Model Hub (for embeddings download)
```

---

## Component Architecture

### 1. FastAPI Application Layer (rag_mcp_server.py)

**Responsibilities**:
- HTTP request/response handling
- MCP protocol adaptation
- Configuration resolution
- Component initialization
- Route orchestration

**Initialization Flow**:
```python
1. Parse command-line arguments (--path)
2. Resolve RAG_PATH from args or env vars
3. Create .chroma directory
4. Initialize HuggingFace embeddings (lazy load from HF hub)
5. Initialize ChromaDB with persistent directory
6. Start file watcher thread (daemon)
7. Start Uvicorn server (port 8000)
```

**Route Architecture**:
```
GET /status
  └─→ Query ChromaDB collection count
      └─→ Return { rag_path, db_path, documents_indexed }

POST /ingest
  ├─→ Check full_rebuild flag
  ├─→ [If true] Reset ChromaDB index
  ├─→ Load all documents via loader.py
  ├─→ Upsert into ChromaDB via embedder.py
  └─→ Return { status, indexed_chunks, source_path }

GET /search
  ├─→ Receive query string (q, k parameters)
  ├─→ Vectorize query using embedding model
  ├─→ ChromaDB similarity_search(query_vector, k)
  ├─→ Format results with metadata
  └─→ Return { query, k, results: [...] }

POST /chat
  ├─→ Receive ChatRequest { query, k, system?, model? }
  ├─→ Execute search (GET /search logic)
  ├─→ Format context string with citations [1], [2], ...
  ├─→ Build RAG prompt with context + question
  ├─→ Call ollama_chat() with Ollama
  ├─→ Parse response
  └─→ Return { answer, citations: [{index, source}] }
```

---

### 2. Document Processing Pipeline

#### Loader (utils/loader.py)

**Data Flow**:
```
RAG_FOLDER (recursive scan)
    ↓
File listing with extension filter
    ↓
UnstructuredFileLoader (per file)
    ↓
LangChain Document objects { content, metadata }
    ↓
RecursiveCharacterTextSplitter
    ├─ chunk_size: 800 chars
    ├─ chunk_overlap: 120 chars
    └─ Maintains semantic boundaries
    ↓
Chunk List with metadata { source, chunk_id }
    ↓
[Return to embedder]
```

**Supported File Types**:
```
Documents:  .txt, .md, .rtf, .pdf, .doc, .docx
Slides:     .ppt, .pptx
Web:        .html, .htm
Data:       .csv, .tsv, .json
Code:       .py, .ipynb
```

**Error Handling Strategy**:
- Per-file try/catch (one bad file doesn't break ingest)
- Print warnings but continue
- Skip silently on parse failure
- Log to stdout/stderr

**Text Splitting Logic**:
```
Why RecursiveCharacterTextSplitter?
- Respects semantic boundaries (paragraphs → sentences → words)
- Overlap prevents context loss at boundaries
- 800 chars ≈ 150 tokens (good for LLM context)
- 120 char overlap ≈ handles mid-sentence splits

Chunking Example:
"The cat sat. The dog ran."  (33 chars)
├─ Chunk 0 [0:800]: "The cat sat. The dog ran."
└─ No split needed (< 800 chars)

"Lorem ipsum... [long text 2000 chars] ...dolor sit"
├─ Chunk 0 [0:800]: "Lorem ipsum... [800 chars]"
├─ Chunk 1 [680:1480]: "[overlapped 120] ... [800 chars]"
├─ Chunk 2 [1360:2160]: "[overlapped 120] ... [800 chars]"
└─ Chunk 3 [2040:end]: "[overlapped 120] ... [remaining]"
```

#### Embedder (utils/embedder.py)

**Vector Database Architecture**:
```
LangChain Documents
    ↓
upsert_documents(db, docs)
    ├─ Extract texts: [doc.page_content, ...]
    ├─ Extract metadatas: [doc.metadata, ...]
    ├─ Generate IDs: [chunk_id from metadata]
    ├─ Call db.add_texts(texts, metadatas, ids)
    │  └─ Sentence-transformers encodes texts → vectors
    │  └─ ChromaDB stores: id → { vector, text, metadata }
    ├─ db.persist() writes to disk (.chroma/)
    └─ Return count of added documents

reset_index(db)
    ├─ db._collection.delete(where={})
    │  └─ Empties all vectors
    ├─ db.persist()
    └─ Clean slate for re-indexing
```

**Metadata Storage**:
```json
{
  "source": "/Users/you/2ndBrain_RAG/notes.md",
  "chunk_id": "/Users/you/2ndBrain_RAG/notes.md::chunk_5"
}
```

---

### 3. Embedding & Vector Search

**Embedding Model Chain**:
```
Input Text (e.g., "machine learning")
    ↓
sentence-transformers/all-MiniLM-L6-v2
    ├─ Model Architecture: MiniLM (6-layer transformer)
    ├─ Output Dimension: 384 dimensions
    ├─ Speed: ~1000 sentences/second (CPU)
    ├─ Quality: Tuned for semantic similarity
    └─ Size: ~90MB
    ↓
384-dimensional vector
    ↓
ChromaDB Storage
```

**Similarity Search Process**:
```
Query: "What is RAG?"
    ↓
Embedding (same model)
    → [0.12, -0.45, 0.89, ...] (384-dim vector)
    ↓
ChromaDB L2/cosine distance metric
    ├─ Compute distance to all stored vectors
    └─ k-NN search (default k=5)
    ↓
Top-5 closest vectors
    ↓
Retrieve text + metadata
    ↓
Return to client
```

**Why This Model**:
- Lightweight: Runs on CPU
- Fast: Real-time search
- Quality: Sufficient for semantic search
- Free: Open source, no API key
- Deterministic: Same embedding for same text

---

### 4. LLM Integration (utils/llm.py)

**Ollama Integration Pattern**:
```
RAG Prompt + Context
    ↓
ollama_chat(prompt, system, model)
    ├─ POST http://localhost:11434/api/generate
    ├─ Payload:
    │  {
    │    "model": "llama3",
    │    "prompt": "...",
    │    "system": "You are helpful...",
    │    "stream": false
    │  }
    ├─ 300-second timeout
    └─ Error handling: return error message
    ↓
Ollama Process (runs locally)
    ├─ Token generation
    ├─ Temperature/top-p defaults
    └─ Streaming or batch response
    ↓
JSON Response { "response": "...", ... }
    ↓
Extract response.response field
    ↓
Return to chat endpoint
```

**Why External Ollama Process**:
- Decoupling: RAG server independent of LLM
- Flexibility: Swap models without restarting RAG
- Performance: Ollama optimized for local inference
- Simplicity: HTTP client vs embedding model library

**Configuration Options**:
```bash
# Environment variables (optional)
OLLAMA_HOST=http://localhost:11434  # Default
OLLAMA_MODEL=llama3                 # Default

# Request-time overrides
POST /chat {
  query: "...",
  model: "mistral",              # Override default
  system: "Custom system prompt"  # Override default
}
```

---

### 5. File System Monitoring (utils/watcher.py)

**Event Handling Architecture**:
```
watchdog.Observer
    ├─ Monitors: RAG_FOLDER (recursive)
    ├─ Triggers on: create, modify, delete, move
    └─ Calls: RAGHandler.on_any_event()

RAGHandler.on_any_event(event)
    ├─ Filter: skip if is_directory
    ├─ Log: "🔄 Change detected: {path}"
    ├─ Load: all documents from RAG_FOLDER
    ├─ Upsert: into ChromaDB (incremental)
    ├─ Log: "✅ Re-indexed N chunks"
    └─ Continue monitoring
```

**Background Thread Model**:
```
Main Thread (FastAPI/Uvicorn)
    ├─ Accepts HTTP requests
    └─ Runs normally

Watcher Thread (Daemon)
    ├─ Sleeps 1 second between checks
    ├─ On event: reload all docs
    ├─ On event: upsert to ChromaDB
    └─ Exception handling: catch KeyboardInterrupt
```

**Reindexing Behavior**:
```
File Change Event
    ↓
Reload ALL documents (not just changed file)
    ├─ Reason: Ensures consistency
    ├─ Trade-off: May be slow for large sets
    └─ Future: Track only changed files
    ↓
Upsert into ChromaDB
    ├─ NEW chunks: added
    ├─ MODIFIED chunks: updated (by chunk_id)
    ├─ DELETED chunks: overwritten (soft delete)
    └─ ChromaDB persists changes
```

---

## Data Structures

### Document Flow

```
LangChain Document
{
  page_content: "Lorem ipsum dolor sit amet...",
  metadata: {
    source: "/path/to/file.pdf",
    [other parse metadata from UnstructuredFileLoader]
  }
}
    ↓ (after chunking)
{
  page_content: "Lorem ipsum dolor sit amet...",  # 800-char chunk
  metadata: {
    source: "/path/to/file.pdf",
    chunk_id: "/path/to/file.pdf::chunk_0"
  }
}
    ↓ (stored in ChromaDB)
{
  id: "/path/to/file.pdf::chunk_0",
  embedding: [0.12, -0.45, ...],  # 384-dim vector
  document: "Lorem ipsum dolor sit amet...",
  metadata: {
    source: "/path/to/file.pdf",
    chunk_id: "/path/to/file.pdf::chunk_0"
  }
}
```

### API Request/Response

```
POST /chat Request
{
  "query": "What is machine learning?",
  "k": 5,                          # top-5 results
  "system": "Be concise",          # optional
  "model": "mistral"               # optional
}

POST /chat Response
{
  "answer": "Machine learning is [1]...",
  "citations": [
    {
      "index": 1,
      "source": "/Users/you/docs/ml_101.pdf"
    },
    {
      "index": 2,
      "source": "/Users/you/docs/notes.md"
    }
  ]
}
```

---

## Concurrency & Threading Model

### Single-Threaded FastAPI
```
Uvicorn (ASGI)
    ├─ Accepts HTTP requests
    ├─ Routes to FastAPI handlers
    ├─ Each request: sync function (blocks until done)
    └─ Queues concurrent requests

RAGHandler (Watchdog)
    ├─ Runs in separate daemon thread
    ├─ Independent from HTTP handling
    ├─ Reindexing doesn't block API
    └─ Concurrent access to ChromaDB
```

### Shared Resource: ChromaDB
```
Problem: Multiple threads accessing db
    ├─ HTTP requests: read-heavy (search, chat)
    ├─ File watcher: write-heavy (reindex)
    └─ Potential race conditions

Solution: ChromaDB Thread-Safety
    ├─ ChromaDB handles locking internally
    ├─ Upsert is atomic
    ├─ persist() flushes to disk safely
    └─ No explicit locking needed in our code
```

**Known Limitation**: Reindexing on file change reloads ALL documents. For large sets, this blocks until complete.

---

## Storage Architecture

### Directory Structure
```
~/2ndBrain_RAG/
├── .chroma/                    # Vector database
│   ├── data/
│   │   └── [hash].db           # SQLite collection data
│   ├── embeddings/
│   │   └── [vectors.bin]       # Vector embeddings
│   └── configs/
│       └── [metadata.json]     # Schema info
│
├── .venv/                      # Python virtual environment
│
├── [user documents]
│   ├── notes.md
│   ├── research.pdf
│   ├── data.csv
│   └── ...
```

### ChromaDB Persistence
```
ChromaDB Storage Format:
    ├─ SQLite database for collection metadata
    ├─ Binary vector storage (numpy arrays)
    ├─ Metadata as JSON
    └─ Fully persistent across restarts

Persistence Flow:
    1. Add documents to ChromaDB
    2. Call db.persist() → flush to disk
    3. Restart server
    4. ChromaDB loads from disk automatically
    5. No reindexing needed
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Index N docs | O(N × M) | N = docs, M = avg chunks per doc |
| Search query | O(log k) | k-NN search via indexing |
| Chat response | O(1) | Fixed LLM call (dominated by Ollama) |
| File watch | O(N) | Reindexes all N documents |

### Space Complexity

| Component | Space | Calculation |
|-----------|-------|-------------|
| 1 embedding | ~1.5 KB | 384 floats × 4 bytes |
| 1 document (1000 docs) | ~1.5 MB | 1000 embeddings × 1.5KB |
| Document index | ~100 MB | 100,000 chunks × 1KB metadata |
| Embedding model (disk) | ~90 MB | sentence-transformers weights |

---

## Security Architecture

### Current Model (Development)
```
Client (trusted)
    ↓ HTTP (unencrypted)
FastAPI Server (no auth)
    ├─ No validation on file paths
    ├─ Full access to RAG_FOLDER
    ├─ Indirect Ollama access
    └─ Readable response data
```

### Production Recommendations
```
Client (untrusted)
    ↓ HTTPS (TLS encryption)
Reverse Proxy (nginx)
    ├─ Rate limiting
    ├─ Input validation
    └─ DDoS protection
    ↓
FastAPI Server (with auth)
    ├─ API key validation
    ├─ Request body size limits
    ├─ Query sanitization
    └─ Rate limiting per key
    ↓
Sandboxed ChromaDB access
    └─ Read-only for most users
```

---

## Error Handling Strategy

### By Component

| Component | Error Type | Handling |
|-----------|-----------|----------|
| Loader | Parse failure | Log warning, skip file, continue |
| Embedder | Out of memory | Would crash (no mitigation) |
| ChromaDB | DB corruption | Clear and rebuild |
| Ollama | Not running | Return error message |
| Watcher | File permission | Log error, continue watching |
| API | Bad request | FastAPI returns 422 |

### Error Response Examples

```bash
# Ollama not running
POST /chat
{
  "answer": "[Ollama error: Connection refused.
             Is Ollama running and is the model pulled?]",
  "citations": []
}

# Invalid request
POST /chat with missing "query" field
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Deployment Architecture

### Single Machine (Current)
```
MacBook / Linux Server
    ├─ Python 3.8+
    ├─ Ollama service (running)
    ├─ 2ndBrain_RAG app (port 8000)
    ├─ ChromaDB local storage
    └─ File system monitoring
```

### Multi-Machine (Future)
```
Client Machine (Claude Desktop)
    ↓ HTTPS
Reverse Proxy (nginx on server)
    ↓
Application Server (FastAPI)
    ├─ Stateless (no local state)
    └─ Multiple instances possible
    ↓
Shared Storage (NFS/S3)
    ├─ Document files
    └─ Vector database
    ↓
Ollama Server (separate GPU machine)
    └─ Shared LLM resource
```

---

## Scaling Considerations

### Horizontal Scaling Blockers
- File watcher tied to single machine
- ChromaDB persistence on local disk
- No session management
- No distributed indexing

### Vertical Scaling Limits
- Embedding model: ~90MB RAM
- Full document scan: O(N) every file change
- Large k searches: slower
- Ollama: limited by available GPU/CPU

### Optimization Opportunities
- Cache popular queries
- Batch indexing (async, scheduled)
- Incremental watcher (track only changed files)
- Distributed ChromaDB (distributed deployment)
- Query result pagination

---

**Architecture Version**: 1.0
**Last Updated**: October 22, 2025
