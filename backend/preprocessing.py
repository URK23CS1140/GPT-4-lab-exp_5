"""
Document Preprocessing Module
Responsible for cleaning, formatting normalization, and computing basic metrics
without altering legal semantics or numbering.
"""

import re
from typing import Dict, Any, Tuple


def clean_legal_text(raw_text: str) -> str:
    """
    Cleans raw extracted legal text:
    - Normalizes carriage returns and line feeds
    - Replaces non-breaking spaces and tabs
    - Collapses repeated spaces while preserving paragraph breaks
    - Removes isolated pagination artifacts
    - Retains numbered clauses, bullets, and legal structure
    """
    if not raw_text:
        return ""

    # Normalize line breaks
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace special unicode spaces and non-breaking spaces
    text = re.sub(r"[\u00A0\u2000-\u200B\u202F\u205F\u3000]", " ", text)

    # Replace tabs with single space
    text = text.replace("\t", " ")

    # Remove repeated spaces within a line
    text = re.sub(r"[ ]{2,}", " ", text)

    # Strip whitespace from each individual line
    lines = [line.strip() for line in text.split("\n")]

    # Remove excessive blank lines (more than 2 consecutive blank lines -> 1 blank line)
    cleaned_lines = []
    blank_counter = 0
    for line in lines:
        if line:
            blank_counter = 0
            cleaned_lines.append(line)
        else:
            blank_counter += 1
            if blank_counter <= 1:
                cleaned_lines.append("")

    cleaned_text = "\n".join(cleaned_lines).strip()
    return cleaned_text


def compute_document_statistics(
    text: str,
    filename: str = "document.txt",
    doc_type_hint: str = "Unspecified",
    page_count_hint: int = None
) -> Dict[str, Any]:
    """
    Computes document metadata and statistics:
    - Character count (with and without whitespace)
    - Word count
    - Estimated or actual page count
    - Paragraph count
    - Line count
    """
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", "").replace("\n", ""))
    words = text.split()
    word_count = len(words)

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)
    line_count = len(text.splitlines())

    # Determine page count: prefer actual PDF page count if valid, else calculate (~450 words/page)
    if page_count_hint and page_count_hint > 0:
        page_count = page_count_hint
    else:
        page_count = max(1, round(word_count / 450)) if word_count > 0 else 0

    return {
        "filename": filename,
        "document_type_hint": doc_type_hint,
        "character_count": char_count,
        "character_count_no_spaces": char_count_no_spaces,
        "word_count": word_count,
        "paragraph_count": paragraph_count,
        "line_count": line_count,
        "approx_page_count": page_count
    }


def preprocess_document(
    raw_text: str,
    filename: str = "document.txt",
    doc_type_hint: str = "Unspecified",
    page_count_hint: int = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Main preprocessing pipeline:
    Cleans text and computes document metrics.
    """
    cleaned_text = clean_legal_text(raw_text)
    stats = compute_document_statistics(
        cleaned_text,
        filename=filename,
        doc_type_hint=doc_type_hint,
        page_count_hint=page_count_hint
    )
    return cleaned_text, stats
