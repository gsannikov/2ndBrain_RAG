
import logging
from typing import List
from langchain.schema import Document

logger = logging.getLogger(__name__)


def upsert_documents(db, docs: List[Document]) -> int:
    """
    Add or update documents in the vector database.

    Args:
        db: ChromaDB collection
        docs: List of LangChain Document objects

    Returns:
        Number of documents added

    Raises:
        Exception: If database operation fails
    """
    if not docs:
        logger.debug("No documents to upsert")
        return 0

    try:
        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]
        ids = [m.get("chunk_id") for m in metadatas]

        logger.debug(f"Upserting {len(texts)} documents")
        db.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        logger.debug("Persisting to disk")
        db.persist()

        logger.info(f"Successfully upserted {len(texts)} documents")
        return len(texts)

    except Exception as e:
        logger.error(f"Error upserting documents: {e}")
        raise


def reset_index(db) -> None:
    """
    Clear all documents from the vector database.

    Args:
        db: ChromaDB collection

    Raises:
        Exception: If reset fails (logged but may not raise)
    """
    try:
        logger.info("Clearing vector database index")

        # Get all IDs first
        data = db.get()
        all_ids = data.get("ids", [])

        if not all_ids:
            logger.info("Index is already empty")
            return

        # Delete all documents
        # Note: Using _collection is necessary as ChromaDB doesn't expose
        # a public clear() method. This should be updated when ChromaDB
        # provides a public API for this.
        logger.debug(f"Deleting {len(all_ids)} documents")
        db.delete(ids=all_ids)

        logger.debug("Persisting changes")
        db.persist()

        logger.info("Index cleared successfully")

    except AttributeError:
        # Fallback if delete() isn't available
        logger.warning("db.delete() not available, attempting private API")
        try:
            db._collection.delete(where={})
            db.persist()
            logger.info("Index cleared using private API")
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            raise

    except Exception as e:
        logger.error(f"Error resetting index: {e}")
        raise
