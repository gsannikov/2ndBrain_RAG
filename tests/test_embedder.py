"""Unit tests for vector database operations."""

import pytest
from langchain.schema import Document
from utils.embedder import upsert_documents, reset_index


class MockChromaDB:
    """Mock ChromaDB collection for testing."""

    def __init__(self):
        """Initialize mock database."""
        self.documents = {}
        self.persisted = False

    def add_texts(self, texts, metadatas, ids):
        """Mock add_texts method."""
        for text, metadata, doc_id in zip(texts, metadatas, ids):
            self.documents[doc_id] = {
                "text": text,
                "metadata": metadata
            }

    def delete(self, ids):
        """Mock delete method."""
        for doc_id in ids:
            if doc_id in self.documents:
                del self.documents[doc_id]

    def get(self):
        """Mock get method."""
        return {"ids": list(self.documents.keys())}

    def persist(self):
        """Mock persist method."""
        self.persisted = True

    def __len__(self):
        """Return number of documents."""
        return len(self.documents)


class TestUpsertDocuments:
    """Test document upsert functionality."""

    def test_upsert_single_document(self):
        """Should upsert a single document."""
        db = MockChromaDB()
        doc = Document(
            page_content="Test content",
            metadata={
                "source": "test.txt",
                "chunk_id": "test.txt::chunk_0"
            }
        )

        count = upsert_documents(db, [doc])

        assert count == 1
        assert len(db) == 1
        assert db.persisted

    def test_upsert_multiple_documents(self):
        """Should upsert multiple documents."""
        db = MockChromaDB()
        docs = [
            Document(
                page_content=f"Content {i}",
                metadata={
                    "source": "test.txt",
                    "chunk_id": f"test.txt::chunk_{i}"
                }
            )
            for i in range(5)
        ]

        count = upsert_documents(db, docs)

        assert count == 5
        assert len(db) == 5

    def test_upsert_empty_list(self):
        """Should handle empty document list."""
        db = MockChromaDB()
        count = upsert_documents(db, [])

        assert count == 0
        assert len(db) == 0
        assert not db.persisted  # Should not persist empty

    def test_upsert_preserves_metadata(self):
        """Should preserve document metadata."""
        db = MockChromaDB()
        metadata = {
            "source": "document.pdf",
            "chunk_id": "doc.pdf::chunk_3",
            "page": "5"
        }
        doc = Document(
            page_content="Sample text",
            metadata=metadata
        )

        upsert_documents(db, [doc])

        stored = db.documents["doc.pdf::chunk_3"]
        assert stored["metadata"]["source"] == "document.pdf"
        assert stored["metadata"]["page"] == "5"

    def test_upsert_persists_to_disk(self):
        """Should persist after upsert."""
        db = MockChromaDB()
        doc = Document(
            page_content="Content",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )

        upsert_documents(db, [doc])

        assert db.persisted

    def test_upsert_overwrites_existing(self):
        """Should overwrite existing documents with same ID."""
        db = MockChromaDB()

        # Add first version
        doc1 = Document(
            page_content="Old content",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )
        upsert_documents(db, [doc1])

        # Add second version with same ID
        doc2 = Document(
            page_content="New content",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )
        upsert_documents(db, [doc2])

        assert len(db) == 1
        assert db.documents["chunk_0"]["text"] == "New content"

    def test_upsert_with_long_content(self):
        """Should handle long document content."""
        db = MockChromaDB()
        long_content = "word " * 10000  # ~50KB

        doc = Document(
            page_content=long_content,
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )

        count = upsert_documents(db, [doc])

        assert count == 1
        assert db.documents["chunk_0"]["text"] == long_content

    def test_upsert_with_special_characters(self):
        """Should handle special characters in content."""
        db = MockChromaDB()
        special_content = "Test with émojis 🎉 and ñ and ü"

        doc = Document(
            page_content=special_content,
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )

        count = upsert_documents(db, [doc])

        assert count == 1
        assert "émojis" in db.documents["chunk_0"]["text"]


