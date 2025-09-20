# agents/tools_parser.py
from __future__ import annotations
from typing import List, Tuple
import io
import os

from loguru import logger

# Light deps only:
#   PyPDF2 for PDFs
#   python-docx for DOCX
# If they’re missing, the code degrades gracefully.

def _read_pdf(data: bytes) -> str:
    try:
        import PyPDF2
        txt_parts: List[str] = []
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        for page in reader.pages:
            txt_parts.append(page.extract_text() or "")
        text = "\n".join(txt_parts).strip()
        if text:
            return text
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")
    return ""  # caller will handle empty

def _read_docx(data: bytes) -> str:
    try:
        import docx  # python-docx
        bio = io.BytesIO(data)
        doc = docx.Document(bio)
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        logger.warning(f"python-docx failed: {e}")
    return ""

def read_any(raw: bytes, filename: str) -> str:
    """
    Return clean UTF-8 text for PDF/DOCX/TXT.
    Never return raw binary; if parsing fails, raise a helpful error.
    """
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        text = _read_pdf(raw)
        if not text:
            raise ValueError("Failed to extract text from PDF. Is it scanned or image-only?")
        return text

    if name.endswith(".docx"):
        text = _read_docx(raw)
        if not text:
            raise ValueError("Failed to extract text from DOCX")
        return text

    if name.endswith(".txt"):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")

    raise ValueError(f"Unsupported file type for {filename}")

# very rough chunker; keep small to avoid token blowups
def rough_clauses(text: str, max_chars: int = 1600) -> List[Tuple[str, str]]:
    """
    Split text into heading+body chunks. We look for common clause keywords;
    otherwise we chunk by length.
    """
    import re

    lines = text.splitlines()
    blocks: List[Tuple[str, str]] = []
    cur_head = "Chunk"
    cur_buf: List[str] = []
    i = 0

    heading_re = re.compile(r"^\s*(\d+(\.\d+)*\s+)?([A-Z][A-Za-z \-/]{3,40}):?\s*$")

    for ln in lines:
        if heading_re.match(ln) and cur_buf:
            blocks.append((cur_head, "\n".join(cur_buf).strip()))
            cur_buf = []
            i += 1
            cur_head = heading_re.match(ln).group(0).strip(": ").strip()
        else:
            cur_buf.append(ln)
            if sum(len(x) for x in cur_buf) > max_chars:
                blocks.append((cur_head, "\n".join(cur_buf).strip()))
                cur_buf = []
                i += 1
                cur_head = f"Chunk {i}"

    if cur_buf:
        blocks.append((cur_head, "\n".join(cur_buf).strip()))
    return blocks
