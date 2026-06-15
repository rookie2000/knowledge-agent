"""
Integration tests for FastAPI routes.
Uses TestClient with mocked backend services.
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.rag import Document


@pytest.fixture
def mock_rag():
    mock = MagicMock()
    mock.get_document_count.return_value = 0
    mock.list_documents.return_value = []
    return mock


@pytest.fixture
def mock_agent():
    return MagicMock()


@pytest.fixture
def client(mock_rag, mock_agent):
    """Create TestClient with mocked dependencies."""
    with patch("src.api.rag_manager", mock_rag), \
         patch("src.api.agent", mock_agent):
        from src.api import app
        yield TestClient(app)


# --- Health ---

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "chroma_connected" in data
        assert "documents_count" in data


# --- Upload ---

class TestUpload:
    def test_upload_markdown(self, client, mock_rag):
        mock_rag.add_document.return_value = Document(
            doc_id="d1", filename="test.md", file_path="/tmp/test.md",
            file_type="markdown", chunks_count=3
        )

        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.md", b"# Title\n\nContent", "text/markdown")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == "d1"
        assert data["chunks_count"] == 3
        assert data["status"] == "indexed"

    def test_upload_unsupported_type(self, client):
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", b"content", "text/plain")}
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_no_filename(self, client):
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("", b"content", "text/plain")}
        )
        # FastAPI returns 422 for validation error on empty filename
        assert resp.status_code in (400, 422)

    def test_upload_processing_error(self, client, mock_rag):
        mock_rag.add_document.side_effect = RuntimeError("boom")

        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.md", b"# Hi", "text/markdown")}
        )
        assert resp.status_code == 500
        assert "boom" in resp.json()["detail"]


# --- List documents ---

class TestListDocuments:
    def test_empty_list(self, client, mock_rag):
        mock_rag.list_documents.return_value = []
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json()["documents"] == []

    def test_with_documents(self, client, mock_rag):
        mock_rag.list_documents.return_value = [
            Document(doc_id="d1", filename="a.md", file_path="/a.md",
                     file_type="markdown", chunks_count=5)
        ]
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["doc_id"] == "d1"


# --- Delete document ---

class TestDeleteDocument:
    def test_delete_success(self, client, mock_rag):
        mock_rag.delete_document.return_value = True
        resp = client.delete("/api/documents/d1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_not_found(self, client, mock_rag):
        mock_rag.delete_document.return_value = False
        resp = client.delete("/api/documents/missing")
        assert resp.status_code == 404


# --- Chat ---

class TestChat:
    def test_chat_success(self, client, mock_agent):
        mock_agent.chat.return_value = {
            "answer": "42",
            "sources": [{"filename": "a.md", "chunk_text": "..."}],
            "tool_calls": [{"tool": "search_knowledge"}],
            "conversation_id": "conv-1"
        }

        resp = client.post("/api/chat", json={"question": "what is the answer?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "42"
        assert len(data["sources"]) == 1

    def test_chat_empty_question(self, client):
        resp = client.post("/api/chat", json={"question": "  "})
        assert resp.status_code == 400

    def test_chat_with_conversation_id(self, client, mock_agent):
        mock_agent.chat.return_value = {
            "answer": "hi", "sources": [], "tool_calls": [],
            "conversation_id": "existing"
        }

        resp = client.post("/api/chat", json={
            "question": "hello", "conversation_id": "existing"
        })
        assert resp.status_code == 200
        mock_agent.chat.assert_called_with(
            question="hello", conversation_id="existing"
        )

    def test_chat_backend_error(self, client, mock_agent):
        mock_agent.chat.side_effect = RuntimeError("API down")

        resp = client.post("/api/chat", json={"question": "hi"})
        assert resp.status_code == 500


# --- Chat history ---

class TestChatHistory:
    def test_get_history(self, client, mock_agent):
        mock_agent.get_history.return_value = [
            {"role": "user", "content": "hi", "timestamp": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "hello", "timestamp": "2026-01-01T00:00:01"}
        ]

        resp = client.get("/api/chat/conv-1/history")
        assert resp.status_code == 200
        assert len(resp.json()["messages"]) == 2

    def test_empty_history(self, client, mock_agent):
        mock_agent.get_history.return_value = []
        resp = client.get("/api/chat/no-such/history")
        assert resp.status_code == 200
        assert resp.json()["messages"] == []
