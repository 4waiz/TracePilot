"""
TracePilot configuration using pydantic-settings.
All settings can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with sensible defaults for local development."""

    # Database
    DATABASE_URL: str = "sqlite:///./tracepilot.db"

    # ChromaDB vector store directory
    CHROMA_DIR: str = "./chroma_data"

    # File upload directory
    UPLOAD_DIR: str = "./uploads"

    # Ollama LLM settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # JWT authentication
    SECRET_KEY: str = "tracepilot-dev-secret-change-in-production"
    TOKEN_EXPIRE_MINUTES: int = 480

    # CORS -- comma-separated origins, or "*" for permissive dev mode
    CORS_ORIGINS: str = "*"

    # Upload / request size limits (megabytes)
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_REQUEST_SIZE_MB: int = 60

    # Rate limiting -- max login attempts per IP within the window
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW_SECONDS: int = 300

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
