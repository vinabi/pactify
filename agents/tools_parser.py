# agents/tools_parser.py
from __future__ import annotations
import io
import os
import re
from typing import List, Tuple

def _clean(txt: str) -> str:
    if not txt:
        return ""
    # collapse binary leftovers and whitespace
    txt = txt.replace("\x00", " ")
    txt = re.sub(r"[ \t\u00A0]+", " ", txt)
    txt = re.sub(r"\r\n|\r|\n", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def read_any(raw: bytes, filename: str) -> str:
    """Return best-effort plain text from PDF/DOCX/TXT bytes."""
    name = (filename or "").lower()

    # ---- TXT ----
    if name.endswith(".txt"):
        try:
            return _clean(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return _clean(raw.decode("latin1", errors="ignore"))

    # ---- DOCX ----
    if name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            parts = []
            for p in doc.paragraphs:
                parts.append(p.text)
            # tables
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            return _clean("\n".join(parts))
        except Exception:
            pass  # fall through to raw

    # ---- PDF ----
    if name.endswith(".pdf"):
        # try pymupdf (fitz)
        try:
            import fitz  # pymupdf
            doc = fitz.open(stream=raw, filetype="pdf")
            parts = []
            for page in doc:
                parts.append(page.get_text("text"))
            txt = "\n".join(parts)
            if txt and "%PDF" not in txt[:20]:
                return _clean(txt)
        except Exception:
            pass
        # try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                parts = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    parts.append(t)
            txt = "\n".join(parts)
            if txt and "%PDF" not in txt[:20]:
                return _clean(txt)
        except Exception:
            pass
        # try pypdf
        try:
            from pypdf import PdfReader
            rd = PdfReader(io.BytesIO(raw))
            parts = []
            for pg in rd.pages:
                parts.append(pg.extract_text() or "")
            txt = "\n".join(parts)
            if txt and "%PDF" not in txt[:20]:
                return _clean(txt)
        except Exception:
            pass
        # last resort: say empty so pipeline can throw a clear error
        return ""

    # default: try to decode as text
    try:
        return _clean(raw.decode("utf-8"))
    except Exception:
        return _clean(raw.decode("latin1", errors="ignore"))


# very light clause splitter (keep your original if you prefer)
_HEADING = re.compile(r"^(?:\d+(?:\.\d+){0,3}\s*[-.:)]\s*)?[A-Z][A-Z \-/]{3,}$|^SECTION\s+\d+\b.*$", re.MULTILINE)

def rough_clauses(text: str) -> List[Tuple[str, str]]:
    """
    Return [(heading, body)] using uppercase/numbered headings or fall back to chunks.
    """
    text = text or ""
    if not text.strip():
        return [("Document", "")]

    parts = []
    last_idx = 0
    last_head = "Preamble"
    for m in _HEADING.finditer(text):
        head = m.group().strip()
        body = text[last_idx:m.start()].strip()
        if body:
            parts.append((last_head, body))
        last_head = head
        last_idx = m.end()
    tail = text[last_idx:].strip()
    if tail:
        parts.append((last_head, tail))

    if parts:
        return parts

    # fallback: fixed-size chunks
    CH = 1200
    chunks = [text[i:i+CH] for i in range(0, len(text), CH)]
    return [(f"Chunk {i+1}", c) for i, c in enumerate(chunks)]
