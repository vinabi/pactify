# agents/tools_parser.py
from __future__ import annotations
import io, re
from typing import List, Tuple
from loguru import logger

def _read_pdf(raw: bytes) -> str:
    """Enhanced PDF reading with multiple extraction strategies"""
    
    def clean_text(text: str) -> str:
        """Clean extracted PDF text"""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Fix common PDF extraction issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add spaces between joined words
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)  # Space between numbers and letters
        text = text.replace('•', '-').replace('◦', '-')  # Normalize bullet points
        return text.strip()
    
    extraction_methods = []
    
    # Method 1: pypdf with enhanced extraction
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        parts = []
        for pg in rd.pages:
            # Try multiple extraction strategies
            text = pg.extract_text() or ""
            if not text and hasattr(pg, 'extract_text'):
                # Alternative extraction for difficult PDFs
                try:
                    text = pg.extract_text(extraction_mode="layout") or ""
                except:
                    pass
            parts.append(clean_text(text))
        
        txt = "\n".join(parts).strip()
        if len(txt) >= 150:  # Lowered threshold
            extraction_methods.append(("pypdf", txt, len(txt)))
    except Exception:
        pass
    
    # Method 2: pdfplumber with table extraction
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            parts = []
            for pg in pdf.pages:
                text = ""
                # Extract regular text
                page_text = pg.extract_text() or ""
                if page_text:
                    text += clean_text(page_text) + "\n"
                
                # Extract tables if present
                tables = pg.extract_tables()
                for table in tables:
                    for row in table:
                        if row and any(cell for cell in row if cell):
                            text += " | ".join(str(cell or "") for cell in row) + "\n"
                
                parts.append(text.strip())
        
        txt = "\n".join(parts).strip()
        if len(txt) >= 150:
            extraction_methods.append(("pdfplumber", txt, len(txt)))
    except Exception:
        pass
    
    # Method 3: PyMuPDF (fallback for complex layouts)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=raw, filetype="pdf")
        parts = []
        for page in doc:
            text = page.get_text()
            parts.append(clean_text(text))
        doc.close()
        
        txt = "\n".join(parts).strip()
        if len(txt) >= 150:
            extraction_methods.append(("pymupdf", txt, len(txt)))
    except Exception:
        pass
    
    # Choose the best extraction (longest text)
    if extraction_methods:
        best_method = max(extraction_methods, key=lambda x: x[2])
        logger.info(f"PDF extracted using {best_method[0]}: {best_method[2]} characters")
        return best_method[1]
    
    # Last resort: check if it's an image-based PDF
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        page_count = len(rd.pages)
        if page_count > 0:
            # Check if pages have images (might be scanned)
            sample_page = rd.pages[0]
            if '/XObject' in sample_page.get('/Resources', {}):
                raise ValueError(f"PDF appears to be image-based with {page_count} pages. Use OCR or convert to text-based PDF.")
        raise ValueError("PDF contains no extractable text (likely scanned or corrupted).")
    except Exception as e:
        if "image-based" in str(e):
            raise e
        raise ValueError("PDF parsing failed completely - file may be corrupted or password protected.")

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
