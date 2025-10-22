"""Unit tests for document loading and chunking."""

import os
import tempfile
import pytest
from utils.loader import load_documents, _iter_files, _is_path_safe, SUPPORTED_EXTS


class TestPathSafety:
    """Test path traversal protection."""

    def test_safe_path_within_root(self):
        """File within root should be safe."""
        root = "/home/user/docs"
        file_path = "/home/user/docs/file.txt"
        assert _is_path_safe(file_path, root) is True

    def test_safe_path_nested_within_root(self):
        """Nested file within root should be safe."""
        root = "/home/user/docs"
        file_path = "/home/user/docs/subfolder/file.txt"
        assert _is_path_safe(file_path, root) is True

    def test_unsafe_path_outside_root(self):
        """File outside root should be unsafe."""
        root = "/home/user/docs"
        file_path = "/home/user/secret.txt"
        assert _is_path_safe(file_path, root) is False

    def test_unsafe_path_symlink_escape(self, tmp_path):
        """Symlink escape should be detected."""
        # Create root directory
        root = tmp_path / "root"
        root.mkdir()

        # Create external file
        external = tmp_path / "external.txt"
        external.write_text("secret")

        # Create symlink inside root pointing outside
        symlink = root / "link.txt"
        symlink.symlink_to(external)

        # Should detect the escape
        assert _is_path_safe(str(symlink), str(root)) is False

    def test_path_safety_with_expanded_path(self):
        """Should handle tilde expansion."""
        root = "~/docs"
        file_path = os.path.expanduser("~/docs/file.txt")
        assert _is_path_safe(file_path, root) is True


class TestFileIteration:
    """Test recursive file discovery."""

    def test_iter_files_finds_supported_formats(self, tmp_path):
        """Should find all supported file formats."""
        # Create test files
        (tmp_path / "test.txt").write_text("text")
        (tmp_path / "test.md").write_text("markdown")
        (tmp_path / "test.pdf").write_text("pdf")
        (tmp_path / "test.exe").write_text("unsupported")

        # Iterate
        files = list(_iter_files(str(tmp_path)))

        # Should find txt, md, pdf but not exe
        assert len(files) == 3
        assert any("test.txt" in f for f in files)
        assert any("test.md" in f for f in files)
        assert any("test.pdf" in f for f in files)
        assert not any("test.exe" in f for f in files)

    def test_iter_files_recursive(self, tmp_path):
        """Should find files in subdirectories."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.txt").write_text("root")
        (subdir / "nested.txt").write_text("nested")

        # Iterate
        files = list(_iter_files(str(tmp_path)))

        # Should find both
        assert len(files) == 2
        assert any("root.txt" in f for f in files)
        assert any("nested.txt" in f for f in files)

    def test_iter_files_respects_max_files(self, tmp_path):
        """Should respect MAX_FILES limit."""
        # Create many files
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text("content")

        # With low limit
        import utils.loader as loader_module
        original_max = loader_module.MAX_FILES
        try:
            loader_module.MAX_FILES = 3
            files = list(_iter_files(str(tmp_path)))
            assert len(files) <= 3
        finally:
            loader_module.MAX_FILES = original_max

    def test_iter_files_respects_max_size(self, tmp_path):
        """Should skip files exceeding size limit."""
        # Create small and large files
        (tmp_path / "small.txt").write_text("x" * 100)

        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * (101 * 1024 * 1024))  # 101 MB

        # With small limit
        import utils.loader as loader_module
        original_max = loader_module.MAX_FILE_SIZE_MB
        try:
            loader_module.MAX_FILE_SIZE_MB = 100
            files = list(_iter_files(str(tmp_path)))
            # Should only find small file
            assert len(files) == 1
            assert "small.txt" in files[0]
        finally:
            loader_module.MAX_FILE_SIZE_MB = original_max

    def test_iter_files_handles_missing_directory(self):
        """Should handle missing directory gracefully."""
        files = list(_iter_files("/nonexistent/path"))
        assert len(files) == 0

    def test_iter_files_skips_directories(self, tmp_path):
        """Should skip directories, only files."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("content")

        files = list(_iter_files(str(tmp_path)))

        # Should only find file, not directory
        assert len(files) == 1
        assert "file.txt" in files[0]


