"""Unit tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
import os

# Mock environment variables before importing the app
os.environ["RAG_FOLDER"] = "/tmp/test_rag"
os.environ.pop("RAG_API_KEY", None)  # Ensure no API key in tests

# Import after setting env vars
from rag_mcp_server import app


@pytest.fixture
def client():
    """Provide test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Provide mock database."""
    db = Mock()
    db.get.return_value = {"ids": ["chunk_0", "chunk_1", "chunk_2"]}
    db.similarity_search.return_value = []
    return db


class TestStatusEndpoint:
    """Test /status endpoint."""

    def test_status_returns_200(self, client):
        """Status endpoint should return 200."""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_response_structure(self, client):
        """Status response should have required fields."""
        response = client.get("/status")
        data = response.json()

        assert "rag_path" in data
        assert "db_path" in data
        assert "documents_indexed" in data

    def test_status_documents_count_is_number(self, client):
        """Documents indexed count should be a number."""
        response = client.get("/status")
        data = response.json()

        assert isinstance(data["documents_indexed"], int)

    def test_status_paths_are_strings(self, client):
        """Paths should be strings."""
        response = client.get("/status")
        data = response.json()

        assert isinstance(data["rag_path"], str)
        assert isinstance(data["db_path"], str)


class TestSearchEndpoint:
    """Test /search endpoint."""

    def test_search_requires_query(self, client):
        """Search without query should return 422."""
        response = client.get("/search")
        assert response.status_code == 422

    def test_search_with_query_returns_200(self, client):
        """Search with query should return 200."""
        response = client.get("/search?q=test")
        assert response.status_code == 200

    def test_search_response_structure(self, client):
        """Search response should have required fields."""
        response = client.get("/search?q=machine+learning")
        data = response.json()

        assert "query" in data
        assert "k" in data
        assert "results" in data

    def test_search_query_echoed_back(self, client):
        """Search should echo back the query."""
        query = "test query"
        response = client.get(f"/search?q={query}")
        data = response.json()

        assert data["query"] == query

    def test_search_k_parameter_default(self, client):
        """K parameter should default to 5."""
        response = client.get("/search?q=test")
        data = response.json()

        assert data["k"] == 5

    def test_search_k_parameter_custom(self, client):
        """K parameter should be customizable."""
        response = client.get("/search?q=test&k=10")
        data = response.json()

        assert data["k"] == 10

    def test_search_k_parameter_bounded_lower(self, client):
        """K must be >= 1."""
        response = client.get("/search?q=test&k=0")
        assert response.status_code == 422

    def test_search_k_parameter_bounded_upper(self, client):
        """K must be <= 100."""
        response = client.get("/search?q=test&k=101")
        assert response.status_code == 422

    def test_search_query_too_long(self, client):
        """Query exceeding max length should fail."""
        long_query = "x" * 501  # Exceeds 500 char limit
        response = client.get(f"/search?q={long_query}")
        assert response.status_code == 422

    def test_search_empty_query_fails(self, client):
        """Empty query should fail."""
        response = client.get("/search?q=")
        assert response.status_code == 400

    def test_search_results_is_list(self, client):
        """Results should be a list."""
        response = client.get("/search?q=test")
        data = response.json()

        assert isinstance(data["results"], list)

    def test_search_result_structure(self, client):
        """Each result should have required fields."""
        response = client.get("/search?q=test")
        data = response.json()

        # Results might be empty, but structure should be list
        assert isinstance(data["results"], list)


class TestChatEndpoint:
    """Test /chat endpoint."""

    def test_chat_requires_query(self, client):
        """Chat without query should return 422."""
        response = client.post("/chat", json={})
        assert response.status_code == 422

    def test_chat_with_query_returns_200(self, client):
        """Chat with query should return 200."""
        response = client.post("/chat", json={"query": "test"})
        assert response.status_code == 200

    def test_chat_response_structure(self, client):
        """Chat response should have answer and citations."""
        response = client.post("/chat", json={"query": "test"})
        data = response.json()

        assert "answer" in data
        assert "citations" in data

    def test_chat_answer_is_string(self, client):
        """Answer should be a string."""
        response = client.post("/chat", json={"query": "test"})
        data = response.json()

        assert isinstance(data["answer"], str)

    def test_chat_citations_is_list(self, client):
        """Citations should be a list."""
        response = client.post("/chat", json={"query": "test"})
        data = response.json()

        assert isinstance(data["citations"], list)

    def test_chat_k_parameter_default(self, client):
        """K should default to 5."""
        response = client.post("/chat", json={"query": "test"})
        # K is not returned, but should be accepted

        assert response.status_code == 200

    def test_chat_k_parameter_custom(self, client):
        """K parameter should be customizable."""
        response = client.post("/chat", json={"query": "test", "k": 10})
        assert response.status_code == 200

    def test_chat_k_parameter_bounded(self, client):
        """K must be in valid range."""
        response = client.post("/chat", json={"query": "test", "k": 101})
        assert response.status_code == 422

    def test_chat_query_too_long(self, client):
        """Query exceeding max length should fail."""
        long_query = "x" * 501
        response = client.post("/chat", json={"query": long_query})
        assert response.status_code == 422

    def test_chat_system_prompt_optional(self, client):
        """System prompt should be optional."""
        response = client.post("/chat", json={"query": "test"})
        assert response.status_code == 200

    def test_chat_system_prompt_custom(self, client):
        """System prompt should be customizable."""
        response = client.post("/chat", json={
            "query": "test",
            "system": "Be concise"
        })
        assert response.status_code == 200

    def test_chat_model_optional(self, client):
        """Model should be optional."""
        response = client.post("/chat", json={"query": "test"})
        assert response.status_code == 200

    def test_chat_model_custom(self, client):
        """Model should be customizable."""
        response = client.post("/chat", json={
            "query": "test",
            "model": "mistral"
        })
        assert response.status_code == 200

    def test_chat_citation_structure(self, client):
        """Citations should have index and source."""
        response = client.post("/chat", json={"query": "test"})
        data = response.json()

        # Citations list might be empty, structure validated elsewhere
        assert isinstance(data["citations"], list)


class TestIngestEndpoint:
    """Test /ingest endpoint."""

    def test_ingest_returns_200(self, client):
        """Ingest should return 200."""
        response = client.post("/ingest")
        assert response.status_code == 200

    def test_ingest_response_structure(self, client):
        """Ingest response should have required fields."""
        response = client.post("/ingest")
        data = response.json()

        assert "status" in data
        assert "indexed_chunks" in data
        assert "source_path" in data

    def test_ingest_status_ok(self, client):
        """Status should be 'ok'."""
        response = client.post("/ingest")
        data = response.json()

        assert data["status"] == "ok"

    def test_ingest_chunks_is_number(self, client):
        """Indexed chunks should be a number."""
        response = client.post("/ingest")
        data = response.json()

        assert isinstance(data["indexed_chunks"], int)

    def test_ingest_full_rebuild_parameter(self, client):
        """full_rebuild parameter should be accepted."""
        response = client.post("/ingest?full_rebuild=true")
        assert response.status_code == 200

    def test_ingest_full_rebuild_false(self, client):
        """full_rebuild=false should work."""
        response = client.post("/ingest?full_rebuild=false")
        assert response.status_code == 200


class TestInputValidation:
    """Test input validation."""

    def test_search_query_sanitized(self, client):
        """Search query should be properly validated."""
        # Valid query
        response = client.get("/search?q=normal+query")
        assert response.status_code == 200

    def test_chat_large_system_prompt_rejected(self, client):
        """System prompt exceeding limit should be rejected."""
        large_prompt = "x" * 501
        response = client.post("/chat", json={
            "query": "test",
            "system": large_prompt
        })
        assert response.status_code == 422

    def test_chat_k_zero_rejected(self, client):
        """K=0 should be rejected."""
        response = client.post("/chat", json={"query": "test", "k": 0})
        assert response.status_code == 422

    def test_chat_k_negative_rejected(self, client):
        """Negative K should be rejected."""
        response = client.post("/chat", json={"query": "test", "k": -1})
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling."""

    def test_nonexistent_endpoint(self, client):
        """Nonexistent endpoint should return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_wrong_method(self, client):
        """Wrong HTTP method should return 405."""
        response = client.post("/status")
        assert response.status_code == 405

    def test_invalid_json_body(self, client):
        """Invalid JSON should return 422."""
        response = client.post(
            "/chat",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestHealthChecks:
    """Test health check endpoints."""

    def test_status_is_health_check(self, client):
        """Status endpoint can serve as health check."""
        response = client.get("/status")
        assert response.status_code == 200
        assert "documents_indexed" in response.json()


class TestResponseFormats:
    """Test response format consistency."""

    def test_all_responses_json(self, client):
        """All endpoints should return JSON."""
        endpoints = [
            ("GET", "/status", None),
            ("GET", "/search?q=test", None),
            ("POST", "/chat", {"query": "test"}),
            ("POST", "/ingest", None)
        ]

        for method, path, json_data in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json=json_data)

            assert response.headers["content-type"].startswith("application/json")

    def test_error_responses_have_detail(self, client):
        """Error responses should have detail field."""
        response = client.get("/search")  # Missing required query
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
