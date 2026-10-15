"""
Ollama Integration and Legal Document Analyzer Module
Communicates with local Ollama service for llama3.2:latest inference.
Includes JSON parsing safeguards and fallback rule-based extraction.
"""

import json
import os
import re
import requests
from typing import Dict, Any, Tuple, Optional
from backend.prompt_generator import SYSTEM_PROMPT, build_analysis_prompt
from backend.chunking import chunk_document_by_paragraphs, merge_chunk_analyses

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
REQUEST_TIMEOUT_SECONDS = 90


def check_ollama_service() -> Tuple[bool, str, list]:
    """
    Checks if the local Ollama service is reachable and lists installed models.
    Returns:
        (is_running, status_message, list_of_models)
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, "Ollama service is active and accessible.", models
        return False, f"Ollama service responded with status {response.status_code}.", []
    except requests.exceptions.ConnectionError:
        return False, "Ollama is not running. Start it in terminal via: 'ollama serve'", []
    except requests.exceptions.Timeout:
        return False, "Connection to Ollama service timed out.", []
    except Exception as e:
        return False, f"Unable to reach Ollama: {str(e)}", []


def is_model_available(model_name: str = DEFAULT_MODEL) -> Tuple[bool, str]:
    """Checks whether the requested model is pulled locally."""
    is_running, msg, models = check_ollama_service()
    if not is_running:
        return False, msg

    # Check exact match or base match (e.g., llama3.2 matches llama3.2:latest)
    clean_target = model_name.split(":")[0].lower()
    for m in models:
        m_lower = m.lower()
        if model_name.lower() in m_lower or clean_target in m_lower:
            return True, f"Model '{m}' is available."

    return False, (
        f"Model '{model_name}' is not installed in Ollama. "
        f"Available models: {models if models else 'None'}. "
        f"Please run 'ollama pull {model_name}' in your terminal."
    )


def extract_json_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extracts and parses JSON from model output, handling:
    - Markdown code fences (```json ... ```)
    - Preamble/postamble text
    - Trailing commas in arrays or objects
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()

    # Direct parse attempt
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Strip markdown code blocks
    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except Exception:
            pass

    # Search for first '{' and last '}'
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            # Clean trailing commas
            fixed = re.sub(r",\s*([\}\]])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except Exception:
                pass

    return None


def fallback_rule_based_analysis(
    text: str,
    doc_type_hint: Optional[str] = None,
    parties_hint: Optional[str] = None,
    analysis_type: str = "Complete Analysis"
) -> Dict[str, Any]:
    """
    Deterministic rule-based legal extraction fallback.
    Used when Ollama service is unavailable or times out, guaranteeing
    seamless lab demonstration and testing.
    """
    lines = text.splitlines()
    first_few_lines = "\n".join(lines[:15])

    # 1. Document Type Detection
    doc_type = doc_type_hint if doc_type_hint and doc_type_hint not in ["Other", "Auto-Detect"] else "Not specified in the document."
    if doc_type == "Not specified in the document.":
        type_patterns = [
            ("Employment Agreement", r"employment\s+agreement|appointment\s+letter|offer\s+of\s+employment"),
            ("Non-Disclosure Agreement (NDA)", r"non-disclosure\s+agreement|confidentiality\s+agreement|\bnda\b"),
            ("Rental / Lease Agreement", r"rental\s+agreement|lease\s+agreement|tenancy\s+agreement"),
            ("Service Agreement", r"service\s+agreement|consulting\s+agreement|master\s+services\s+agreement"),
            ("Sales Agreement", r"sales\s+agreement|purchase\s+agreement|sale\s+deed"),
            ("Loan Agreement", r"loan\s+agreement|credit\s+facility|promissory\s+note"),
            ("Privacy Policy", r"privacy\s+policy"),
            ("Terms and Conditions", r"terms\s+and\s+conditions|terms\s+of\s+service"),
            ("Business Contract", r"business\s+contract|partnership\s+deed|joint\s+venture"),
            ("Legal Notice", r"legal\s+notice|demand\s+notice")
        ]
        for name, pat in type_patterns:
            if re.search(pat, first_few_lines, re.IGNORECASE) or re.search(pat, text[:500], re.IGNORECASE):
                doc_type = name
                break

    # 2. Parties Extraction
    parties = []
    if parties_hint and parties_hint.strip():
        parties = [p.strip() for p in re.split(r"[,;]|(?:\s+and\s+)", parties_hint) if p.strip()]

    if not parties:
        # Search for "between ... and ...", "by and between", "PARTIES:"
        between_match = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:,|\.|\n|hereinafter|\()", text, re.IGNORECASE)
        if between_match:
            p1 = re.sub(r"^[\d\.\-\s]+", "", between_match.group(1)).strip()
            p2 = re.sub(r"^[\d\.\-\s]+", "", between_match.group(2)).strip()
            if len(p1) < 80:
                parties.append(p1)
            if len(p2) < 80:
                parties.append(p2)

        # Look under PARTIES: section
        if not parties:
            parties_block = re.search(r"PARTIES:?\s*\n([\s\S]{10,250}?)(?=\n\s*(?:\d+\.|\bPURPOSE\b|\bWHEREAS\b))", text, re.IGNORECASE)
            if parties_block:
                p_lines = [l.strip() for l in parties_block.group(1).split("\n") if l.strip()]
                for l in p_lines:
                    cleaned_p = re.sub(r"^(?:\d+[\.\)]|[-•])\s*", "", l)
                    cleaned_p = cleaned_p.split(",")[0].strip()
                    if cleaned_p and len(cleaned_p) < 80 and not cleaned_p.lower().startswith("and"):
                        parties.append(cleaned_p)

    if not parties:
        parties = ["Employer and Employee"] if "employment" in doc_type.lower() else ["Party A", "Party B"]

    # 3. Purpose Extraction
    purpose = "Not specified in the document."
    purpose_match = re.search(r"(?:PURPOSE|OBJECTIVE|SCOPE|WHEREAS)\s*[:\.]?\s*([^\n\.]+(?:\.[^\n\.]+){0,2})", text, re.IGNORECASE)
    if purpose_match:
        purpose = purpose_match.group(1).strip()
    elif "employment" in doc_type.lower():
        purpose = f"Employment of the individual by the organization under agreed terms and conditions."

    # 4. Duration / Term Extraction
    duration = "Not specified in the document."
    dur_match = re.search(r"(?:duration|term|period)\s*(?:of\s+this\s+agreement)?\s*[:\.]?\s*([^\n\.]*(?:\d+\s*(?:months?|years?|days?|weeks?)|effective\s+until[^\n\.]+))", text, re.IGNORECASE)
    if dur_match:
        duration = dur_match.group(1).strip()
    else:
        num_months = re.search(r"(\b\d+\s+months?\b)", text, re.IGNORECASE)
        if num_months:
            duration = num_months.group(1)

    # 5. Key Obligations
    obligations = []
    ob_section = re.search(r"(?:OBLIGATIONS|DUTIES|RESPONSIBILITIES)\s*[:\.]?\s*\n([\s\S]{20,500}?)(?=\n\s*(?:\d+\.|\bRIGHTS\b|\bPAYMENT\b|\bTERMINATION\b))", text, re.IGNORECASE)
    if ob_section:
        for line in ob_section.group(1).splitlines():
            line = line.strip()
            if line and (line.startswith(("•", "-", "*", "(a)", "(b)", "(c)")) or re.match(r"^\d+\.", line)):
                clean_ob = re.sub(r"^(?:•|-|\*|\([a-z0-9]+\)|\d+\.)\s*", "", line).strip()
                if clean_ob:
                    obligations.append(clean_ob)
    if not obligations:
        if re.search(r"confidential", text, re.IGNORECASE):
            obligations.append("Maintain strict confidentiality regarding proprietary and company information.")
        if re.search(r"perform\s+assigned\s+duties", text, re.IGNORECASE):
            obligations.append("Perform assigned duties diligently and follow company policies.")

    # 6. Rights & Intellectual Property
    rights = []
    ip_match = re.search(r"(?:RIGHTS|INTELLECTUAL\s+PROPERTY)\s*[:\.]?\s*([^\n]+(?:\n[^\n]+){0,2})", text, re.IGNORECASE)
    if ip_match:
        clean_r = ip_match.group(1).strip()
        rights.append(clean_r[:200])
    elif re.search(r"intellectual\s+property", text, re.IGNORECASE):
        rights.append("Any intellectual property created during employment belongs to the company.")

    # 7. Payment Terms
    payment_terms = "Not specified in the document."
    pay_match = re.search(r"(?:salary|compensation|payment|fee|remuneration)\s*(?:terms)?\s*[:\.]?\s*([^\n\.]*(?:₹|\$|€|rs\.?|inr|usd)?\s*[\d,]+(?:\s*(?:per|\/)\s*(?:month|annum|hour|milestone))?[^\n\.]*)", text, re.IGNORECASE)
    if pay_match:
        payment_terms = pay_match.group(1).strip()
    else:
        salary_match = re.search(r"((?:₹|\$|€|rs\.?|inr)\s*[\d,]+(?:\s*(?:per|\/)\s*month)?)", text, re.IGNORECASE)
        if salary_match:
            payment_terms = f"Monthly compensation of {salary_match.group(1)}"

    # 8. Termination
    termination = "Not specified in the document."
    term_match = re.search(r"termination\s*(?:conditions|provisions)?\s*[:\.]?\s*([^\n\.]*(?:\d+\s*days?\s*written\s*notice|[^\n\.]+))", text, re.IGNORECASE)
    if term_match:
        termination = term_match.group(1).strip()
    else:
        notice_match = re.search(r"(\b\d+\s+days?\s+written\s+notice\b)", text, re.IGNORECASE)
        if notice_match:
            termination = f"Either party may terminate by providing {notice_match.group(1)}."

    # 9. Confidentiality
    confidentiality = "Not specified in the document."
    conf_match = re.search(r"confidentiality\s*[:\.]?\s*([^\n\.]+(?:\.[^\n\.]+){0,2})", text, re.IGNORECASE)
    if conf_match:
        confidentiality = conf_match.group(1).strip()
    elif re.search(r"confidential", text, re.IGNORECASE):
        confidentiality = "Maintain confidentiality regarding company proprietary information and client records."

    # 10. Important Dates
    important_dates = []
    date_matches = re.findall(r"\b(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b", text)
    if date_matches:
        for d in sorted(set(date_matches)):
            important_dates.append(f"Date referenced: {d}")
    else:
        important_dates.append("Not specified in the document.")

    # 11. Governing Law
    governing_law = "Not specified in the document."
    gov_match = re.search(r"governing\s+law\s*[:\.]?\s*([^\n\.]+(?:\.[^\n\.]+){0,1})", text, re.IGNORECASE)
    if gov_match:
        governing_law = gov_match.group(1).strip()
    elif re.search(r"laws\s+of\s+([A-Za-z\s]+)", text, re.IGNORECASE):
        law_country = re.search(r"laws\s+of\s+([A-Za-z\s]+?)(?:\.|,|\n)", text, re.IGNORECASE)
        if law_country:
            governing_law = f"Applicable laws of {law_country.group(1).strip()}"

    # 12. Potentially Important Clauses
    key_clauses = []
    potential_clauses = [
        ("Confidentiality", r"\bconfidential|\bnon-disclosure\b"),
        ("Termination", r"\bterminat\w+"),
        ("Intellectual Property", r"\bintellectual\s+property\b|\bip\s+rights\b|\bcopyright\b|\bpatent\b"),
        ("Payment Terms", r"\bpayment|\bsalary|\bfee\b|\bcompensation\b"),
        ("Liability", r"\bliabilit\w+|\bindemnif\w+"),
        ("Dispute Resolution", r"\bdispute|\barbitration|\bjurisdiction\b"),
        ("Governing Law", r"\bgoverning\s+law\b|\bapplicable\s+law\b"),
        ("Non-compete", r"\bnon-compete\b|\brestriction\s+on\s+competition\b"),
        ("Non-solicitation", r"\bnon-solicitation\b"),
        ("Data Protection / Privacy", r"\bdata\s+protection\b|\bprivacy\b|\bgdpr\b")
    ]
    for clause_name, pat in potential_clauses:
        if re.search(pat, text, re.IGNORECASE):
            key_clauses.append(clause_name)

    # 13. Abstractive Summary
    party_str = " and ".join(parties[:2]) if parties else "the involved parties"
    summary = (
        f"A {doc_type.lower() if doc_type != 'Not specified in the document.' else 'legal agreement'} "
        f"entered into between {party_str}. The agreement outlines the purpose: {purpose.lower() if purpose != 'Not specified in the document.' else 'governing mutual rights and obligations'}. "
        f"Key provisions include payment terms ({payment_terms}), duration ({duration}), "
        f"and termination notice requirements ({termination}). Both parties are bound by standard confidentiality and governing legal frameworks."
    )

    return {
        "document_type": doc_type,
        "parties": parties,
        "purpose": purpose,
        "duration": duration,
        "obligations": obligations if obligations else ["Not specified in the document."],
        "rights": rights if rights else ["Not specified in the document."],
        "payment_terms": payment_terms,
        "termination": termination,
        "confidentiality": confidentiality,
        "important_dates": important_dates,
        "governing_law": governing_law,
        "key_clauses": key_clauses,
        "summary": summary,
        "inference_engine": "Rule-Based Deterministic Engine (Offline Fallback)"
    }


def analyze_with_ollama(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Executes local inference with Ollama service using Llama 3.2.
    """
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,  # Low temperature for strict factual extraction
            "top_p": 0.9,
            "num_predict": 1500
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        if response.status_code == 200:
            data = response.json()
            raw_response = data.get("response", "")
            parsed = extract_json_from_text(raw_response)
            if parsed:
                parsed["inference_engine"] = f"Local Ollama ({model})"
                return parsed
            else:
                # Fallback to text formatting if JSON parse fails
                return {
                    "document_type": "Extracted via LLM",
                    "parties": [],
                    "purpose": "See summary below.",
                    "duration": "Not specified in the document.",
                    "obligations": [],
                    "rights": [],
                    "payment_terms": "Not specified in the document.",
                    "termination": "Not specified in the document.",
                    "confidentiality": "Not specified in the document.",
                    "important_dates": [],
                    "governing_law": "Not specified in the document.",
                    "key_clauses": [],
                    "summary": raw_response,
                    "inference_engine": f"Local Ollama ({model}) - Raw Text Fallback"
                }
        else:
            raise RuntimeError(f"Ollama returned HTTP error {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama is not running. Please start Ollama using 'ollama serve' in your terminal.")
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama inference timed out. The document may be too large or the model is still loading.")


