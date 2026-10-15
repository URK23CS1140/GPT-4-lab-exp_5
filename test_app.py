"""
Automated Comprehensive Test Suite for Experiment 5
Tests extraction, preprocessing, chunking, prompt generation, analyzer, and Flask endpoints.
"""

import os
import sys
import json
import unittest

# Ensure root is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.extractor import extract_document
from backend.preprocessing import preprocess_document
from backend.chunking import chunk_document_by_paragraphs, merge_chunk_analyses
from backend.prompt_generator import build_analysis_prompt, SYSTEM_PROMPT
from backend.analyzer import fallback_rule_based_analysis, extract_json_from_text, check_ollama_service
from backend.utils import calculate_dashboard_metrics, save_analysis_json, generate_text_report, generate_html_report
from app import app


class LegalAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.sample_path = os.path.join(os.path.dirname(__file__), "sample_contract.txt")
        with open(self.sample_path, "r", encoding="utf-8") as f:
            self.sample_text = f.read()

    def test_01_text_extraction(self):
        """Test extraction from TXT file and manual text input."""
        res_file = extract_document(file_path=self.sample_path)
        self.assertEqual(res_file["status"], "success")
        self.assertIn("EMPLOYMENT AGREEMENT", res_file["text"])
        self.assertIn("ABC Technologies", res_file["text"])

        res_manual = extract_document(manual_text="This is a test legal agreement between A and B.")
        self.assertEqual(res_manual["status"], "success")
        self.assertEqual(res_manual["file_type"], "Manual Text Input")

    def test_02_preprocessing(self):
        """Test text cleaning and statistics generation."""
        raw = "  EMPLOYMENT AGREEMENT  \r\n\r\n\r\n\tBetween Party A  and  Party B.  \n"
        cleaned, stats = preprocess_document(raw, filename="test.txt")
        self.assertNotIn("\r", cleaned)
        self.assertNotIn("   ", cleaned)
        self.assertGreater(stats["word_count"], 0)
        self.assertGreater(stats["character_count"], 0)
        self.assertEqual(stats["filename"], "test.txt")

    def test_03_chunking(self):
        """Test document chunking with short and long text."""
        # Short document should be 1 chunk
        chunks_short = chunk_document_by_paragraphs(self.sample_text, max_words=2000)
        self.assertEqual(len(chunks_short), 1)
        self.assertTrue(chunks_short[0]["is_single_chunk"])

        # Long simulated document should be partitioned
        long_text = "\n\n".join([f"SECTION {i}. Clause text with repetitive legal definitions and obligations for paragraph {i}." * 20 for i in range(1, 15)])
        chunks_long = chunk_document_by_paragraphs(long_text, max_words=250, overlap_words=50)
        self.assertGreater(len(chunks_long), 1)

    def test_04_prompt_generator(self):
        """Test prompt synthesis enforcing zero-hallucination constraints."""
        prompt = build_analysis_prompt(
            document_text=self.sample_text,
            document_type_hint="Employment Agreement",
            parties_hint="ABC Technologies Pvt. Ltd., John Smith",
            analysis_type="Complete Analysis"
        )
        self.assertIn("CRITICAL CONSTRAINTS", SYSTEM_PROMPT)
        self.assertIn("Use ONLY information present in the document", prompt)
        self.assertIn("Not specified in the document", prompt)
        self.assertIn("Employment Agreement", prompt)
        self.assertIn("John Smith", prompt)

    def test_05_deterministic_analyzer(self):
        """Test fallback rule-based analyzer when Ollama is offline."""
        analysis = fallback_rule_based_analysis(
            text=self.sample_text,
            doc_type_hint="Employment Agreement",
            parties_hint="ABC Technologies Pvt. Ltd., John Smith"
        )
        self.assertIn("Employment Agreement", analysis["document_type"])
        self.assertTrue(any("ABC Technologies" in p for p in analysis["parties"]))
        self.assertTrue(any("John Smith" in p for p in analysis["parties"]))
        self.assertIn("12 months", analysis["duration"])
        self.assertIn("50,000", analysis["payment_terms"])
        self.assertIn("30 days", analysis["termination"])
        self.assertTrue(len(analysis["obligations"]) > 0)
        self.assertTrue(len(analysis["key_clauses"]) > 0)
        self.assertIn("Confidentiality", analysis["key_clauses"])
        self.assertIn("Termination", analysis["key_clauses"])
        self.assertIn("Intellectual Property", analysis["key_clauses"])
        self.assertTrue(len(analysis["summary"]) > 20)

    def test_06_json_parser_safety(self):
        """Test robust JSON parsing with markdown code fences and malformed syntax."""
        valid_json = '{"document_type": "NDA", "parties": ["A", "B"]}'
        markdown_json = '```json\n{"document_type": "NDA", "parties": ["A", "B"]}\n```'
        trailing_comma_json = '{"document_type": "NDA", "parties": ["A", "B",],}'

        self.assertIsNotNone(extract_json_from_text(valid_json))
        self.assertIsNotNone(extract_json_from_text(markdown_json))
        self.assertIsNotNone(extract_json_from_text(trailing_comma_json))

    def test_07_dashboard_metrics(self):
        """Test metric calculations."""
        mock_analysis = {
            "document_type": "Employment Agreement",
            "parties": ["Company A", "Person B"],
            "obligations": ["Duty 1", "Duty 2"],
            "key_clauses": ["Confidentiality", "Termination"],
            "important_dates": ["01-07-2026"]
        }
        mock_stats = {"word_count": 500, "character_count": 3000, "approx_page_count": 2}
        metrics = calculate_dashboard_metrics(mock_analysis, mock_stats)
        self.assertEqual(metrics["parties_count"], 2)
        self.assertEqual(metrics["obligations_count"], 2)
        self.assertEqual(metrics["key_clauses_count"], 2)
        self.assertEqual(metrics["important_dates_count"], 1)

    def test_08_api_endpoints(self):
        """Test Flask HTTP endpoints."""
        # /health
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        health_data = res_health.get_json()
        self.assertIn("ollama_active", health_data)

        # /sample
        res_sample = self.client.get("/sample")
        self.assertEqual(res_sample.status_code, 200)
        sample_data = res_sample.get_json()
        self.assertTrue(sample_data["success"])
        self.assertIn("ABC Technologies", sample_data["content"])

        # /analyze with manual text
        res_analyze = self.client.post("/analyze", data={
            "manual_text": self.sample_text,
            "document_type": "Employment Agreement",
            "parties": "ABC Technologies Pvt. Ltd., John Smith",
            "analysis_type": "Complete Analysis"
        })
        self.assertEqual(res_analyze.status_code, 200)
        data = res_analyze.get_json()
        self.assertTrue(data["success"])
        self.assertIn("analysis", data)
        self.assertIn("document_stats", data)
        self.assertIn("dashboard_metrics", data)

        # /download/txt
        res_txt = self.client.post("/download/txt", json=data)
        self.assertEqual(res_txt.status_code, 200)
        self.assertIn(b"LEGAL DOCUMENT ANALYSIS REPORT", res_txt.data)

        # /download/html
        res_html = self.client.post("/download/html", json=data)
        self.assertEqual(res_html.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", res_html.data)

        # /download/json
        res_json = self.client.post("/download/json", json=data)
        self.assertEqual(res_json.status_code, 200)


if __name__ == "__main__":
    unittest.main()
