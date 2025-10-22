
import time
import logging
from threading import RLock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.loader import load_documents
from utils.embedder import upsert_documents

logger = logging.getLogger(__name__)


class RAGHandler(FileSystemEventHandler):
    """Handles file system events and triggers reindexing."""

    def __init__(self, path: str, db, embeddings, db_lock: RLock):
        """
        Initialize the RAG file system event handler.

        Args:
            path: Root RAG folder path
            db: ChromaDB collection
            embeddings: Embedding model
            db_lock: Thread lock for database access
        """
        self.path = path
        self.db = db
        self.embeddings = embeddings
        self.db_lock = db_lock
        self.last_reindex_time = 0
        self.reindex_cooldown = 5  # Seconds (debounce rapid events)

    def on_any_event(self, event):
        """Handle file system events."""
        if event.is_directory:
            return

        # Get the changed file path
        changed_path = getattr(event, 'src_path', '') or getattr(event, 'dest_path', '')

        # Debouncing: Don't reindex if we just did
        current_time = time.time()
        if current_time - self.last_reindex_time < self.reindex_cooldown:
            logger.debug(f"Skipping reindex (cooldown): {changed_path}")
            return

        logger.info(f"File change detected: {changed_path}")
        self._reindex()
        self.last_reindex_time = current_time

    def _reindex(self):
        """Reload and reindex documents."""
        try:
            with self.db_lock:
                logger.debug("Loading documents after file change")
                docs = load_documents(self.path)

                if not docs:
                    logger.warning("No documents found after file change")
                    return

                n = upsert_documents(self.db, docs)
                logger.info(f"Re-indexed {n} chunks after file change")

        except Exception as e:
            logger.error(f"Error during file watcher reindex: {e}")


def start_watcher(path: str, db, embeddings, db_lock: RLock) -> None:
    """
    Start watching RAG folder for file changes.

    Args:
        path: Root RAG folder path
        db: ChromaDB collection
        embeddings: Embedding model
        db_lock: Thread lock for thread-safe database access

    Note:
        Runs as a daemon thread. Blocking call (runs event loop).
    """
    logger.info(f"Starting file watcher for: {path}")

    observer = Observer()
    handler = RAGHandler(path, db, embeddings, db_lock)

    try:
        observer.schedule(handler, path, recursive=True)
        observer.start()
        logger.info("File watcher active, watching for changes...")

        # Run indefinitely until KeyboardInterrupt
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("File watcher interrupted")
    except Exception as e:
        logger.error(f"File watcher error: {e}")
    finally:
        logger.info("Stopping file watcher...")
        observer.stop()
        observer.join()
        logger.info("File watcher stopped")
