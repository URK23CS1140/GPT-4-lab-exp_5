"""
Utility Module
Handles exporting analysis results (JSON, TXT, HTML), calculating dashboard metrics,
and managing outputs according to the experiment requirements.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Sanitizes strings for safe filename usage."""
    clean = re.sub(r"[^\w\-_.]", "_", name)
    return clean[:50]


def calculate_dashboard_metrics(analysis_result: Dict[str, Any], doc_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes dashboard summary metrics:
    - Parties count
    - Obligations count
    - Key clauses count
    - Important dates count
    - Combined document word and char counts
    """
    parties = analysis_result.get("parties", [])
    if isinstance(parties, str):
        parties_count = 1 if parties != "Not specified in the document." else 0
    else:
        parties_count = len([p for p in parties if p and p != "Not specified in the document."])

    obligations = analysis_result.get("obligations", [])
    if isinstance(obligations, str):
        ob_count = 1 if obligations != "Not specified in the document." else 0
    else:
        ob_count = len([o for o in obligations if o and o != "Not specified in the document."])

    clauses = analysis_result.get("key_clauses", [])
    if isinstance(clauses, str):
        clauses_count = 1 if clauses != "Not specified in the document." else 0
    else:
        clauses_count = len([c for c in clauses if c and c != "Not specified in the document."])

    dates = analysis_result.get("important_dates", [])
    if isinstance(dates, str):
        dates_count = 1 if dates != "Not specified in the document." else 0
    else:
        dates_count = len([d for d in dates if d and d != "Not specified in the document."])

    return {
        "word_count": doc_stats.get("word_count", 0),
        "character_count": doc_stats.get("character_count", 0),
        "approx_pages": doc_stats.get("approx_page_count", 1),
        "parties_count": parties_count,
        "obligations_count": ob_count,
        "key_clauses_count": clauses_count,
        "important_dates_count": dates_count,
        "document_type": analysis_result.get("document_type", "Legal Agreement")
    }


def save_analysis_json(data: Dict[str, Any], filename_prefix: str = "analysis") -> str:
    """Saves the complete analysis result to a JSON file in the outputs directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_prefix = sanitize_filename(filename_prefix)
    output_filename = f"{clean_prefix}_{timestamp}.json"
    file_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_filename


def generate_text_report(data: Dict[str, Any]) -> str:
    """
    Generates a formatted plain-text legal analysis report
    matching the Recommended Output Format in EXPT 5 PREPARATION.pdf.
    """
    analysis = data.get("analysis", {})
    stats = data.get("document_stats", {})

    lines = [
        "============================================================",
        "                LEGAL DOCUMENT ANALYSIS REPORT              ",
        "============================================================",
        f"Generated At: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
        f"File Name:    {stats.get('filename', 'Manual Input')}",
        f"Engine:       {analysis.get('inference_engine', 'Local LLM Inference')}",
        "------------------------------------------------------------",
        "",
        "DOCUMENT TYPE:",
        f"  {analysis.get('document_type', 'Not specified in the document.')}",
        "",
        "PARTIES:",
    ]

    parties = analysis.get("parties", [])
    if isinstance(parties, list) and parties:
        for p in parties:
            lines.append(f"  • {p}")
    else:
        lines.append(f"  {parties if parties else 'Not specified in the document.'}")

    lines.extend([
        "",
        "PURPOSE:",
        f"  {analysis.get('purpose', 'Not specified in the document.')}",
        "",
        "DURATION / TERM:",
        f"  {analysis.get('duration', 'Not specified in the document.')}",
        "",
        "KEY OBLIGATIONS:",
    ])

    obligations = analysis.get("obligations", [])
    if isinstance(obligations, list) and obligations:
        for ob in obligations:
            lines.append(f"  • {ob}")
    else:
        lines.append(f"  {obligations if obligations else 'Not specified in the document.'}")

    lines.extend([
        "",
        "RIGHTS:",
    ])

    rights = analysis.get("rights", [])
    if isinstance(rights, list) and rights:
        for r in rights:
            lines.append(f"  • {r}")
    else:
        lines.append(f"  {rights if rights else 'Not specified in the document.'}")

    lines.extend([
        "",
        "PAYMENT TERMS:",
        f"  {analysis.get('payment_terms', 'Not specified in the document.')}",
        "",
        "TERMINATION CONDITIONS:",
        f"  {analysis.get('termination', 'Not specified in the document.')}",
        "",
        "CONFIDENTIALITY:",
        f"  {analysis.get('confidentiality', 'Not specified in the document.')}",
        "",
        "IMPORTANT DATES:",
    ])

    dates = analysis.get("important_dates", [])
    if isinstance(dates, list) and dates:
        for d in dates:
            lines.append(f"  • {d}")
    else:
        lines.append(f"  {dates if dates else 'Not specified in the document.'}")

    lines.extend([
        "",
        "GOVERNING LAW:",
        f"  {analysis.get('governing_law', 'Not specified in the document.')}",
        "",
        "POTENTIALLY IMPORTANT CLAUSES:",
    ])

    clauses = analysis.get("key_clauses", [])
    if isinstance(clauses, list) and clauses:
        for c in clauses:
            lines.append(f"  • {c}")
    else:
        lines.append(f"  {clauses if clauses else 'Not specified in the document.'}")

    lines.extend([
        "",
        "EXECUTIVE SUMMARY:",
        f"  {analysis.get('summary', 'Not specified in the document.')}",
        "",
        "============================================================",
        "DISCLAIMER:",
        "This tool provides automated document analysis for educational and",
        "informational purposes only. It is not legal advice and should not",
        "replace consultation with a qualified legal professional.",
        "============================================================"
    ])

    return "\n".join(lines)


def generate_html_report(data: Dict[str, Any]) -> str:
    """Generates a clean, printable HTML report."""
    analysis = data.get("analysis", {})
    stats = data.get("document_stats", {})

    parties_html = "".join(f"<li>{p}</li>" for p in analysis.get("parties", [])) or "<li>Not specified in the document.</li>"
    obligations_html = "".join(f"<li>{o}</li>" for o in analysis.get("obligations", [])) or "<li>Not specified in the document.</li>"
    rights_html = "".join(f"<li>{r}</li>" for r in analysis.get("rights", [])) or "<li>Not specified in the document.</li>"
    dates_html = "".join(f"<li>{d}</li>" for d in analysis.get("important_dates", [])) or "<li>Not specified in the document.</li>"
    clauses_html = "".join(f"<span class='badge'>{c}</span>" for c in analysis.get("key_clauses", [])) or "<span class='badge'>None identified</span>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Legal Analysis Report - {stats.get('filename', 'Document')}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a202c; max-width: 860px; margin: 40px auto; padding: 20px; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 24px; }}
    .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    .card h3 {{ margin-top: 0; color: #1e3a8a; font-size: 16px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }}
    .badge {{ display: inline-block; background: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin: 3px; }}
    ul {{ padding-left: 20px; margin: 8px 0; }}
    li {{ margin-bottom: 4px; }}
    .disclaimer {{ background: #fffbeb; border: 1px solid #fde68a; color: #92400e; padding: 12px; border-radius: 6px; font-size: 12px; margin-top: 30px; }}
    @media print {{ body {{ margin: 10px; }} .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()" style="float: right; padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Print Report</button>
  <h1>LEGAL DOCUMENT ANALYSIS</h1>
  <div class="subtitle">Document: <strong>{stats.get('filename', 'Manual Input')}</strong> | Processed: {datetime.now().strftime('%d-%m-%Y %H:%M')} | Engine: {analysis.get('inference_engine', 'Local LLM')}</div>

  <div class="card">
    <h3>Executive Document Summary</h3>
    <p>{analysis.get('summary', 'Not specified in the document.')}</p>
  </div>

  <div class="card">
    <h3>Document Type & Purpose</h3>
    <p><strong>Document Type:</strong> {analysis.get('document_type', 'Not specified in the document.')}</p>
    <p><strong>Purpose:</strong> {analysis.get('purpose', 'Not specified in the document.')}</p>
    <p><strong>Duration / Term:</strong> {analysis.get('duration', 'Not specified in the document.')}</p>
  </div>

  <div class="card">
    <h3>Parties Involved</h3>
    <ul>{parties_html}</ul>
  </div>

  <div class="card">
    <h3>Key Obligations</h3>
    <ul>{obligations_html}</ul>
  </div>

  <div class="card">
    <h3>Rights & Intellectual Property</h3>
    <ul>{rights_html}</ul>
  </div>

  <div class="card">
    <h3>Financial & Termination Terms</h3>
    <p><strong>Payment Terms:</strong> {analysis.get('payment_terms', 'Not specified in the document.')}</p>
    <p><strong>Termination Conditions:</strong> {analysis.get('termination', 'Not specified in the document.')}</p>
    <p><strong>Confidentiality:</strong> {analysis.get('confidentiality', 'Not specified in the document.')}</p>
    <p><strong>Governing Law:</strong> {analysis.get('governing_law', 'Not specified in the document.')}</p>
  </div>

  <div class="card">
    <h3>Important Dates</h3>
    <ul>{dates_html}</ul>
  </div>

  <div class="card">
    <h3>Potentially Important Clauses Identified</h3>
    <div>{clauses_html}</div>
  </div>

  <div class="disclaimer">
    <strong>DISCLAIMER:</strong> This tool provides automated document analysis for educational and informational purposes only. It is not legal advice and should not replace consultation with a qualified legal professional.
  </div>
</body>
</html>"""
