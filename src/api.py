"""
FastAPI routes for Knowledge Agent API.
"""

import json
from pathlib import Path
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import config
from .rag import RAGManager
from .agent import KnowledgeAgent


# Request/Response models
class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    tool_calls: list[dict]
    conversation_id: str


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_count: int
    status: str


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunks_count: int
    created_at: str


class HealthResponse(BaseModel):
    status: str
    chroma_connected: bool
    documents_count: int


# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Agent API",
    description="个人知识库问答 Agent",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
rag_manager = RAGManager()
agent = KnowledgeAgent(rag_manager)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        chroma_connected=True,
        documents_count=rag_manager.get_document_count()
    )


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Query(default=config.CHUNK_SIZE, ge=100, le=5000)
):
    """
    Upload and index a document.

    Supports PDF and Markdown files.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in config.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {config.SUPPORTED_FILE_TYPES}"
        )

    # Save uploaded file temporarily
    upload_dir = Path("./data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    try:
        # Write file
        content = await file.read()
        file_path.write_bytes(content)

        # Process document
        doc = rag_manager.add_document(str(file_path), chunk_size)

        return DocumentUploadResponse(
            doc_id=doc.doc_id,
            filename=doc.filename,
            chunks_count=doc.chunks_count,
            status="indexed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()


@app.get("/api/documents")
async def list_documents():
    """List all indexed documents."""
    documents = rag_manager.list_documents()
    return {
        "documents": [
            {
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "chunks_count": doc.chunks_count,
                "created_at": doc.created_at.isoformat()
            }
            for doc in documents
        ]
    }


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document by ID."""
    success = rag_manager.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the Knowledge Agent.

    The agent will search the knowledge base and provide answers with sources.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = agent.chat(
            question=request.question,
            conversation_id=request.conversation_id
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with streaming response (SSE).

    Event types:
    - text: partial answer text
    - tool_start: agent is calling a tool
    - done: final metadata (sources, tool_calls, conversation_id)
    - error: something went wrong
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    def event_generator():
        for event in agent.chat_stream(
            question=request.question,
            conversation_id=request.conversation_id
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/api/chat/{conversation_id}/history")
async def get_chat_history(conversation_id: str):
    """Get conversation history."""
    history = agent.get_history(conversation_id)
    return {"messages": history}
