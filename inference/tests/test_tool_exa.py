"""Tests for the Exa search backend (``inference/tool_exa.py``).

These tests do not hit the live Exa API. They mock the ``exa_py.Exa`` class
and assert response parsing, snippet fallback ordering, the integration header,
and behavior when ``EXA_API_KEY`` is unset.
"""

import os
import sys
import unittest
from unittest import mock

# The inference package uses sibling-relative imports (e.g. ``from tool_exa import ...``)
# so we add the inference directory to sys.path for these tests.
HERE = os.path.dirname(os.path.abspath(__file__))
INFERENCE_DIR = os.path.dirname(HERE)
if INFERENCE_DIR not in sys.path:
    sys.path.insert(0, INFERENCE_DIR)


class _FakeResult:
    def __init__(
        self,
        title="",
        url="",
        published_date=None,
        author=None,
        text=None,
        highlights=None,
        summary=None,
    ):
        self.title = title
        self.url = url
        self.published_date = published_date
        self.author = author
        self.text = text
        self.highlights = highlights
        self.summary = summary


class _FakeResponse:
    def __init__(self, results):
        self.results = results


class _FakeExa:
    """Stands in for ``exa_py.Exa`` and records the kwargs it receives."""

    last_kwargs: dict = {}
    last_query: str = ""
    last_instance: "Optional[_FakeExa]" = None

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers: dict = {}
        _FakeExa.last_instance = self

    def search_and_contents(self, query, **kwargs):
        _FakeExa.last_query = query
        _FakeExa.last_kwargs = kwargs
        return _FakeResponse(_FakeExa.next_results)


_FakeExa.next_results = []


def _patch_exa(results):
    """Install a fake ``exa_py`` module so ``from exa_py import Exa`` returns _FakeExa."""
    _FakeExa.next_results = results
    fake_module = mock.MagicMock()
    fake_module.Exa = _FakeExa
    return mock.patch.dict(sys.modules, {"exa_py": fake_module})


class ExaParsingTests(unittest.TestCase):
    def setUp(self):
        os.environ["EXA_API_KEY"] = "test-key"

    def test_search_parses_results_and_sets_integration_header(self):
        results = [
            _FakeResult(
                title="Example",
                url="https://example.com/a",
                published_date="2026-04-01",
                highlights=["Hello world", "More context"],
            ),
            _FakeResult(
                title="Second",
                url="https://example.com/b",
                summary="A short summary.",
            ),
        ]
        with _patch_exa(results):
            from tool_exa import search_with_exa

            output = search_with_exa("python testing")

        self.assertIn("python testing", output)
        self.assertIn("Example", output)
        self.assertIn("https://example.com/a", output)
        self.assertIn("Hello world ... More context", output)
        self.assertIn("A short summary.", output)
        self.assertIn("Date published: 2026-04-01", output)
        self.assertEqual(_FakeExa.last_query, "python testing")
        self.assertEqual(_FakeExa.last_kwargs.get("type"), "auto")
        self.assertIn("highlights", _FakeExa.last_kwargs)
        self.assertIn("text", _FakeExa.last_kwargs)
        self.assertIsNotNone(_FakeExa.last_instance)
        self.assertEqual(
            _FakeExa.last_instance.headers.get("x-exa-integration"),
            "deepresearch",
        )

    def test_snippet_falls_back_through_highlights_summary_text(self):
        from tool_exa import ExaResult

        only_highlights = ExaResult(title="t", url="u", highlights=["h1", "h2"])
        only_summary = ExaResult(title="t", url="u", summary="s")
        only_text = ExaResult(title="t", url="u", text="t" * 600)
        empty = ExaResult(title="t", url="u")

        self.assertEqual(only_highlights.snippet(), "h1 ... h2")
        self.assertEqual(only_summary.snippet(), "s")
        self.assertTrue(only_text.snippet().endswith("..."))
        self.assertLessEqual(len(only_text.snippet()), 504)
        self.assertEqual(empty.snippet(), "")

    def test_scholar_uses_research_paper_category(self):
        results = [_FakeResult(title="Paper", url="https://arxiv.org/x", summary="S")]
        with _patch_exa(results):
            from tool_exa import scholar_with_exa

            output = scholar_with_exa("transformer scaling laws")

        self.assertIn("Scholar Results", output)
        self.assertIn("Paper", output)
        self.assertEqual(_FakeExa.last_kwargs.get("category"), "research paper")

    def test_no_results_returns_friendly_message(self):
        with _patch_exa([]):
            from tool_exa import search_with_exa

            output = search_with_exa("zzz nothing matches")

        self.assertIn("No results found", output)


class ExaDisabledTests(unittest.TestCase):
    def test_missing_api_key_returns_error_string(self):
        os.environ.pop("EXA_API_KEY", None)
        with _patch_exa([]):
            from tool_exa import search_with_exa

            output = search_with_exa("anything")

        self.assertIn("EXA_API_KEY is not set", output)

if __name__ == "__main__":
    unittest.main()
