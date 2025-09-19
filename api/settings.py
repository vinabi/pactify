from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # Groq (primary)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_temperature: float = Field(default=0.2, alias="GROQ_TEMPERATURE")

    # Optional OpenAI fallback
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")

    # App
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"], alias="CORS_ALLOW_ORIGINS")
    max_file_mb: int = Field(default=10, alias="MAX_FILE_MB")
    max_clauses: int = Field(default=300, alias="MAX_CLAUSES")

    # Chroma
    chroma_dir: str = Field(default=".chroma", alias="CHROMA_DIR")

    # SendGrid
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")
    email_sender: str = Field(default="", alias="EMAIL_SENDER")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