def run_full_analysis(
    text: str,
    document_type_hint: Optional[str] = None,
    parties_hint: Optional[str] = None,
    analysis_type: str = "Complete Analysis",
    preferred_model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    High-level orchestrator:
    1. Checks Ollama status.
    2. Segments long documents into chunks if required.
    3. Runs Ollama inference or fallback.
    4. Merges and formats the final structured legal analysis.
    """
    is_running, status_msg, models = check_ollama_service()

    # Determine if we should attempt Ollama or fallback
    use_ollama = is_running
    model_to_use = preferred_model
    if is_running:
        # Check if requested model or any llama model is available
        has_model, model_msg = is_model_available(preferred_model)
        if not has_model:
            # Check if any model exists in Ollama
            if models:
                model_to_use = models[0]
            else:
                use_ollama = False

    chunks = chunk_document_by_paragraphs(text)
    chunk_results = []

    if use_ollama:
        try:
            for chunk in chunks:
                prompt = build_analysis_prompt(
                    chunk["text"],
                    document_type_hint=document_type_hint,
                    parties_hint=parties_hint,
                    analysis_type=analysis_type
                )
                res = analyze_with_ollama(prompt, model=model_to_use)
                chunk_results.append(res)
            merged = merge_chunk_analyses(chunk_results)
            merged["inference_engine"] = f"Local Ollama ({model_to_use})"
            merged["chunks_processed"] = len(chunks)
            return merged
        except Exception as e:
            # Ollama failed during inference; fall back gracefully to rule-based engine
            fallback_res = fallback_rule_based_analysis(text, document_type_hint, parties_hint, analysis_type)
            fallback_res["notice"] = f"Ollama execution encountered an issue ({str(e)}). Displaying deterministic extraction result."
            fallback_res["chunks_processed"] = len(chunks)
            return fallback_res
    else:
        # Service unavailable or offline: execute deterministic rule-based analysis
        res = fallback_rule_based_analysis(text, document_type_hint, parties_hint, analysis_type)
        res["chunks_processed"] = len(chunks)
        res["notice"] = (
            "Local Ollama service is currently offline or unreachable. "
            "To activate Llama 3.2 inference, open terminal and run: 'ollama serve' "
            "followed by 'ollama pull llama3.2:latest'. "
            "The results below were extracted using the embedded deterministic legal parser."
        )
        return res
