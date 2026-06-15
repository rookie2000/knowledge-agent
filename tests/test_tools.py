"""
Tests for ToolExecutor and tool definitions.
"""

import pytest
from unittest.mock import MagicMock

from src.tools import ToolExecutor, ToolResult, TOOLS
from src.rag import Chunk, Document


@pytest.fixture
def mock_rag():
    """Mock RAGManager."""
    return MagicMock()


@pytest.fixture
def executor(mock_rag):
    """Create ToolExecutor with mocked RAG."""
    return ToolExecutor(mock_rag)


# --- Tool definitions ---

class TestToolDefinitions:
    def test_tools_is_list(self):
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 2

    def test_search_tool_schema(self):
        tool = next(t for t in TOOLS if t["name"] == "search_knowledge")
        assert "input_schema" in tool
        assert "query" in tool["input_schema"]["properties"]
        assert "query" in tool["input_schema"]["required"]

    def test_get_document_info_schema(self):
        tool = next(t for t in TOOLS if t["name"] == "get_document_info")
        assert "doc_id" in tool["input_schema"]["required"]


# --- ToolExecutor.execute ---

class TestExecute:
    def test_unknown_tool(self, executor):
        result = executor.execute("nonexistent_tool", {})
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_search_knowledge(self, executor, mock_rag):
        mock_rag.search.return_value = [
            Chunk(chunk_id="c1", doc_id="d1", content="hello",
                  chunk_index=0, relevance_score=0.9)
        ]
        mock_rag.get_document_info.return_value = Document(
            doc_id="d1", filename="test.md", file_path="/test.md",
            file_type="markdown", chunks_count=1
        )

        result = executor.execute("search_knowledge", {"query": "hello"})
        assert result.success is True
        assert result.data["total_results"] == 1
        assert result.data["results"][0]["filename"] == "test.md"

    def test_search_knowledge_missing_query(self, executor):
        result = executor.execute("search_knowledge", {})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_get_document_info_found(self, executor, mock_rag):
        mock_rag.get_document_info.return_value = Document(
            doc_id="d1", filename="test.md", file_path="/test.md",
            file_type="markdown", chunks_count=5
        )

        result = executor.execute("get_document_info", {"doc_id": "d1"})
        assert result.success is True
        assert result.data["chunks_count"] == 5

    def test_get_document_info_not_found(self, executor, mock_rag):
        mock_rag.get_document_info.return_value = None

        result = executor.execute("get_document_info", {"doc_id": "missing"})
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_get_document_info_missing_id(self, executor):
        result = executor.execute("get_document_info", {})
        assert result.success is False
