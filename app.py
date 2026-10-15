"""
Automated Legal Document Analyzer using GPT-4 / Ollama (Llama 3.2)
Main Flask Web Application Entrypoint
Experiment 5 - Building Applications using GPT-4
"""

import os
import json
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

from backend.extractor import extract_document
from backend.preprocessing import preprocess_document
from backend.analyzer import run_full_analysis, check_ollama_service, is_model_available, DEFAULT_MODEL
from backend.utils import (
    calculate_dashboard_metrics,
    save_analysis_json,
    generate_text_report,
    generate_html_report,
    OUTPUTS_DIR
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".text"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit


@app.route("/")
def index():
    """Renders the main legal document analyzer dashboard."""
    is_running, status_msg, models = check_ollama_service()
    has_model, model_msg = is_model_available(DEFAULT_MODEL) if is_running else (False, "Ollama offline")
    return render_template(
        "index.html",
        ollama_running=is_running,
        ollama_status_msg=status_msg,
        models=models,
        has_default_model=has_model,
        default_model=DEFAULT_MODEL
    )


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint indicating server and Ollama status."""
    is_running, status_msg, models = check_ollama_service()
    has_model, model_msg = is_model_available(DEFAULT_MODEL) if is_running else (False, "Ollama offline")
    return jsonify({
        "status": "online",
        "ollama_active": is_running,
        "ollama_status_message": status_msg,
        "available_models": models,
        "target_model": DEFAULT_MODEL,
        "target_model_installed": has_model,
        "target_model_message": model_msg
    })


@app.route("/sample", methods=["GET"])
def get_sample_document():
    """Returns the fictional sample legal contract for immediate testing."""
    sample_path = os.path.join(BASE_DIR, "sample_contract.txt")
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({
            "success": True,
            "filename": "sample_contract.txt",
            "document_type": "Employment Agreement",
            "parties": "ABC Technologies Pvt. Ltd., John Smith",
            "content": content
        })
    return jsonify({"success": False, "error": "Sample document not found."}), 404


@app.route("/analyze", methods=["POST"])
def analyze_document():
    """
    Main analysis endpoint.
    Accepts:
      - file: PDF, DOCX, or TXT document (optional if manual_text provided)
      - manual_text: Directly pasted legal text (optional if file provided)
      - document_type: Selected or user-provided document type
      - parties: Optional user-provided parties hint
      - analysis_type: 'Summary', 'Clause Analysis', 'Obligation Analysis', 'Complete Analysis'
      - preferred_model: Optional model override
    """
    try:
        document_type = request.form.get("document_type", "Employment Agreement")
        parties_hint = request.form.get("parties", "")
        analysis_type = request.form.get("analysis_type", "Complete Analysis")
        manual_text = request.form.get("manual_text", "").strip()
        preferred_model = request.form.get("preferred_model", DEFAULT_MODEL)

        uploaded_file = request.files.get("file")
        saved_file_path = None
        original_filename = "manual_input.txt"

        if uploaded_file and uploaded_file.filename:
            original_filename = secure_filename(uploaded_file.filename)
            _, ext = os.path.splitext(original_filename)
            if ext.lower() not in ALLOWED_EXTENSIONS:
                return jsonify({
                    "success": False,
                    "error": f"Unsupported file type '{ext}'. Please upload a PDF, DOCX, or TXT file."
                }), 400

            saved_file_path = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
            uploaded_file.save(saved_file_path)

        # 1. Extraction Module
        if not saved_file_path and not manual_text:
            return jsonify({
                "success": False,
                "error": "No legal document provided. Please upload a file or paste legal text."
            }), 400

        extracted_data = extract_document(
            file_path=saved_file_path,
            filename=original_filename,
            manual_text=manual_text if not saved_file_path else None
        )

        raw_text = extracted_data["text"]

        # 2. Preprocessing Module
        cleaned_text, doc_stats = preprocess_document(
            raw_text=raw_text,
            filename=extracted_data["filename"],
            doc_type_hint=document_type,
            page_count_hint=extracted_data.get("page_count")
        )

        if not cleaned_text:
            return jsonify({
                "success": False,
                "error": "The document contains no readable text after preprocessing."
            }), 400

        # 3. Prompting, Chunking & LLM Analysis
        analysis_result = run_full_analysis(
            text=cleaned_text,
            document_type_hint=document_type,
            parties_hint=parties_hint,
            analysis_type=analysis_type,
            preferred_model=preferred_model
        )

        # If user explicitly selected a document type and model didn't find one or was vague
        if document_type and document_type not in ["Other", "Auto-Detect"]:
            if not analysis_result.get("document_type") or analysis_result["document_type"] == "Not specified in the document.":
                analysis_result["document_type"] = document_type

        # 4. Dashboard Metrics Calculation
        dashboard_metrics = calculate_dashboard_metrics(analysis_result, doc_stats)

        # 5. Save Results to outputs directory
        full_payload = {
            "analysis": analysis_result,
            "document_stats": doc_stats,
            "dashboard_metrics": dashboard_metrics
        }
        saved_filename = save_analysis_json(full_payload, filename_prefix=doc_stats["filename"])

        return jsonify({
            "success": True,
            "analysis": analysis_result,
            "document_stats": doc_stats,
            "dashboard_metrics": dashboard_metrics,
            "saved_json": saved_filename
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Document analysis failed: {str(e)}"
        }), 500


@app.route("/download/<file_type>", methods=["POST"])
def download_report(file_type: str):
    """
    Generates and returns downloadable reports (JSON, TXT, HTML).
    """
    try:
        data = request.get_json(force=True)
        filename_base = data.get("document_stats", {}).get("filename", "legal_analysis")
        clean_base = os.path.splitext(filename_base)[0]

        if file_type == "json":
            content = json.dumps(data, indent=2)
            return Response(
                content,
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment;filename={clean_base}_analysis.json"}
            )
        elif file_type == "txt":
            content = generate_text_report(data)
            return Response(
                content,
                mimetype="text/plain; charset=utf-8",
                headers={"Content-Disposition": f"attachment;filename={clean_base}_analysis.txt"}
            )
        elif file_type == "html":
            content = generate_html_report(data)
            return Response(
                content,
                mimetype="text/html; charset=utf-8",
                headers={"Content-Disposition": f"attachment;filename={clean_base}_analysis.html"}
            )
        else:
            return jsonify({"error": "Unsupported download format"}), 400

    except Exception as e:
        return jsonify({"error": f"Download generation failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"============================================================")
    print(f" Automated Legal Document Analyzer (Experiment 5)")
    print(f" Running on http://127.0.0.1:{port}")
    print(f" Target Model: {DEFAULT_MODEL}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=True)
