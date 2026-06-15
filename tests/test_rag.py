"""
Tests for RAG module.
Covers: text extraction, chunking, search, document CRUD.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.rag import RAGManager, Document, Chunk


@pytest.fixture
def mock_chroma():
    """Mock ChromaDB client and collection."""
    with patch("src.rag.chromadb") as mock_chromadb:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        yield mock_client, mock_collection


@pytest.fixture
def rag_manager(mock_chroma):
    """Create RAGManager with mocked ChromaDB."""
    return RAGManager()


@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file."""
    content = """# Introduction

This is the introduction section.
It has some content for testing.

# Methods

This section describes the methods used.
We use RAG for retrieval.

# Results

The results are promising.
Performance improved by 50%.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def large_markdown(tmp_path):
    """Create a markdown file that requires chunking."""
    # Each section is > 200 chars to trigger chunking
    sections = []
    for i in range(5):
        sections.append(f"# Section {i}\n\n" + "word " * 80)
    content = "\n\n".join(sections)
    file_path = tmp_path / "large.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


# --- File type detection ---

class TestGetFileType:
    def test_pdf(self, rag_manager):
        assert rag_manager._get_file_type(Path("doc.pdf")) == "pdf"

    def test_markdown(self, rag_manager):
        assert rag_manager._get_file_type(Path("doc.md")) == "markdown"
        assert rag_manager._get_file_type(Path("doc.markdown")) == "markdown"

    def test_unknown(self, rag_manager):
        assert rag_manager._get_file_type(Path("doc.txt")) == "unknown"


# --- Markdown extraction ---

class TestExtractMarkdown:
    def test_extracts_sections(self, rag_manager, sample_markdown):
        sections = rag_manager._extract_markdown(sample_markdown)
        assert len(sections) == 3
        assert sections[0]["metadata"]["section"] == "Introduction"
        assert sections[1]["metadata"]["section"] == "Methods"
        assert sections[2]["metadata"]["section"] == "Results"

    def test_section_content_is_trimmed(self, rag_manager, sample_markdown):
        sections = rag_manager._extract_markdown(sample_markdown)
        for section in sections:
            assert section["content"] == section["content"].strip()


# --- Chunking ---

class TestChunkText:
    def test_short_text_single_chunk(self, rag_manager):
        pages = [{"content": "Short text", "metadata": {"page": 1}}]
        chunks = rag_manager._chunk_text(pages, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Short text"
        assert chunks[0]["metadata"] == {"page": 1}

    def test_long_text_multiple_chunks(self, rag_manager):
        # Create text longer than chunk_size
        long_text = "\n\n".join([f"Paragraph {i}. " * 50 for i in range(10)])
        pages = [{"content": long_text, "metadata": {}}]
        chunks = rag_manager._chunk_text(pages, chunk_size=200)
        assert len(chunks) > 1

    def test_metadata_preserved(self, rag_manager):
        pages = [{"content": "content", "metadata": {"section": "test"}}]
        chunks = rag_manager._chunk_text(pages, chunk_size=1000)
        assert chunks[0]["metadata"]["section"] == "test"


# --- Document CRUD ---

class TestAddDocument:
    def test_add_markdown(self, rag_manager, sample_markdown, mock_chroma):
        _, mock_collection = mock_chroma
        doc = rag_manager.add_document(str(sample_markdown))

        assert isinstance(doc, Document)
        assert doc.filename == "test.md"
        assert doc.file_type == "markdown"
        assert doc.chunks_count > 0
        mock_collection.add.assert_called_once()

    def test_file_not_found(self, rag_manager):
        with pytest.raises(FileNotFoundError):
            rag_manager.add_document("/nonexistent/file.md")

    def test_unsupported_type(self, rag_manager, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        with pytest.raises(ValueError, match="Unsupported"):
            rag_manager.add_document(str(txt_file))


class TestDeleteDocument:
    def test_delete_existing(self, rag_manager, sample_markdown, mock_chroma):
        _, mock_collection = mock_chroma
        mock_collection.get.return_value = {"ids": ["chunk_0", "chunk_1"]}

        doc = rag_manager.add_document(str(sample_markdown))
        result = rag_manager.delete_document(doc.doc_id)

        assert result is True
        mock_collection.delete.assert_called_once()

    def test_delete_nonexistent(self, rag_manager):
        result = rag_manager.delete_document("nonexistent-id")
        assert result is False


class TestSearch:
    def test_returns_chunks(self, rag_manager, mock_chroma):
        _, mock_collection = mock_chroma
        mock_collection.count.return_value = 10
        mock_collection.query.return_value = {
            "ids": [["chunk_0", "chunk_1"]],
            "documents": [["content 1", "content 2"]],
            "metadatas": [[{"doc_id": "d1", "chunk_index": 0},
                           {"doc_id": "d1", "chunk_index": 1}]],
            "distances": [[0.1, 0.3]]
        }

        results = rag_manager.search("test query", top_k=2)
        assert len(results) == 2
        assert all(isinstance(c, Chunk) for c in results)
        assert results[0].relevance_score > results[1].relevance_score

    def test_empty_results(self, rag_manager, mock_chroma):
        _, mock_collection = mock_chroma
        mock_collection.count.return_value = 0
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        results = rag_manager.search("nothing")
        assert results == []


class TestListDocuments:
    def test_empty_at_start(self, rag_manager):
        assert rag_manager.list_documents() == []
        assert rag_manager.get_document_count() == 0

    def test_after_add(self, rag_manager, sample_markdown, mock_chroma):
        rag_manager.add_document(str(sample_markdown))
        assert rag_manager.get_document_count() == 1
        docs = rag_manager.list_documents()
        assert len(docs) == 1