class TestDocumentLoading:
    """Test document loading and chunking."""

    def test_load_documents_basic(self, tmp_path):
        """Should load and return documents."""
        # Create test file
        (tmp_path / "test.txt").write_text("Hello world. This is a test.")

        # Load
        docs = load_documents(str(tmp_path))

        # Should have documents
        assert len(docs) > 0
        assert any("Hello world" in d.page_content for d in docs)

    def test_load_documents_empty_folder(self, tmp_path):
        """Should return empty list for folder with no supported files."""
        # Create unsupported file
        (tmp_path / "test.exe").write_text("binary")

        # Load
        docs = load_documents(str(tmp_path))

        # Should be empty
        assert len(docs) == 0

    def test_load_documents_metadata_attached(self, tmp_path):
        """Should attach source metadata to documents."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        docs = load_documents(str(tmp_path))

        # Check metadata
        assert len(docs) > 0
        assert all("source" in d.metadata for d in docs)
        assert all("chunk_id" in d.metadata for d in docs)
        assert all(str(test_file) in d.metadata["source"] for d in docs)

    def test_load_documents_chunking(self, tmp_path):
        """Should chunk long documents."""
        # Create long document
        long_text = "word " * 1000  # ~5000 chars
        (tmp_path / "long.txt").write_text(long_text)

        docs = load_documents(str(tmp_path))

        # Should be split into multiple chunks
        assert len(docs) > 1

    def test_load_documents_chunk_ids_unique(self, tmp_path):
        """Chunk IDs should be unique."""
        (tmp_path / "test.txt").write_text("word " * 1000)

        docs = load_documents(str(tmp_path))

        chunk_ids = [d.metadata.get("chunk_id") for d in docs]
        # All unique
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_load_documents_skips_invalid_files(self, tmp_path):
        """Should skip files that can't be parsed."""
        # Valid file
        (tmp_path / "valid.txt").write_text("Content")
        # Invalid file (binary)
        invalid = tmp_path / "invalid.pdf"
        invalid.write_bytes(b"\x00\x01\x02\x03")

        # Should not raise, just skip invalid
        docs = load_documents(str(tmp_path))
        assert len(docs) > 0  # Valid file was loaded

    def test_load_documents_multiple_files(self, tmp_path):
        """Should load from multiple files."""
        (tmp_path / "file1.txt").write_text("Content 1")
        (tmp_path / "file2.txt").write_text("Content 2")

        docs = load_documents(str(tmp_path))

        # Should have documents from both files
        assert len(docs) >= 2
        assert any("Content 1" in d.page_content for d in docs)
        assert any("Content 2" in d.page_content for d in docs)

    def test_load_documents_nonexistent_path(self):
        """Should handle nonexistent path gracefully."""
        docs = load_documents("/nonexistent/path")
        assert len(docs) == 0

    def test_load_documents_preserves_order(self, tmp_path):
        """Documents should maintain consistent ordering."""
        # Create predictable content
        (tmp_path / "aaa.txt").write_text("AAA")
        (tmp_path / "zzz.txt").write_text("ZZZ")

        docs1 = load_documents(str(tmp_path))
        docs2 = load_documents(str(tmp_path))

        # Order should be the same
        assert len(docs1) == len(docs2)
        for d1, d2 in zip(docs1, docs2):
            assert d1.metadata["chunk_id"] == d2.metadata["chunk_id"]

    def test_load_documents_handles_special_chars(self, tmp_path):
        """Should handle special characters in content."""
        test_file = tmp_path / "special.txt"
        test_file.write_text("Test with émojis 🎉 and spëcial çhars")

        docs = load_documents(str(tmp_path))

        assert len(docs) > 0
        assert any("émojis" in d.page_content for d in docs)


class TestSupportedFormats:
    """Test supported file format configuration."""

    def test_supported_exts_not_empty(self):
        """SUPPORTED_EXTS should contain formats."""
        assert len(SUPPORTED_EXTS) > 0

    def test_supported_exts_includes_common_formats(self):
        """Should include common document formats."""
        assert ".txt" in SUPPORTED_EXTS
        assert ".md" in SUPPORTED_EXTS
        assert ".pdf" in SUPPORTED_EXTS
        assert ".json" in SUPPORTED_EXTS

    def test_supported_exts_format(self):
        """Extensions should be lowercase with dot."""
        for ext in SUPPORTED_EXTS:
            assert ext.startswith(".")
            assert ext == ext.lower()


@pytest.fixture
def temp_doc_folder(tmp_path):
    """Fixture providing temp folder with sample documents."""
    (tmp_path / "readme.md").write_text("# README\n\nThis is a test readme.")
    (tmp_path / "notes.txt").write_text("Important notes\nLine 2")

    return tmp_path
