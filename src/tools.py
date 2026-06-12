"""
Tool definitions and execution for Knowledge Agent.
Follows Claude Tool Use specification.
"""

from dataclasses import dataclass
from typing import Any

from .rag import RAGManager


@dataclass
class ToolResult:
    """Tool execution result."""
    success: bool
    data: Any = None
    error: str | None = None


# Tool definitions - Claude Tool Use format
TOOLS = [
    {
        "name": "search_knowledge",
        "description": "搜索知识库中的相关文档片段。当用户问题涉及文档内容时使用此工具。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_document_info",
        "description": "获取指定文档的详细信息。当用户询问文档元信息时使用此工具。",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "文档ID"
                }
            },
            "required": ["doc_id"]
        }
    }
]


class ToolExecutor:
    """Executes tools based on tool calls from Claude."""

    def __init__(self, rag_manager: RAGManager):
        self.rag = rag_manager

    def execute(self, tool_name: str, tool_input: dict) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            ToolResult with success status and data/error
        """
        try:
            if tool_name == "search_knowledge":
                return self._search_knowledge(tool_input)
            elif tool_name == "get_document_info":
                return self._get_document_info(tool_input)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    def _search_knowledge(self, tool_input: dict) -> ToolResult:
        """
        Search knowledge base for relevant chunks.

        Args:
            tool_input: {"query": str, "top_k": int (optional)}

        Returns:
            ToolResult with search results
        """
        query = tool_input.get("query")
        if not query:
            return ToolResult(success=False, error="Query is required")

        top_k = tool_input.get("top_k", 5)

        # Execute search
        chunks = self.rag.search(query, top_k=top_k)

        # Format results
        results = []
        for chunk in chunks:
            doc = self.rag.get_document_info(chunk.doc_id)
            results.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "filename": doc.filename if doc else "unknown",
                "content": chunk.content,
                "relevance_score": round(chunk.relevance_score, 2),
                "metadata": chunk.metadata
            })

        return ToolResult(
            success=True,
            data={
                "results": results,
                "total_results": len(results)
            }
        )

    def _get_document_info(self, tool_input: dict) -> ToolResult:
        """
        Get document metadata.

        Args:
            tool_input: {"doc_id": str}

        Returns:
            ToolResult with document info
        """
        doc_id = tool_input.get("doc_id")
        if not doc_id:
            return ToolResult(success=False, error="doc_id is required")

        doc = self.rag.get_document_info(doc_id)
        if not doc:
            return ToolResult(
                success=False,
                error=f"Document not found: {doc_id}"
            )

        return ToolResult(
            success=True,
            data={
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "chunks_count": doc.chunks_count,
                "created_at": doc.created_at.isoformat(),
                "metadata": doc.metadata
            }
        )
