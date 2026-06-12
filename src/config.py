"""
Configuration management for Knowledge Agent.
Reads from .env file and provides type-safe access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Application configuration."""

    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    # Model configuration
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

    # ChromaDB configuration
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "knowledge_base")

    # Document processing
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # API server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Agent constraints
    MAX_TOOL_CALLS: int = 5
    TOOL_TIMEOUT: int = 30  # seconds
    MAX_CONVERSATION_HISTORY: int = 10  # rounds

    # Supported file types
    SUPPORTED_FILE_TYPES: list[str] = [".pdf", ".md", ".markdown"]

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")

        # Ensure ChromaDB directory exists
        Path(cls.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)


# Singleton instance
config = Config()
