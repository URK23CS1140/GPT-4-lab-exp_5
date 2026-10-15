"""
Chunking Module
Handles document segmentation for long legal contracts according to
Experiment 5 Preparation guidelines.
Preserves clause headers, paragraph boundaries, and semantic context.
"""

import re
from typing import List, Dict, Any


# Document length threshold: ~2500 words (~3500 tokens) fits comfortably in 8k context window of Llama 3.2
DEFAULT_MAX_WORDS_PER_CHUNK = 1800
DEFAULT_OVERLAP_WORDS = 200


def is_heading_or_clause(line: str) -> bool:
    """Detects whether a line represents a legal section, clause header, or article."""
    patterns = [
        r"^(?:SECTION|ARTICLE|CLAUSE)\s+\d+",
        r"^\d+\.\s+[A-Z]",
        r"^[A-Z\s]{4,30}$",
        r"^[IVXLCDM]+\.\s+",
        r"^\([a-z0-9]+\)\s+"
    ]
    trimmed = line.strip()
    return any(re.match(p, trimmed, re.IGNORECASE) for p in patterns)


def chunk_document_by_paragraphs(
    text: str,
    max_words: int = DEFAULT_MAX_WORDS_PER_CHUNK,
    overlap_words: int = DEFAULT_OVERLAP_WORDS
) -> List[Dict[str, Any]]:
    """
    Splits long legal documents into overlapping contextual chunks.
    Preserves paragraph and section boundaries wherever possible.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        # Fallback to line splitting if no double newlines exist
        paragraphs = [line.strip() for line in text.split("\n") if line.strip()]

    # If the document is short enough, keep it as a single chunk
    total_words = len(text.split())
    if total_words <= max_words:
        return [{
            "chunk_id": 1,
            "total_chunks": 1,
            "text": text,
            "word_count": total_words,
            "is_single_chunk": True
        }]

    chunks: List[Dict[str, Any]] = []
    current_chunk_paragraphs: List[str] = []
    current_word_count = 0

    for para in paragraphs:
        para_words = len(para.split())

        # If adding this paragraph exceeds limit, finalize the current chunk
        if current_chunk_paragraphs and (current_word_count + para_words > max_words):
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "text": chunk_text,
                "word_count": current_word_count,
                "is_single_chunk": False
            })

            # Calculate overlap from previous paragraphs
            overlap_paras: List[str] = []
            accumulated_overlap = 0
            for prev_p in reversed(current_chunk_paragraphs):
                p_len = len(prev_p.split())
                if accumulated_overlap + p_len <= overlap_words or not overlap_paras:
                    overlap_paras.insert(0, prev_p)
                    accumulated_overlap += p_len
                else:
                    break

            current_chunk_paragraphs = overlap_paras + [para]
            current_word_count = sum(len(p.split()) for p in current_chunk_paragraphs)
        else:
            current_chunk_paragraphs.append(para)
            current_word_count += para_words

    # Append remaining paragraphs
    if current_chunk_paragraphs:
        chunk_text = "\n\n".join(current_chunk_paragraphs)
        chunks.append({
            "chunk_id": len(chunks) + 1,
            "text": chunk_text,
            "word_count": current_word_count,
            "is_single_chunk": False
        })

    # Update total_chunks count
    total_chunks = len(chunks)
    for c in chunks:
        c["total_chunks"] = total_chunks

    return chunks


def merge_chunk_analyses(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combines structured extractions from multiple chunks into one consolidated legal analysis.
    Eliminates duplicates from overlapping sections.
    """
    if not chunk_results:
        return {}
    if len(chunk_results) == 1:
        return chunk_results[0]

    merged: Dict[str, Any] = {
        "document_type": "",
        "parties": [],
        "purpose": "",
        "obligations": [],
        "rights": [],
        "payment_terms": "",
        "duration": "",
        "termination": "",
        "confidentiality": "",
        "important_dates": [],
        "governing_law": "",
        "key_clauses": [],
        "summary": ""
    }

    summaries = []
    seen_parties = set()
    seen_obligations = set()
    seen_rights = set()
    seen_dates = set()
    seen_clauses = set()

    for res in chunk_results:
        if not isinstance(res, dict):
            continue

        # Document type: take first non-empty
        if not merged["document_type"] and res.get("document_type") and res["document_type"] != "Not specified in the document.":
            merged["document_type"] = res["document_type"]

        # Purpose: take first meaningful
        if not merged["purpose"] and res.get("purpose") and res["purpose"] != "Not specified in the document.":
            merged["purpose"] = res["purpose"]

        # Payment terms
        if not merged["payment_terms"] and res.get("payment_terms") and res["payment_terms"] != "Not specified in the document.":
            merged["payment_terms"] = res["payment_terms"]

        # Duration
        if not merged["duration"] and res.get("duration") and res["duration"] != "Not specified in the document.":
            merged["duration"] = res["duration"]

        # Termination
        if not merged["termination"] and res.get("termination") and res["termination"] != "Not specified in the document.":
            merged["termination"] = res["termination"]

        # Confidentiality
        if not merged["confidentiality"] and res.get("confidentiality") and res["confidentiality"] != "Not specified in the document.":
            merged["confidentiality"] = res["confidentiality"]

        # Governing Law
        if not merged["governing_law"] and res.get("governing_law") and res["governing_law"] != "Not specified in the document.":
            merged["governing_law"] = res["governing_law"]

        # Parties
        parties = res.get("parties", [])
        if isinstance(parties, list):
            for p in parties:
                p_str = str(p).strip()
                if p_str and p_str.lower() not in seen_parties:
                    seen_parties.add(p_str.lower())
                    merged["parties"].append(p_str)

        # Obligations
        obligations = res.get("obligations", [])
        if isinstance(obligations, list):
            for ob in obligations:
                ob_str = str(ob).strip()
                if ob_str and ob_str.lower() not in seen_obligations:
                    seen_obligations.add(ob_str.lower())
                    merged["obligations"].append(ob_str)

        # Rights
        rights = res.get("rights", [])
        if isinstance(rights, list):
            for r in rights:
                r_str = str(r).strip()
                if r_str and r_str.lower() not in seen_rights:
                    seen_rights.add(r_str.lower())
                    merged["rights"].append(r_str)

        # Dates
        dates = res.get("important_dates", [])
        if isinstance(dates, list):
            for d in dates:
                d_str = str(d).strip()
                if d_str and d_str.lower() not in seen_dates:
                    seen_dates.add(d_str.lower())
                    merged["important_dates"].append(d_str)

        # Key Clauses
        clauses = res.get("key_clauses", [])
        if isinstance(clauses, list):
            for c in clauses:
                c_str = str(c).strip()
                if c_str and c_str.lower() not in seen_clauses:
                    seen_clauses.add(c_str.lower())
                    merged["key_clauses"].append(c_str)

        # Summary fragments
        s = res.get("summary", "")
        if s and s != "Not specified in the document.":
            summaries.append(s)

    # Combine summary
    if summaries:
        merged["summary"] = " ".join(summaries)
    else:
        merged["summary"] = "Not specified in the document."

    # Fill defaults for remaining empty fields
    for field in ["document_type", "purpose", "payment_terms", "duration", "termination", "confidentiality", "governing_law"]:
        if not merged[field]:
            merged[field] = "Not specified in the document."

    return merged
