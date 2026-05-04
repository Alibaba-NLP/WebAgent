"""Exa search backend.

Provides Exa-powered web search and Exa-powered scholar search. The implementations
return strings with the same numbered-snippet format produced by the Serper backends
in ``tool_search.py`` and ``tool_scholar.py`` so the agent prompt format is unchanged.
"""

import os
from dataclasses import dataclass
from typing import Any, List, Optional


_EXA_INTEGRATION_HEADER = "deepresearch"


@dataclass
class ExaResult:
    title: str
    url: str
    published_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None
    highlights: Optional[List[str]] = None
    summary: Optional[str] = None

    @classmethod
    def from_sdk(cls, item: Any) -> "ExaResult":
        get = lambda key: getattr(item, key, None) if not isinstance(item, dict) else item.get(key)
        highlights = get("highlights")
        if highlights is not None and not isinstance(highlights, list):
            highlights = list(highlights)
        return cls(
            title=get("title") or "",
            url=get("url") or "",
            published_date=get("published_date") or get("publishedDate"),
            author=get("author"),
            text=get("text"),
            highlights=highlights,
            summary=get("summary"),
        )

    def snippet(self) -> str:
        if self.highlights:
            return " ... ".join(h.strip() for h in self.highlights if h)
        if self.summary:
            return self.summary.strip()
        if self.text:
            text = self.text.strip()
            if len(text) > 500:
                text = text[:500].rstrip() + "..."
            return text
        return ""


def _build_client():
    from exa_py import Exa

    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY is not set")
    client = Exa(api_key=api_key)
    try:
        client.headers["x-exa-integration"] = _EXA_INTEGRATION_HEADER
    except AttributeError:
        pass
    return client


def _run_search(
    query: str,
    num_results: int,
    category: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
) -> List[ExaResult]:
    client = _build_client()

    kwargs: dict = {
        "num_results": num_results,
        "type": "auto",
        "highlights": {"num_sentences": 3},
        "text": {"max_characters": 500},
    }
    if category:
        kwargs["category"] = category
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains
    if start_published_date:
        kwargs["start_published_date"] = start_published_date
    if end_published_date:
        kwargs["end_published_date"] = end_published_date

    last_err: Optional[Exception] = None
    for attempt in range(5):
        try:
            response = client.search_and_contents(query, **kwargs)
            raw_results = getattr(response, "results", None) or []
            return [ExaResult.from_sdk(r) for r in raw_results]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Exa search failed after 5 attempts: {last_err}")


def _format_block(query: str, results: List[ExaResult], header: str, label: str) -> str:
    if not results:
        return f"No results found for '{query}'. Try with a more general query."

    snippets: List[str] = []
    for idx, r in enumerate(results, start=1):
        date_published = f"\nDate published: {r.published_date}" if r.published_date else ""
        author_line = f"\nSource: {r.author}" if r.author else ""
        snippet = r.snippet()
        snippet_block = f"\n{snippet}" if snippet else ""
        title = r.title or r.url
        snippets.append(f"{idx}. [{title}]({r.url}){date_published}{author_line}{snippet_block}")

    return f"{header} for '{query}' found {len(snippets)} results:\n\n## {label}\n" + "\n\n".join(snippets)


def search_with_exa(
    query: str,
    num_results: int = 10,
    category: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
) -> str:
    try:
        results = _run_search(
            query,
            num_results=num_results,
            category=category,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            start_published_date=start_published_date,
            end_published_date=end_published_date,
        )
    except RuntimeError as e:
        return f"[Exa search] {e}"
    except Exception as e:
        return f"[Exa search] Unexpected error: {e}"
    return _format_block(query, results, header="A web search", label="Web Results")


def scholar_with_exa(query: str, num_results: int = 10) -> str:
    try:
        results = _run_search(query, num_results=num_results, category="research paper")
    except RuntimeError as e:
        return f"[Exa scholar] {e}"
    except Exception as e:
        return f"[Exa scholar] Unexpected error: {e}"
    return _format_block(query, results, header="A research-paper search", label="Scholar Results")
