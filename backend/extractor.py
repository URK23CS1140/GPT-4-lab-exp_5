"""
Document Extraction Module
Responsible for extracting text from PDF, DOCX, TXT files, and manual text input.
"""

import os
from typing import Tuple, Dict, Any


def extract_from_pdf(file_path: str) -> Tuple[str, int]:
    """
    Extracts text from a PDF file using pypdf.
    Returns:
        (extracted_text, page_count)
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        return "\n\n".join(text_parts), page_count
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_from_docx(file_path: str) -> Tuple[str, int]:
    """
    Extracts text from a DOCX file using python-docx.
    Returns:
        (extracted_text, paragraph_count)
    """
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n\n".join(paragraphs), len(paragraphs)
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")


def extract_from_txt(file_path: str) -> Tuple[str, int]:
    """
    Extracts text from a plain TXT file with encodings fallback.
    Returns:
        (extracted_text, line_count)
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
                lines = content.splitlines()
                return content, len(lines)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError("Unable to read TXT file with supported encodings (UTF-8, Latin-1, CP1252).")


def extract_document(
    file_path: str = None,
    filename: str = None,
    manual_text: str = None
) -> Dict[str, Any]:
    """
    Unified extraction entry point.
    Handles uploaded files (PDF, DOCX, TXT) and manually provided legal text.
    """
    if manual_text and manual_text.strip():
        text = manual_text.strip()
        return {
            "text": text,
            "filename": filename or "manual_input.txt",
            "file_type": "Manual Text Input",
            "page_count": max(1, len(text.split()) // 450),
            "status": "success"
        }

    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("Document file not provided or does not exist.")

    ext = os.path.splitext(file_path)[1].lower()
    base_name = filename or os.path.basename(file_path)

    if ext == ".pdf":
        text, page_count = extract_from_pdf(file_path)
        file_type = "PDF"
    elif ext in [".docx", ".doc"]:
        text, count = extract_from_docx(file_path)
        file_type = "DOCX"
        page_count = max(1, len(text.split()) // 450)
    elif ext in [".txt", ".text"]:
        text, count = extract_from_txt(file_path)
        file_type = "TXT"
        page_count = max(1, len(text.split()) // 450)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed formats: .pdf, .docx, .txt")

    if not text or not text.strip():
        raise ValueError(f"The uploaded document '{base_name}' is empty or contains no readable text.")

    return {
        "text": text.strip(),
        "filename": base_name,
        "file_type": file_type,
        "page_count": page_count,
        "status": "success"
    }
