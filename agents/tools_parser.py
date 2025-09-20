# agents/tools_parser.py
from __future__ import annotations
import io, re
from typing import List, Tuple

def _read_pdf(raw: bytes) -> str:
    # Try pypdf first
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        parts = []
        for pg in rd.pages:
            parts.append(pg.extract_text() or "")
        txt = "\n".join(parts).strip()
        if len(txt) >= 200:
            return txt
    except Exception:
        pass
    # Fallback pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            parts = []
            for pg in pdf.pages:
                parts.append(pg.extract_text() or "")
        txt = "\n".join(parts).strip()
        if len(txt) >= 200:
            return txt
    except Exception:
        pass
    raise ValueError("PDF contains little/no extractable text (likely scanned).")

def _read_docx(raw: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        raise ValueError(f"DOCX parse failed: {e}")

def _read_txt(raw: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")

def read_any(raw: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _read_pdf(raw)
    if name.endswith(".docx"):
        return _read_docx(raw)
    if name.endswith(".txt"):
        return _read_txt(raw)
    raise ValueError(f"Unsupported file type for {filename}")

# very light clause splitter
_HEADING = re.compile(r"^\s*(?:section|clause|article|\d+(\.\d+)*|\([a-z]\)|[A-Z][\w\- ]{3,})[:\-–]?\s*$", re.I)

def rough_clauses(text: str) -> List[Tuple[str, str]]:
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    out: List[Tuple[str,str]] = []
    head, buf = "Preamble", []
    for ln in lines:
        if _HEADING.match(ln.strip()):
            if buf:
                out.append((head, "\n".join(buf).strip()))
                buf = []
            head = ln.strip().strip(":").strip()
        else:
            buf.append(ln)
    if buf:
        out.append((head, "\n".join(buf).strip()))
    if not out:
        clean = " ".join(lines)
        sz = 1200
        chunks = [clean[i:i+sz] for i in range(0, len(clean), sz)]
        out = [(f"Chunk {i+1}", c) for i, c in enumerate(chunks)]
    return out
