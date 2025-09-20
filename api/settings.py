# api/settings.py
from __future__ import annotations
import json
import os
from pydantic_settings import BaseSettings

def _trim(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else v

def _parse_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default or []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except Exception:
            pass
    # comma separated
    return [x.strip() for x in raw.split(",") if x.strip()]

class Settings(BaseSettings):
    groq_api_key: str = _trim("GROQ_API_KEY")
    groq_model: str = _trim("GROQ_MODEL", "llama-3.1-70b-versatile")
    groq_temperature: float = float(_trim("GROQ_TEMPERATURE", "0.2") or 0.2)

    sendgrid_api_key: str = _trim("SENDGRID_API_KEY")
    email_sender: str = _trim("EMAIL_SENDER")

    chroma_dir: str = _trim("CHROMA_DIR", ".chroma")

    cors_allow_origins: list[str] = _parse_list("CORS_ALLOW_ORIGINS", ["*"])

    max_file_mb: int = int(_trim("MAX_FILE_MB", "10"))
    max_clauses: int = int(_trim("MAX_CLAUSES", "300"))

    sendgrid_api_key: str | None = None
    email_sender: str | None = None

    def __init__(self, **values):
        super().__init__(**values)
        # strip whitespace/newlines from secrets
        if self.sendgrid_api_key:
            self.sendgrid_api_key = self.sendgrid_api_key.strip()
        if self.email_sender:
            self.email_sender = self.email_sender.strip()

settings = Settings()
