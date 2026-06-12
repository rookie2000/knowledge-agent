"""
Knowledge Agent - Entry point.
"""

import uvicorn

from src.config import config


def main():
    """Start the Knowledge Agent API server."""
    # Validate configuration
    config.validate()

    print(f"Starting Knowledge Agent API on {config.API_HOST}:{config.API_PORT}")
    print(f"ChromaDB storage: {config.CHROMA_PERSIST_DIR}")
    print(f"Model: {config.CLAUDE_MODEL}")

    # Run server
    uvicorn.run(
        "src.api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )


if __name__ == "__main__":
    main()
