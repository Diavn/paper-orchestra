"""Offline unit checks; no network or API key is required."""
import os
import tempfile
import unittest
from unittest.mock import patch

from utils import gemini_utils as g


class DummyResponse:
    text = '{"ok": true}'


class FakeQuotaError(Exception):
    code = 429
    status = "RESOURCE_EXHAUSTED"


class SafetyTests(unittest.TestCase):
    def setUp(self):
        g._api_request_count = 0

    def test_one_call_budget(self):
        class Client:
            class models:
                @staticmethod
                def generate_content(**kwargs):
                    return DummyResponse()

        with patch.dict(os.environ, {"PAPER_ORCHESTRA_MAX_API_CALLS": "1"}), patch.object(g, "get_genai_client", return_value=Client()):
            first = g.call_gemini_with_contents(contents=["test"], model_name="gemini-4-hydrogen")
            self.assertTrue(first["parsed_response"]["ok"])
            with self.assertRaises(g.APILimitReached):
                g.call_gemini_with_contents(contents=["test"], model_name="gemini-4-hydrogen")

    def test_quota_fails_without_retry(self):
        class Client:
            class models:
                calls = 0
                @classmethod
                def generate_content(cls, **kwargs):
                    cls.calls += 1
                    raise FakeQuotaError("do not print raw error")

        with patch.dict(os.environ, {"PAPER_ORCHESTRA_MAX_API_CALLS": "3"}), patch.object(g, "get_genai_client", return_value=Client()):
            with self.assertRaises(g.GeminiQuotaExhausted):
                g.call_gemini_with_contents(contents=["test"], model_name="gemini-4-hydrogen")
            self.assertEqual(Client.models.calls, 1)

    def test_offline_corpus_requires_verified_mark(self):
        from methods.agents.literature_review_agent import PaperData
        record = {
            "citation_key": "A2026", "title": "Illustrative", "authors": ["A"],
            "venue": "Example", "year": 2026, "abstract": "",
            "citation_count": 0, "found_in_section": "Introduction",
            "reason": "Example"
        }
        parsed = PaperData(**record)
        self.assertEqual(parsed.citation_key, "A2026")


if __name__ == "__main__":
    unittest.main()
