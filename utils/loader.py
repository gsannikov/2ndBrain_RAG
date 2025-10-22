
import os
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

SUPPORTED_EXTS = {
    ".txt", ".md", ".rtf", ".pdf", ".doc", ".docx",
    ".ppt", ".pptx", ".html", ".htm", ".csv", ".tsv", ".json",
    ".py", ".ipynb"
}

def _iter_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTS:
                yield os.path.join(dirpath, name)

def load_documents(path: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    docs = []
    for fp in _iter_files(path):
        try:
            loader = UnstructuredFileLoader(fp)
            file_docs = loader.load()
            for d in file_docs:
                d.metadata = d.metadata or {}
                d.metadata["source"] = fp
            chunks = splitter.split_documents(file_docs)
            for i, ch in enumerate(chunks):
                ch.metadata["chunk_id"] = f"{fp}::chunk_{i}"
            docs.extend(chunks)
        except Exception as e:
            print(f"⚠️ Skipping {fp}: {e}")
    return docs
