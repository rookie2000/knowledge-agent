"""
RAG (Retrieval-Augmented Generation) module.
Handles document processing, chunking, and semantic search.
"""

import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

import chromadb
from PyPDF2 import PdfReader

from .config import config


@dataclass
class Document:
    """Document metadata."""
    doc_id: str
    filename: str
    file_path: str
    file_type: str  # "pdf" | "markdown"
    chunks_count: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    """Document chunk with content and metadata."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    relevance_score: float = 0.0


class RAGManager:
    """Manages document indexing and semantic search."""

    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self.client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        # In-memory document metadata store
        self._documents: dict[str, Document] = {}

    def add_document(self, file_path: str, chunk_size: int | None = None) -> Document:
        """
        Process document and create vector index.

        Args:
            file_path: Path to the document file
            chunk_size: Optional chunk size override

        Returns:
            Document metadata

        Raises:
            UnsupportedFileTypeError: If file type is not supported
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = self._get_file_type(path)
        if file_type not in ["pdf", "markdown"]:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        # Extract text based on file type
        if file_type == "pdf":
            pages = self._extract_pdf(path)
        else:
            pages = self._extract_markdown(path)

        # Chunk the text
        chunks = self._chunk_text(pages, chunk_size or config.CHUNK_SIZE)

        # Generate document ID
        doc_id = str(uuid.uuid4())

        # Store chunks in ChromaDB
        chunk_ids = []
        documents = []
        metadatas = []

        for i, chunk_content in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            documents.append(chunk_content["content"])
            metadatas.append({
                "doc_id": doc_id,
                "chunk_index": i,
                **chunk_content.get("metadata", {})
            })

        # Batch insert into ChromaDB
        if chunk_ids:
            self.collection.add(
                ids=chunk_ids,
                documents=documents,
                metadatas=metadatas
            )

        # Create document metadata
        doc = Document(
            doc_id=doc_id,
            filename=path.name,
            file_path=str(path.absolute()),
            file_type=file_type,
            chunks_count=len(chunks),
            metadata={"original_path": file_path}
        )

        self._documents[doc_id] = doc
        return doc

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """
        Semantic search for relevant chunks.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of relevant chunks
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count() or 1)
        )

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                # Convert distance to relevance score (cosine distance -> similarity)
                relevance_score = 1 - distance

                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=metadata.get("doc_id", ""),
                    content=results["documents"][0][i],
                    chunk_index=metadata.get("chunk_index", 0),
                    metadata=metadata,
                    relevance_score=relevance_score
                )
                chunks.append(chunk)

        return chunks

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document and all its chunks.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted successfully
        """
        if doc_id not in self._documents:
            return False

        # Find all chunks for this document
        results = self.collection.get(
            where={"doc_id": doc_id}
        )

        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])

        del self._documents[doc_id]
        return True

    def get_document_info(self, doc_id: str) -> Document | None:
        """
        Get document metadata.

        Args:
            doc_id: Document ID

        Returns:
            Document metadata or None if not found
        """
        return self._documents.get(doc_id)

    def list_documents(self) -> list[Document]:
        """List all documents."""
        return list(self._documents.values())

    def get_document_count(self) -> int:
        """Get total number of documents."""
        return len(self._documents)

    def _get_file_type(self, path: Path) -> str:
        """Determine file type from extension."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return "pdf"
        elif suffix in [".md", ".markdown"]:
            return "markdown"
        return "unknown"

    def _extract_pdf(self, path: Path) -> list[dict]:
        """
        Extract text from PDF, preserving page information.

        Returns:
            List of {"content": str, "metadata": {"page": int}}
        """
        pages = []
        reader = PdfReader(str(path))

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                pages.append({
                    "content": text.strip(),
                    "metadata": {"page": i + 1}
                })

        return pages

    def _extract_markdown(self, path: Path) -> list[dict]:
        """
        Extract text from Markdown, preserving section information.

        Returns:
            List of {"content": str, "metadata": {"section": str}}
        """
        content = path.read_text(encoding="utf-8")
        sections = []
        current_section = "Introduction"
        current_content = []

        for line in content.split("\n"):
            # Detect markdown headers
            if line.startswith("#"):
                # Save previous section
                if current_content:
                    sections.append({
                        "content": "\n".join(current_content).strip(),
                        "metadata": {"section": current_section}
                    })
                    current_content = []

                current_section = line.lstrip("#").strip()
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections.append({
                "content": "\n".join(current_content).strip(),
                "metadata": {"section": current_section}
            })

        return sections

    def _chunk_text(self, pages: list[dict], chunk_size: int) -> list[dict]:
        """
        Chunk text with overlap.

        Args:
            pages: List of page/section content
            chunk_size: Target chunk size in characters

        Returns:
            List of chunks with metadata
        """
        chunks = []
        overlap = config.CHUNK_OVERLAP

        for page in pages:
            text = page["content"]
            metadata = page.get("metadata", {})

            # If text is short enough, keep as single chunk
            if len(text) <= chunk_size:
                chunks.append({
                    "content": text,
                    "metadata": metadata
                })
                continue

            # Split by paragraphs first
            paragraphs = text.split("\n\n")
            current_chunk = []

            for para in paragraphs:
                # If adding this paragraph exceeds chunk size, save current chunk
                if current_chunk and len("\n\n".join(current_chunk)) + len(para) > chunk_size:
                    chunk_content = "\n\n".join(current_chunk)
                    chunks.append({
                        "content": chunk_content,
                        "metadata": metadata
                    })

                    # Keep overlap from end of current chunk
                    overlap_text = chunk_content[-overlap:] if overlap else ""
                    current_chunk = [overlap_text] if overlap_text else []

                current_chunk.append(para)

            # Save remaining chunk
            if current_chunk:
                chunks.append({
                    "content": "\n\n".join(current_chunk),
                    "metadata": metadata
                })

        return chunks
