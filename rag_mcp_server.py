import os
import argparse
import logging
from threading import Thread, RLock
from fastapi import FastAPI, Query, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from utils.loader import load_documents
from utils.embedder import upsert_documents, reset_index
from utils.watcher import start_watcher
from utils.llm import ollama_chat
from utils.cache import clear_cache, get_cache_stats
from utils.ratelimit import RateLimitMiddleware

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="2ndBrain_RAG MCP Server (with Ollama)")

# Add rate limiting middleware
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=RATE_LIMIT_PER_MINUTE)
    logger.info(f"Rate limiting enabled: {RATE_LIMIT_PER_MINUTE} req/min")
else:
    logger.info("Rate limiting disabled")

# Configuration
API_KEY = os.getenv("RAG_API_KEY", None)  # Optional API key for authentication
MAX_QUERY_LENGTH = 500
MAX_K_VALUE = 100
MIN_K_VALUE = 1

class ChatRequest(BaseModel):
    query: str = Field(..., max_length=500, description="User question")
    k: int = Field(default=5, ge=1, le=100, description="Number of results")
    system: str | None = Field(None, max_length=500, description="System prompt")
    model: str | None = Field(None, description="Ollama model name")

def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Optional API key verification if RAG_API_KEY is set."""
    if API_KEY and x_api_key != API_KEY:
        logger.warning("Unauthorized access attempt")
        raise HTTPException(status_code=403, detail="Invalid API key")
    return None

def resolve_rag_path():
    """Resolve RAG folder path from arguments or environment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to your RAG folder (data root)")
    args, _ = parser.parse_known_args()  # Use parse_known_args to avoid conflicts
    path = args.path or os.getenv("RAG_FOLDER", "~/2ndBrain_RAG")
    expanded = os.path.expanduser(path)
    logger.info(f"RAG folder: {expanded}")
    return expanded

RAG_PATH = resolve_rag_path()
DB_PATH = os.path.join(RAG_PATH, ".chroma")
os.makedirs(DB_PATH, exist_ok=True)
logger.info(f"Database path: {DB_PATH}")

# Thread-safe lock for ChromaDB access (prevents race conditions)
db_lock = RLock()

try:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    logger.info("ChromaDB initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    raise

@app.get("/status")
def status(api_key: None = Depends(verify_api_key)):
    """Get indexing status and statistics."""
    try:
        with db_lock:
            data = db.get()
            count = len(data.get("ids", []))
        logger.info(f"Status check: {count} documents indexed")
        return {"rag_path": RAG_PATH, "db_path": DB_PATH, "documents_indexed": count}
    except (KeyError, TypeError) as e:
        logger.warning(f"Error getting status: {e}")
        return {"rag_path": RAG_PATH, "db_path": DB_PATH, "documents_indexed": 0}
    except Exception as e:
        logger.error(f"Unexpected error in status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@app.post("/ingest")
def ingest(full_rebuild: bool = False, api_key: None = Depends(verify_api_key)):
    """Load and index documents from RAG folder."""
    logger.info(f"Starting ingest (full_rebuild={full_rebuild})")
    try:
        with db_lock:
            if full_rebuild:
                logger.info("Clearing existing index")
                reset_index(db)
                # Clear search cache when reindexing
                clear_cache()
                logger.info("Cache cleared due to full rebuild")

            logger.info("Loading documents from RAG folder")
            docs = load_documents(RAG_PATH)

            if not docs:
                logger.warning("No documents found to index")
                return {"status": "ok", "indexed_chunks": 0, "source_path": RAG_PATH}

            logger.info(f"Upserting {len(docs)} document chunks")
            n = upsert_documents(db, docs)
            logger.info(f"Ingest complete: {n} chunks indexed")

            # Clear cache on any ingest (documents changed)
            clear_cache()
            logger.info("Cache cleared after ingest")

        return {"status": "ok", "indexed_chunks": n, "source_path": RAG_PATH}
    except Exception as e:
        logger.error(f"Error during ingest: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)[:100]}")

@app.get("/search")
def search(
    q: str = Query(..., max_length=MAX_QUERY_LENGTH, description="Search query"),
    k: int = Query(5, ge=MIN_K_VALUE, le=MAX_K_VALUE, description="Number of results"),
    api_key: None = Depends(verify_api_key)
):
    """Semantic search over indexed documents."""
    if not q.strip():
        logger.warning("Empty search query")
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Search query: '{q[:50]}...' k={k}")
    try:
        with db_lock:
            results = db.similarity_search(q, k=k)

        logger.info(f"Found {len(results)} results")
        return {
            "query": q,
            "k": k,
            "results": [
                {
                    "source": r.metadata.get("source", "unknown"),
                    "chunk_id": r.metadata.get("chunk_id", "unknown"),
                    "content": r.page_content[:500]  # Limit content size in response
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/cache-stats")
def cache_stats(api_key: None = Depends(verify_api_key)):
    """Get cache performance statistics."""
    logger.info("Cache stats requested")
    try:
        stats = get_cache_stats()
        return {
            "cache": stats,
            "message": "Cache statistics"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")

@app.post("/chat")
def chat(req: ChatRequest, api_key: None = Depends(verify_api_key)):
    """RAG-based question answering with citations."""
    logger.info(f"Chat query: '{req.query[:50]}...'")
    try:
        with db_lock:
            docs = db.similarity_search(req.query, k=req.k)

        if not docs:
            logger.warning("No documents found for chat query")
            return {
                "answer": "No relevant documents found in the knowledge base.",
                "citations": []
            }

        # Format context with proper escaping
        context_parts = []
        for i, d in enumerate(docs):
            source = d.metadata.get("source", "unknown")
            content = d.page_content[:1000]  # Limit content
            context_parts.append(f"[{i+1}] {content}\nSOURCE: {source}")

        context = "\n\n".join(context_parts)

        # Build prompt
        system_prompt = req.system or "You are a helpful, concise assistant."
        prompt = f"""Answer the user's question STRICTLY using the CONTEXT provided.
If the answer is not present in the context, say you don't know.
Cite sources as [n] matching the provided context blocks.

QUESTION: {req.query}

CONTEXT:
{context}

Provide a concise answer with citations like [1], [2]."""

        logger.info("Calling Ollama for chat response")
        answer = ollama_chat(prompt, system=system_prompt, model=req.model)

        citations = [
            {"index": i+1, "source": d.metadata.get("source", "unknown")}
            for i, d in enumerate(docs)
        ]

        logger.info(f"Chat complete: {len(citations)} citations")
        return {"answer": answer, "citations": citations}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("2ndBrain_RAG Server Starting")
    logger.info("=" * 60)
    logger.info(f"API Key Required: {bool(API_KEY)}")
    logger.info(f"RAG Folder: {RAG_PATH}")
    logger.info(f"Database: {DB_PATH}")

    # Start file watcher in background
    try:
        watcher_thread = Thread(
            target=start_watcher,
            args=(RAG_PATH, db, embeddings, db_lock),
            daemon=True,
            name="FileWatcher"
        )
        watcher_thread.start()
        logger.info("File watcher started")
    except Exception as e:
        logger.error(f"Failed to start file watcher: {e}")

    logger.info("Starting Uvicorn server on 0.0.0.0:8000")
    logger.info("API docs: http://localhost:8000/docs")
    logger.info("=" * 60)

    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None  # Use our logging configuration
    )
