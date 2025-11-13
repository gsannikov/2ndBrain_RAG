import os
import hashlib
import json
from pathlib import Path

from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from rapidfuzz import fuzz
from mcp.server import Server
from mcp.types import TextContent
from ingest.extractor import read_text_with_ocr as read_text

load_dotenv()

ROOT = Path(os.getenv("ROOT_DIR", ".")).resolve()
ALLOWED = set(e.strip().lower() for e in os.getenv("ALLOWED_EXTS",".pdf,.txt,.md").split(","))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE","3000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP","400"))
PERSIST_DIR = os.getenv("PERSIST_DIR",".chromadb")
EMBED_MODEL = os.getenv("EMBED_MODEL","sentence-transformers/all-MiniLM-L6-v2")
STATE_PATH = Path("state/ingest_state.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

server = Server("local-rag")
model = SentenceTransformer(EMBED_MODEL)
client = chromadb.PersistentClient(path=PERSIST_DIR, settings=Settings(allow_reset=True))
COLL = client.get_or_create_collection("docs", metadata={"hnsw:space":"cosine"})

def fhash(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_state():
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}

def save_state(s):
    STATE_PATH.write_text(json.dumps(s, indent=2))

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    n = len(text)
    i = 0
    while i < n:
        j = min(n, i + size)
        yield i, j, text[i:j]
        if j == n:
            break
        i = j - overlap

def upsert_file(p: Path, state: dict):
    if not p.exists() or not p.is_file():
        return
    if p.suffix.lower() not in ALLOWED:
        return
    if p.stat().st_size > int(os.getenv("MAX_FILE_MB","80")) * (1<<20):
        return

    try:
        txt = read_text(p)
    except Exception:
        return
    if not txt.strip():
        return

    COLL.delete(where={"path": str(p)})

    ids, docs, metas = [], [], []
    for k,(a,b,seg) in enumerate(chunk_text(txt)):
        ids.append(f"{p}:{a}-{b}")
        docs.append(seg)
        metas.append({"path":str(p), "start":a, "end":b, "mtime": int(p.stat().st_mtime)})
    if not docs:
        return

    vecs = model.encode(docs, normalize_embeddings=True)
    COLL.add(ids=ids, embeddings=vecs.tolist(), documents=docs, metadatas=metas)

    state[str(p)] = {"hash": fhash(p), "mtime": int(p.stat().st_mtime)}
    save_state(state)

def delete_file(p: Path, state: dict):
    COLL.delete(where={"path": str(p)})
    state.pop(str(p), None)
    save_state(state)

def initial_scan():
    st = load_state()
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in ALLOWED:
            h = fhash(p)
            prev = st.get(str(p), {}).get("hash")
            if h != prev:
                upsert_file(p, st)
    save_state(st)

class Handler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() not in ALLOWED:
            return
        st = load_state()
        if event.event_type in {"created","modified"} and p.exists():
            h = fhash(p)
            if st.get(str(p), {}).get("hash") != h:
                upsert_file(p, st)
        elif event.event_type == "deleted":
            delete_file(p, st)

@server.tool()
def rag_stats() -> TextContent:
    count = COLL.count()
    return TextContent(text=json.dumps({"chunks": count, "persist_dir": PERSIST_DIR}, indent=2))

@server.tool()
def rag_reindex(paths: list[str] | None = None) -> TextContent:
    st = load_state()
    if not paths:
        initial_scan()
        return TextContent(text="Reindexed all changed files.")
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    upsert_file(f, st)
        elif p.is_file():
            upsert_file(p, st)
    return TextContent(text=f"Reindexed {len(paths)} path(s).")

@server.tool()
def rag_search(query: str, k: int = 6, path_filter: str | None = None) -> TextContent:
    where = {"path": {"$contains": path_filter}} if path_filter else None
    qvec = model.encode([query])[0].tolist()
    res = COLL.query(query_embeddings=[qvec], n_results=k, where=where, include=["documents","metadatas","distances"])
    items=[]
    if res.get("ids"):
        for i in range(len(res["ids"][0])):
            meta = res["metadatas"][0][i]
            doc = res["documents"][0][i]
            score = 1 - float(res["distances"][0][i])
            score = 0.8*score + 0.2*(fuzz.partial_ratio(query, doc[:800])/100)
            items.append({
                "path": meta["path"],
                "score": round(score,4),
                "start": meta["start"],
                "end": meta["end"],
                "preview": doc[:500].replace("\n"," ")
            })
    return TextContent(text=json.dumps({"query": query, "results": items}, indent=2))

@server.tool()
def rag_get(path: str, start: int | None = None, end: int | None = None, window: int = 1200) -> TextContent:
    p = Path(path)
    if not p.exists():
        return TextContent(text=json.dumps({"error":"not found"}))
    try:
        txt = read_text(p)
    except Exception as e:
        return TextContent(text=json.dumps({"error": str(e)}))
    if start is None and end is None:
        out = txt[:min(len(txt), window)]
        span = [0, len(out)]
    else:
        s = max(0, (start or 0) - window//4)
        e = min(len(txt), (end or (start or 0)) + window//4)
        out = txt[s:e]
        span = [s,e]
    return TextContent(text=json.dumps({"path": path, "span": span, "text": out}, indent=2))

@server.tool()
def rag_invalidate(path: str) -> TextContent:
    p = Path(path)
    COLL.delete(where={"path": str(p)})
    st = load_state()
    st.pop(str(p), None)
    save_state(st)
    return TextContent(text=f"Invalidated {path}")

def run():
    initial_scan()
    obs = Observer()
    obs.schedule(Handler(), str(ROOT), recursive=True)
    obs.start()
    try:
        server.run_stdio()
    finally:
        obs.stop()
        obs.join()

if __name__ == "__main__":
    run()
