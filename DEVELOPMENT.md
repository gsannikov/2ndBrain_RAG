# Development & Contributing Guide

**For developers wanting to contribute, extend, or work on 2ndBrain_RAG**

---

## Development Setup

### Prerequisites
- Python 3.8+
- Git
- Ollama (https://ollama.com)
- Virtual environment (recommended)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/gsannikov/2ndBrain_RAG.git
cd 2ndBrain_RAG

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -r requirements.txt
pip install -r requirements-dev.txt  # (create this with: pytest, ruff, black, mypy)

# Ensure Ollama is running
ollama serve  # In a separate terminal
```

### Verify Setup

```bash
# Start the server
uvicorn rag_mcp_server:app --reload

# In another terminal, test
curl http://localhost:8000/status

# Should return: {"rag_path": "...", "db_path": "...", "documents_indexed": 0}
```

---

## Project Structure

```
2ndBrain_RAG/
├── rag_mcp_server.py          # Main app entry point
├── utils/
│   ├── __init__.py
│   ├── loader.py              # Document loading
│   ├── embedder.py            # Vector DB operations
│   ├── llm.py                 # Ollama integration
│   └── watcher.py             # File monitoring
├── scripts/
│   └── install.sh             # macOS setup
├── tests/                     # Unit tests (TODO)
│   ├── test_loader.py
│   ├── test_embedder.py
│   ├── test_api.py
│   └── test_watcher.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies (TODO)
├── README.md                  # User guide
├── CLAUDE_GUIDE.md           # Claude AI guide
├── ARCHITECTURE.md           # Technical architecture
├── CODE_AUDIT.md            # Security & quality audit
├── PROJECT_DISCOVERY.md     # Project intent
├── DEVELOPMENT.md           # This file
├── QUICK_REF.md            # Quick reference
└── .claude/
    ├── context.md            # Context priming
    └── metadata.json         # Semantic index
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b bugfix/issue-number
```

### 2. Make Changes

**Code Style**:
- Follow PEP 8
- Use type hints
- Add docstrings for public functions
- Keep functions focused and small

**Example Function**:
```python
def process_documents(folder_path: str, max_size: int = 100) -> int:
    """
    Process all documents in a folder.

    Args:
        folder_path: Path to documents
        max_size: Maximum file size in MB

    Returns:
        Number of documents processed

    Raises:
        ValueError: If folder doesn't exist
    """
    if not os.path.exists(folder_path):
        raise ValueError(f"Path not found: {folder_path}")
    # Implementation...
    return count
```

### 3. Test Your Changes

```bash
# Run tests
pytest tests/ -v

# Check code style
ruff check .
black --check .

# Type checking
mypy rag_mcp_server.py utils/

# Manual testing
curl http://localhost:8000/status
curl "http://localhost:8000/search?q=test"
```

### 4. Commit Your Changes

```bash
# Stage files
git add .

# Write descriptive commit message
git commit -m "Add feature: incremental indexing

- Track changed files instead of reindexing all
- Reduces CPU usage by 80%
- Maintains backward compatibility

Fixes #123"
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name

# Then create PR on GitHub with description of changes
```

---

## Common Development Tasks

### Task 1: Add Support for New File Format

**Files to modify**: `utils/loader.py`

```python
# Step 1: Add extension to SUPPORTED_EXTS (line 6-10)
SUPPORTED_EXTS = {
    ".txt", ".md", ".rtf", ".pdf", ".doc", ".docx",
    ".ppt", ".pptx", ".html", ".htm", ".csv", ".tsv", ".json",
    ".py", ".ipynb",
    ".new_format"  # ← Add here
}

# Step 2: Test with sample file
echo "test content" > ~/2ndBrain_RAG/test.new_format

# Step 3: Run ingest
curl -X POST http://localhost:8000/ingest

# Step 4: Verify in /status
curl http://localhost:8000/status
```

### Task 2: Modify Chat Prompt Template

**Files to modify**: `rag_mcp_server.py`

```python
# Find the chat prompt (around line 68)
# Change the system message or response formatting

# Example: Make it more technical
prompt = f"""You are a technical expert. Answer the user's question
using ONLY the provided CONTEXT. If information is not available,
clearly state this and suggest where to look.

QUESTION: {req.query}
CONTEXT:
{context}

Provide a detailed technical answer with [citations]."""
```

### Task 3: Optimize Chunking

**Files to modify**: `utils/loader.py`

```python
# Experiment with different chunk sizes
# Line 20: adjust chunk_size and chunk_overlap

# For long documents with deep context:
chunk_size = 1200      # Larger chunks
chunk_overlap = 200    # More overlap

# For precise Q&A:
chunk_size = 500       # Smaller chunks
chunk_overlap = 50     # Less overlap

# Test and benchmark
```

### Task 4: Add Authentication

**Files to modify**: `rag_mcp_server.py`

```python
from fastapi import Depends, HTTPException, Header

API_KEY = os.getenv("RAG_API_KEY", "default-key")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

# Add dependency to routes
@app.get("/search")
def search(q: str, k: int = 5, api_key: str = Depends(verify_api_key)):
    # ... existing code
```

### Task 5: Add Query Caching

**Files to modify**: Create `utils/cache.py`

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query: str, k: int):
    """Cache search results for 1 hour"""
    # Wrapper around db.similarity_search
    pass

# Use in rag_mcp_server.py
results = cached_search(req.query, req.k)
```

---

## Testing

### Setting Up Tests

**Create `requirements-dev.txt`**:
```
pytest>=7.0
pytest-asyncio>=0.21.0
ruff>=0.1.0
black>=23.0
mypy>=1.0
```

**Install dev dependencies**:
```bash
pip install -r requirements-dev.txt
```

### Writing Tests

**Example: `tests/test_loader.py`**
```python
import pytest
from utils.loader import load_documents

def test_load_txt_file(tmp_path):
    # Create temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello world")

    # Load and verify
    docs = load_documents(str(tmp_path))
    assert len(docs) > 0
    assert "Hello world" in docs[0].page_content

def test_unsupported_format_skipped(tmp_path):
    # Create unsupported file
    test_file = tmp_path / "test.exe"
    test_file.write_bytes(b"binary")

    # Load should skip it
    docs = load_documents(str(tmp_path))
    assert len(docs) == 0
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_loader.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=utils --cov-report=html
```

---

## Code Review Checklist

Before submitting a PR, ensure:

### Functionality
- ✅ Feature works as intended
- ✅ Edge cases handled
- ✅ Backward compatible (unless breaking change intentional)

### Code Quality
- ✅ PEP 8 compliant
- ✅ Type hints on all functions
- ✅ Docstrings for public functions
- ✅ No console logs (use proper logging)

### Testing
- ✅ Unit tests written
- ✅ Tests pass locally
- ✅ Manual testing completed

### Documentation
- ✅ README updated if needed
- ✅ ARCHITECTURE.md updated if design changed
- ✅ Inline comments for complex logic

### Security
- ✅ No hardcoded secrets
- ✅ Input validated
- ✅ No SQL injection risk
- ✅ Error messages don't leak info

---

## Performance Testing

### Benchmarking Search

```python
import time
from utils.loader import load_documents

# Load test documents
docs = load_documents("~/2ndBrain_RAG")
print(f"Loaded {len(docs)} documents")

# Benchmark search
queries = ["machine learning", "RAG", "embeddings", "vector database"]
for query in queries:
    start = time.time()
    results = db.similarity_search(query, k=5)
    elapsed = time.time() - start
    print(f"Search '{query}': {elapsed:.3f}s")
```

### Memory Profiling

```bash
# Install memory_profiler
pip install memory-profiler

# Profile a function
python -m memory_profiler rag_mcp_server.py
```

---

## Debugging Tips

### Enable Debug Logging

```python
# Add to rag_mcp_server.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Then use
logger.debug(f"Searching for: {q}")
logger.info(f"Found {len(results)} results")
logger.error(f"Error: {e}")
```

### Inspect Database State

```python
# Check ChromaDB contents
from langchain.vectorstores import Chroma

db = Chroma(persist_directory=".chroma", embedding_function=embeddings)
all_items = db.get()
print(f"Total items: {len(all_items['ids'])}")
print(f"Sample: {all_items['ids'][:5]}")
```

### Trace API Requests

```bash
# Use curl verbose mode
curl -v http://localhost:8000/search?q=test

# Or use httpie
pip install httpie
http GET http://localhost:8000/search q==test k==5
```

---

## Deployment Considerations

### Local Development
```bash
uvicorn rag_mcp_server:app --reload
```

### Production (Linux/macOS)
```bash
# Use gunicorn for multiple workers
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker rag_mcp_server:app
```

### Docker (Future)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "rag_mcp_server:app", "--host", "0.0.0.0"]
```

---

## Contributing Guidelines

### Before Starting

1. **Check issues** - Is someone already working on this?
2. **Discuss first** - For large changes, open an issue first
3. **Read docs** - Understand ARCHITECTURE.md and CODE_AUDIT.md

### During Development

1. **Keep commits small** - One feature per PR
2. **Write tests** - Aim for >80% coverage
3. **Document changes** - Update relevant markdown files
4. **Follow style** - Use black/ruff for formatting

### After Completing

1. **Self-review** - Use the checklist above
2. **Test thoroughly** - All paths, edge cases
3. **Write good description** - Help reviewers understand
4. **Be responsive** - Address feedback promptly

---

## Troubleshooting Development

### Issue: Import errors after changes
```bash
# Reinstall in development mode
pip install -e .

# Or restart Python environment
deactivate
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Changes not reflected
```bash
# Ensure uvicorn is running with --reload
uvicorn rag_mcp_server:app --reload

# Check for syntax errors
python -m py_compile rag_mcp_server.py utils/*.py
```

### Issue: Database locked
```bash
# ChromaDB might have stale locks
rm -rf .chroma
curl -X POST http://localhost:8000/ingest
```

### Issue: Different behavior locally vs production
```bash
# Check environment variables
echo $RAG_FOLDER
echo $OLLAMA_HOST

# Check Ollama status
curl http://localhost:11434/api/status
```

---

## Pull Request Template

When submitting a PR, use this template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Performance improvement
- [ ] Documentation
- [ ] Refactoring

## Testing Done
- [ ] Unit tests written
- [ ] Manual testing completed
- [ ] Edge cases tested

## Documentation
- [ ] README updated
- [ ] Code documented
- [ ] Architecture docs updated

## Checklist
- [ ] Code follows style guide (PEP 8)
- [ ] No new warnings
- [ ] Tests pass locally
- [ ] Commit messages are clear

## Related Issues
Fixes #123
```

---

## Getting Help

### Documentation
- **CLAUDE_GUIDE.md** - Ask Claude for guidance
- **ARCHITECTURE.md** - Understand system design
- **CODE_AUDIT.md** - Security/quality info
- **API docs** - http://localhost:8000/docs

### Community
- **GitHub Issues** - Report bugs
- **GitHub Discussions** - Ask questions
- **Pull Requests** - Discuss ideas

---

**Development Guide Version**: 1.0
**Last Updated**: October 22, 2025

