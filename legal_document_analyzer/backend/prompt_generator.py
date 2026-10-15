"""
Prompt Generator Module
Generates structured LLM prompts adhering to the specifications of
Experiment 5 (Automated Legal Document Analyzer).
Enforces strict hallucination avoidance and deterministic JSON formatting.
"""

from typing import Optional


SYSTEM_PROMPT = """You are a legal document analysis assistant.
Analyze and summarize the provided legal document accurately and objectively.

CRITICAL CONSTRAINTS:
1. Use ONLY information directly present in the provided document text.
2. DO NOT invent, assume, extrapolate, or fabricate any facts, names, dates, amounts, or terms.
3. If any field or detail is not explicitly mentioned in the text, you MUST return: "Not specified in the document."
4. Maintain a legally neutral, clear tone.
5. You MUST return your output STRICTLY as valid JSON matching the specified JSON schema. Do not include markdown code fences or conversational text outside the JSON object."""


def build_analysis_prompt(
    document_text: str,
    document_type_hint: Optional[str] = None,
    parties_hint: Optional[str] = None,
    analysis_type: str = "Complete Analysis"
) -> str:
    """
    Constructs the user prompt instructing the LLM to analyze the legal text.
    """
    hints = []
    if document_type_hint and document_type_hint != "Other" and document_type_hint != "Auto-Detect":
        hints.append(f"- User Suggested Document Type: {document_type_hint}")
    if parties_hint and parties_hint.strip():
        hints.append(f"- User Specified Known Parties: {parties_hint.strip()}")

    hints_section = ("\nAdditional Context Provided by User:\n" + "\n".join(hints)) if hints else ""

    schema_example = """{
  "document_type": "Specific type of legal document (e.g., Employment Agreement, NDA, Rental Agreement, etc.)",
  "parties": ["Party 1 Name / Entity", "Party 2 Name / Entity"],
  "purpose": "A clear, concise statement of the primary purpose/objective of the agreement.",
  "duration": "Duration or term of the contract, including commencement and expiration if mentioned.",
  "obligations": [
    "Specific affirmative obligation or duty of party A",
    "Specific affirmative obligation or duty of party B"
  ],
  "rights": [
    "Specific right granted to party A or employer (e.g. IP ownership, inspection rights)"
  ],
  "payment_terms": "Specific monetary compensation, fees, salary, payment schedule, or currency.",
  "termination": "Specific conditions, notice period (e.g., 30 days written notice), or grounds for termination.",
  "confidentiality": "Specific non-disclosure, trade secrets, or proprietary data protections.",
  "important_dates": [
    "Effective / Start Date: DD-MM-YYYY",
    "Execution Date or Expiration Date if present"
  ],
  "governing_law": "Applicable jurisdiction, governing legal code, and arbitration/court venue.",
  "key_clauses": [
    "Confidentiality",
    "Termination",
    "Intellectual Property",
    "Payment Terms",
    "Dispute Resolution"
  ],
  "summary": "A concise abstractive summary explaining the core transaction, relationship, and key terms in 3-5 sentences."
}"""

    prompt = f"""Task: Perform a {analysis_type} on the following legal document.

{hints_section}

Information to Extract and Structure:
- Document Type
- Parties involved
- Purpose of the agreement
- Duration / Term
- Key Obligations (actionable duties of each party)
- Rights (legal rights, intellectual property ownership, licenses)
- Payment Terms (amounts, currency, intervals, invoicing)
- Termination conditions and notice periods
- Confidentiality requirements
- Important dates (start date, execution date, milestones, expiry)
- Governing law and dispute resolution
- Potentially important clauses (e.g. Confidentiality, Payment, Termination, Liability, Intellectual Property, Dispute Resolution, Non-compete, Non-solicitation)
- Summary (Concise abstractive summary)

REQUIRED OUTPUT FORMAT:
Respond with ONLY a single valid JSON object following this schema:
{schema_example}

CONSTRAINT: Use ONLY information present in the document. Do not invent facts. If any item is missing from the document, set its value to "Not specified in the document." (or empty array [] if a list).

LEGAL DOCUMENT TEXT:
\"\"\"
{document_text}
\"\"\"
"""
    return prompt
