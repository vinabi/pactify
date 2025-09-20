# api/settings.py
from __future__ import annotations
import os, json
from pydantic_settings import BaseSettings

def _trim_env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip().strip('"').strip("'") if isinstance(v, str) else v

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
    return [x.strip() for x in raw.split(",") if x.strip()]

class Settings(BaseSettings):
    groq_api_key: str = _trim_env("GROQ_API_KEY")
    groq_model: str = _trim_env("GROQ_MODEL", "llama-3.1-70b-versatile")
    groq_temperature: float = float(_trim_env("GROQ_TEMPERATURE", "0.2") or 0.2)

    sendgrid_api_key: str | None = _trim_env("SENDGRID_API_KEY") or None
    email_sender: str | None = _trim_env("EMAIL_SENDER") or None

    chroma_dir: str = _trim_env("CHROMA_DIR", ".chroma")
    cors_allow_origins: list[str] = _parse_list("CORS_ALLOW_ORIGINS", ["*"])

    max_file_mb: int = int(_trim_env("MAX_FILE_MB", "10"))
    max_clauses: int = int(_trim_env("MAX_CLAUSES", "300"))

settings = Settings()
