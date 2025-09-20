# agents/tools_parser.py
from __future__ import annotations
import io
import re
from typing import List, Tuple

# Light dependencies only; all available in your env
from docx import Document as DocxDocument
from pypdf import PdfReader

def _read_txt(raw: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")

def _read_docx(raw: bytes) -> str:
    fp = io.BytesIO(raw)
    doc = DocxDocument(fp)
    return "\n".join(p.text for p in doc.paragraphs)

def _read_pdf(raw: bytes) -> str:
    # Try PyPDF first (works on many text-based PDFs)
    try:
        reader = PdfReader(io.BytesIO(raw))
        texts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            texts.append(txt)
        out = "\n".join(texts).strip()
        if out:
            return out
    except Exception:
        pass
    # Last-ditch: if it still looks like binary, fall back to a safe placeholder
    # (so UI won’t display raw %PDF bytes as “Original”)
    return "[Unable to extract text from PDF. Please upload a text-based PDF or DOCX/TXT.]"

def read_any(raw: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return _read_txt(raw)
    if name.endswith(".docx"):
        return _read_docx(raw)
    if name.endswith(".pdf"):
        return _read_pdf(raw)
    # default
    return _read_txt(raw)

CLAUSE_SPLIT = re.compile(r"\n{2,}|^\s*\d+(\.\d+)*\s+[A-Z].{2,}$", re.M)

def rough_clauses(text: str) -> List[Tuple[str, str]]:
    """Very rough chunker: (heading, body)."""
    parts = [p.strip() for p in CLAUSE_SPLIT.split(text) if p.strip()]
    out = []
    for i, chunk in enumerate(parts, 1):
        # Heading guess: first line up to 120 chars
        first_line = chunk.splitlines()[0][:120]
        heading = re.sub(r"[^A-Za-z0-9 \-/&]", " ", first_line).strip() or f"Chunk {i}"
        out.append((heading, chunk))
    return out
