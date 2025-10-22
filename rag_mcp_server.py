
    import os
    import argparse
    from threading import Thread
    from fastapi import FastAPI, Query
    from pydantic import BaseModel
    from langchain.vectorstores import Chroma
    from langchain.embeddings import HuggingFaceEmbeddings
    from utils.loader import load_documents
    from utils.embedder import upsert_documents, reset_index
    from utils.watcher import start_watcher
    from utils.llm import ollama_chat

    app = FastAPI(title="2ndBrain_RAG MCP Server (with Ollama)")

    class ChatRequest(BaseModel):
        query: str
        k: int = 5
        system: str | None = None
        model: str | None = None

    def resolve_rag_path():
        parser = argparse.ArgumentParser()
        parser.add_argument("--path", type=str, help="Path to your RAG folder (data root)")
        args = parser.parse_args()
        return os.path.expanduser(args.path or os.getenv("RAG_FOLDER", "~/2ndBrain_RAG"))

    RAG_PATH = resolve_rag_path()
    DB_PATH = os.path.join(RAG_PATH, ".chroma")
    os.makedirs(DB_PATH, exist_ok=True)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    @app.get("/status")
    def status():
        try:
            ids = db.get()["ids"]
            count = len(ids)
        except Exception:
            count = -1
        return {"rag_path": RAG_PATH, "db_path": DB_PATH, "documents_indexed": count}

    @app.post("/ingest")
    def ingest(full_rebuild: bool = False):
        if full_rebuild:
            reset_index(db)
        docs = load_documents(RAG_PATH)
        n = upsert_documents(db, docs)
        return {"status": "ok", "indexed_chunks": n, "source_path": RAG_PATH}

    @app.get("/search")
    def search(q: str = Query(..., description="Search query"), k: int = 5):
        results = db.similarity_search(q, k=k)
        return {
            "query": q,
            "k": k,
            "results": [
                {"source": r.metadata.get("source"), "chunk_id": r.metadata.get("chunk_id"), "content": r.page_content}
                for r in results
            ],
        }

    @app.post("/chat")
    def chat(req: ChatRequest):
        docs = db.similarity_search(req.query, k=req.k)
        context = "\n\n".join([f"[{i+1}] {d.page_content}\nSOURCE: {d.metadata.get('source')}" for i, d in enumerate(docs)])
        prompt = f"""You are a helpful assistant. Answer the user's question strictly using the CONTEXT.
If the answer is not present in the context, say you don't know and suggest where to look in the files.
Cite sources as [n] matching the provided context blocks.

QUESTION: {req.query}

CONTEXT:
{context}

Provide a concise answer with citations like [1], [2]."""
        answer = ollama_chat(prompt, system=req.system, model=req.model)
        citations = [{"index": i+1, "source": d.metadata.get("source")} for i, d in enumerate(docs)]
        return {"answer": answer, "citations": citations}

    if __name__ == "__main__":
        Thread(target=start_watcher, args=(RAG_PATH, db, embeddings), daemon=True).start()
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
