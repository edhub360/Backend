import io
from typing import List, Tuple
from pathlib import Path
from pypdf import PdfReader
from docx import Document

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text.strip():
                text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)
        return "\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"Error processing DOCX: {str(e)}")

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT bytes."""
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise ValueError(f"Error processing TXT: {str(e)}")

def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from file based on extension."""
    suffix = Path(filename).suffix.lower()
    
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt
    }
    
    if suffix not in extractors:
        raise ValueError(f"Unsupported file type: {suffix}")
    
    return extractors[suffix](file_bytes)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []
    
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end == len(words):
            break
        
        start = end - overlap
        if start < 0:
            start = 0
    
    return chunks