class TestResetIndex:
    """Test index reset functionality."""

    def test_reset_empty_database(self):
        """Should handle resetting empty database."""
        db = MockChromaDB()
        # Should not raise
        reset_index(db)
        assert len(db) == 0
        assert db.persisted

    def test_reset_clears_all_documents(self):
        """Should clear all documents."""
        db = MockChromaDB()

        # Add documents
        docs = [
            Document(
                page_content=f"Content {i}",
                metadata={"source": "test", "chunk_id": f"chunk_{i}"}
            )
            for i in range(5)
        ]
        upsert_documents(db, docs)
        assert len(db) == 5

        # Reset
        reset_index(db)

        # Should be empty
        assert len(db) == 0

    def test_reset_persists(self):
        """Should persist after reset."""
        db = MockChromaDB()

        # Add then reset
        doc = Document(
            page_content="Content",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )
        upsert_documents(db, [doc])
        db.persisted = False  # Reset flag

        reset_index(db)

        assert db.persisted

    def test_reset_multiple_times(self):
        """Should be able to reset multiple times."""
        db = MockChromaDB()

        for iteration in range(3):
            # Add documents
            doc = Document(
                page_content=f"Content {iteration}",
                metadata={"source": "test", "chunk_id": "chunk_0"}
            )
            upsert_documents(db, [doc])
            assert len(db) == 1

            # Reset
            reset_index(db)
            assert len(db) == 0

    def test_reset_then_upsert(self):
        """Should be able to upsert after reset."""
        db = MockChromaDB()

        # Add, reset, then add again
        doc1 = Document(
            page_content="First",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )
        upsert_documents(db, [doc1])
        reset_index(db)

        doc2 = Document(
            page_content="Second",
            metadata={"source": "test", "chunk_id": "chunk_0"}
        )
        upsert_documents(db, [doc2])

        assert len(db) == 1
        assert db.documents["chunk_0"]["text"] == "Second"


class TestErrorHandling:
    """Test error handling in embedder."""

    def test_upsert_with_missing_chunk_id(self):
        """Should handle documents without chunk_id."""
        db = MockChromaDB()
        doc = Document(
            page_content="Content",
            metadata={"source": "test"}  # Missing chunk_id
        )

        # Should handle None chunk_id gracefully
        count = upsert_documents(db, [doc])
        assert count == 1

    def test_upsert_with_none_metadata(self):
        """Should handle None metadata."""
        db = MockChromaDB()
        doc = Document(
            page_content="Content",
            metadata=None
        )

        # Should not raise
        try:
            upsert_documents(db, [doc])
        except Exception as e:
            pytest.fail(f"Upsert raised exception: {e}")

    def test_upsert_batch_consistency(self):
        """All documents in batch should be added."""
        db = MockChromaDB()
        docs = [
            Document(
                page_content=f"Content {i}",
                metadata={"source": f"file_{i}.txt", "chunk_id": f"chunk_{i}"}
            )
            for i in range(10)
        ]

        count = upsert_documents(db, docs)

        assert count == 10
        assert len(db) == 10


class TestIntegration:
    """Integration tests."""

    def test_workflow_add_reset_add(self):
        """Test typical workflow: add, reset, add."""
        db = MockChromaDB()

        # First batch
        docs1 = [
            Document(
                page_content=f"First batch {i}",
                metadata={"source": "first.txt", "chunk_id": f"chunk_{i}"}
            )
            for i in range(3)
        ]
        count1 = upsert_documents(db, docs1)
        assert count1 == 3
        assert len(db) == 3

        # Reset
        reset_index(db)
        assert len(db) == 0

        # Second batch
        docs2 = [
            Document(
                page_content=f"Second batch {i}",
                metadata={"source": "second.txt", "chunk_id": f"new_chunk_{i}"}
            )
            for i in range(5)
        ]
        count2 = upsert_documents(db, docs2)
        assert count2 == 5
        assert len(db) == 5

    def test_workflow_incremental_updates(self):
        """Test incremental updates with upsert."""
        db = MockChromaDB()

        # Initial documents
        docs1 = [
            Document(
                page_content="Content A",
                metadata={"source": "file.txt", "chunk_id": "chunk_0"}
            ),
            Document(
                page_content="Content B",
                metadata={"source": "file.txt", "chunk_id": "chunk_1"}
            )
        ]
        upsert_documents(db, docs1)
        assert len(db) == 2

        # Add more documents
        docs2 = [
            Document(
                page_content="Content C",
                metadata={"source": "file.txt", "chunk_id": "chunk_2"}
            )
        ]
        upsert_documents(db, docs2)
        assert len(db) == 3

        # Update existing document
        docs3 = [
            Document(
                page_content="Updated Content A",
                metadata={"source": "file.txt", "chunk_id": "chunk_0"}
            )
        ]
        upsert_documents(db, docs3)
        assert len(db) == 3
        assert db.documents["chunk_0"]["text"] == "Updated Content A"
