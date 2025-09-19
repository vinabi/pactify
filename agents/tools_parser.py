from typing import List, Tuple
import pdfplumber
from pypdf import PdfReader
from docx import Document
import re

SUPPORTED = (".pdf", ".docx", ".txt")

def _read_pdf(raw: bytes) -> str:
    # Try pdfplumber (more robust text extraction)
    try:
        import io
        text = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text).strip()
    except Exception:
        # Fallback to pypdf
        import io
        reader = PdfReader(io.BytesIO(raw))
        buf = []
        for page in reader.pages:
            buf.append(page.extract_text() or "")
        return "\n".join(buf).strip()

def _read_docx(raw: bytes) -> str:
    import io
    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs)

def _read_txt(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("latin-1", errors="ignore")

def read_any(raw: bytes, filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".pdf"):
        txt = _read_pdf(raw)
        if not txt.strip():
            raise ValueError("Empty/unencrypted PDF or text not extractable")
        return txt
    if fn.endswith(".docx"):
        txt = _read_docx(raw)
        if not txt.strip():
            raise ValueError("DOCX had no readable text")
        return txt
    if fn.endswith(".txt"):
        txt = _read_txt(raw)
        if not txt.strip():
            raise ValueError("TXT is empty")
        return txt
    raise ValueError("Unsupported file type. Use PDF/DOCX/TXT.")

def rough_clauses(text: str) -> List[Tuple[str, str]]:
    """Return list of (heading, clause_text). Uses simple heading heuristics then length-based chunking."""
    # Split by common headings (very rough); fallback to size chunks
    lines = [l.strip() for l in text.splitlines()]
    blocks = []
    current_heading = "Preamble"
    current = []
    heading_re = re.compile(r"^(section\s+\d+|\d+\.\d+|[A-Z][A-Z\s\-]{3,}|[A-Z][A-Za-z\s]{3,}\:)$", re.I)

    for ln in lines:
        if heading_re.match(ln.strip()):
            if current:
                blocks.append((current_heading, " ".join(current).strip()))
                current = []
            current_heading = ln.strip().rstrip(":")
        else:
            if ln:
                current.append(ln)
    if current:
        blocks.append((current_heading, " ".join(current).strip()))

    # If too few blocks, chunk by size ~900 chars
    if len(blocks) < 5:
        text_clean = " ".join(lines)
        chunk_sz = 900
        chunks = [text_clean[i:i+chunk_sz] for i in range(0, len(text_clean), chunk_sz)]
        blocks = [(f"Chunk {i+1}", c) for i, c in enumerate(chunks)]

    return [(h if h else "Clause", t) for h, t in blocks if t]
