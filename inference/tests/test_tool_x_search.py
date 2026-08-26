import unittest

import requests

from tool_x_search import XQUIK_SEARCH_URL, XSearch


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.responses.pop(0)


class XSearchTest(unittest.TestCase):
    def test_missing_key_disables_tool_without_request(self):
        session = FakeSession()
        tool = XSearch({"api_key": "", "session": session})

        result = tool.call({"query": ["open source agents"]})

        self.assertIn("XQUIK_API_KEY is not configured", result)
        self.assertEqual(session.calls, [])

    def test_request_uses_published_contract_and_formats_posts(self):
        session = FakeSession(
            [
                FakeResponse(
                    payload={
                        "tweets": [
                            {
                                "id": "2033891852621840387",
                                "text": "Agent release notes\nwith details",
                                "createdAt": "2026-08-26T12:00:00.000Z",
                                "likeCount": 12,
                                "replyCount": 3,
                                "author": {
                                    "username": "researcher",
                                    "name": "Researcher",
                                },
                            }
                        ],
                        "has_next_page": False,
                        "next_cursor": "",
                    }
                )
            ]
        )
        tool = XSearch({"api_key": "xq_test_key", "session": session})

        result = tool.call(
            {"query": ["agent releases"], "limit": 7, "query_type": "Top"}
        )

        self.assertIn("untrusted source material", result)
        self.assertIn("https://x.com/researcher/status/2033891852621840387", result)
        self.assertIn("Agent release notes with details", result)
        self.assertIn("likes: 12", result)
        self.assertEqual(
            session.calls,
            [
                (
                    XQUIK_SEARCH_URL,
                    {
                        "headers": {"x-api-key": "xq_test_key"},
                        "params": {
                            "q": "agent releases",
                            "limit": 7,
                            "queryType": "Top",
                        },
                        "timeout": (5, 30),
                    },
                )
            ],
        )

    def test_batch_search_preserves_query_boundaries(self):
        session = FakeSession(
            [FakeResponse(payload={"tweets": []}), FakeResponse(payload={"tweets": []})]
        )
        tool = XSearch({"api_key": "xq_test_key", "session": session})

        result = tool.call({"query": ["first", "second"]})

        self.assertIn('An X search for "first" found no posts.', result)
        self.assertIn('An X search for "second" found no posts.', result)
        self.assertEqual(len(session.calls), 2)

    def test_http_errors_do_not_expose_response_or_key(self):
        secret = "xq_secret_value"
        session = FakeSession(
            [FakeResponse(status_code=401, payload={"error": secret})]
        )
        tool = XSearch({"api_key": secret, "session": session})

        result = tool.call({"query": ["agents"]})

        self.assertIn("HTTP 401", result)
        self.assertIn("Check XQUIK_API_KEY", result)
        self.assertNotIn(secret, result)

    def test_timeout_returns_retryable_error(self):
        tool = XSearch(
            {"api_key": "xq_test_key", "session": FakeSession(error=requests.Timeout())}
        )

        result = tool.call({"query": ["agents"]})

        self.assertIn("timed out", result)

    def test_invalid_json_and_shape_return_contract_errors(self):
        session = FakeSession(
            [
                FakeResponse(payload=ValueError("bad json")),
                FakeResponse(payload={"tweets": {}}),
            ]
        )
        tool = XSearch({"api_key": "xq_test_key", "session": session})

        invalid_json = tool.call({"query": ["first"]})
        invalid_shape = tool.call({"query": ["second"]})

        self.assertIn("invalid JSON", invalid_json)
        self.assertIn("invalid response", invalid_shape)

    def test_schema_bounds_queries_and_limits(self):
        tool = XSearch({"api_key": "xq_test_key", "session": FakeSession()})

        too_many_queries = tool.call({"query": ["a", "b", "c", "d", "e", "f"]})
        excessive_limit = tool.call({"query": ["agents"], "limit": 21})
        blank_query = tool.call({"query": ["   "]})

        self.assertIn("Invalid request", too_many_queries)
        self.assertIn("Invalid request", excessive_limit)
        self.assertIn("cannot be blank", blank_query)


if __name__ == "__main__":
    unittest.main()
