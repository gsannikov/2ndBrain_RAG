
from typing import List
from langchain.schema import Document

def upsert_documents(db, docs: List[Document]) -> int:
    if not docs:
        return 0
    texts = [d.page_content for d in docs]
    metadatas = [d.metadata for d in docs]
    ids = [m.get("chunk_id") for m in metadatas]
    db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    db.persist()
    return len(texts)

def reset_index(db):
    try:
        db._collection.delete(where={})
        db.persist()
    except Exception:
        pass
