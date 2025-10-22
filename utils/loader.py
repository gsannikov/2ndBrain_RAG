
import os
import logging
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {
    ".txt", ".md", ".rtf", ".pdf", ".doc", ".docx",
    ".ppt", ".pptx", ".html", ".htm", ".csv", ".tsv", ".json",
    ".py", ".ipynb"
}

# Configuration
MAX_FILE_SIZE_MB = 100
MAX_FILES = 10000


def _is_path_safe(file_path: str, root_path: str) -> bool:
    """
    Check if file_path is within root_path (prevents path traversal).

    Args:
        file_path: Path to check
        root_path: Root directory

    Returns:
        True if file is safely within root
    """
    try:
        # Resolve both to absolute, real paths
        real_root = os.path.realpath(os.path.expanduser(root_path))
        real_file = os.path.realpath(file_path)

        # Check if file path starts with root path
        return real_file.startswith(real_root + os.sep) or real_file == real_root
    except Exception as e:
        logger.error(f"Path safety check failed: {e}")
        return False


def _iter_files(root: str):
    """Recursively find supported document files."""
    root_expanded = os.path.expanduser(root)
    if not os.path.isdir(root_expanded):
        logger.warning(f"RAG folder not found: {root_expanded}")
        return

    file_count = 0
    for dirpath, _, filenames in os.walk(root_expanded):
        if file_count >= MAX_FILES:
            logger.warning(f"Hit maximum file limit: {MAX_FILES}")
            break

        for name in filenames:
            if file_count >= MAX_FILES:
                break

            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue

            full_path = os.path.join(dirpath, name)

            # Security: Check for path traversal
            if not _is_path_safe(full_path, root_expanded):
                logger.warning(f"Skipping path outside root (potential traversal): {full_path}")
                continue

            # Check file size
            try:
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                if size_mb > MAX_FILE_SIZE_MB:
                    logger.warning(f"Skipping {full_path}: exceeds {MAX_FILE_SIZE_MB}MB limit ({size_mb:.1f}MB)")
                    continue
            except OSError as e:
                logger.warning(f"Cannot check size of {full_path}: {e}")
                continue

            file_count += 1
            yield full_path

    logger.debug(f"Scanned {file_count} files")


def load_documents(path: str):
    """
    Load and chunk all supported documents from a folder.

    Args:
        path: Root folder path

    Returns:
        List of LangChain Document chunks

    Raises:
        None (errors logged, files skipped)
    """
    logger.info(f"Loading documents from: {path}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    docs = []
    file_count = 0
    skip_count = 0

    for fp in _iter_files(path):
        file_count += 1
        try:
            logger.debug(f"Loading {fp}")
            loader = UnstructuredFileLoader(fp)
            file_docs = loader.load()

            if not file_docs:
                logger.debug(f"No content extracted from {fp}")
                skip_count += 1
                continue

            # Attach source metadata
            for d in file_docs:
                d.metadata = d.metadata or {}
                d.metadata["source"] = fp

            # Split into chunks
            chunks = splitter.split_documents(file_docs)
            for i, ch in enumerate(chunks):
                ch.metadata["chunk_id"] = f"{fp}::chunk_{i}"

            docs.extend(chunks)
            logger.debug(f"Extracted {len(chunks)} chunks from {fp}")

        except TypeError:
            logger.debug(f"Format not supported by Unstructured: {fp}")
            skip_count += 1
        except Exception as e:
            logger.warning(f"Error loading {fp}: {e.__class__.__name__}: {str(e)[:100]}")
            skip_count += 1

    logger.info(f"Loaded {len(docs)} document chunks from {file_count} files ({skip_count} skipped)")
    return docs
