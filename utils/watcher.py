
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.loader import load_documents
from utils.embedder import upsert_documents

class RAGHandler(FileSystemEventHandler):
    def __init__(self, path, db, embeddings):
        self.path = path
        self.db = db
        self.embeddings = embeddings

    def on_any_event(self, event):
        if event.is_directory:
            return
        print(f"🔄 Change detected: {getattr(event, 'src_path', '') or getattr(event, 'dest_path', '')}")
        docs = load_documents(self.path)
        n = upsert_documents(self.db, docs)
        print(f"✅ Re-indexed {n} chunks.")

def start_watcher(path, db, embeddings):
    observer = Observer()
    handler = RAGHandler(path, db, embeddings)
    observer.schedule(handler, path, recursive=True)
    observer.start()
    print(f"👁️ Watching {path} for changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
