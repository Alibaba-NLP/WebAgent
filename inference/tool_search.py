import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union
import requests
from qwen_agent.tools.base import BaseTool, register_tool
import asyncio
from typing import Dict, List, Optional, Union
import uuid
import http.client
import json

import os


SERPER_KEY=os.environ.get('SERPER_KEY_ID')
EXA_API_KEY=os.environ.get('EXA_API_KEY')
SEARCH_PROVIDER=os.environ.get('SEARCH_PROVIDER') or ('exa' if EXA_API_KEY and not SERPER_KEY else 'serper')


@register_tool("search", allow_overwrite=True)
class Search(BaseTool):
    name = "search"
    description = "Performs batched web searches: supply an array 'query'; the tool retrieves the top 10 results for each query in one call."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Array of query strings. Include multiple complementary search queries in a single call."
            },
        },
        "required": ["query"],
    }

    def __init__(self, cfg: Optional[dict] = None):
        super().__init__(cfg)
    def google_search_with_serp(self, query: str):
        def contains_chinese_basic(text: str) -> bool:
            return any('\u4E00' <= char <= '\u9FFF' for char in text)
        conn = http.client.HTTPSConnection("google.serper.dev")
        if contains_chinese_basic(query):
            payload = json.dumps({
                "q": query,
                "location": "China",
                "gl": "cn",
                "hl": "zh-cn"
            })
            
        else:
            payload = json.dumps({
                "q": query,
                "location": "United States",
                "gl": "us",
                "hl": "en"
            })
        headers = {
                'X-API-KEY': SERPER_KEY,
                'Content-Type': 'application/json'
            }
        
        
        for i in range(5):
            try:
                conn.request("POST", "/search", payload, headers)
                res = conn.getresponse()
                break
            except Exception as e:
                print(e)
                if i == 4:
                    return f"Google search Timeout, return None, Please try again later."
                continue
    
        data = res.read()
        results = json.loads(data.decode("utf-8"))

        try:
            if "organic" not in results:
                raise Exception(f"No results found for query: '{query}'. Use a less specific query.")

            web_snippets = list()
            idx = 0
            if "organic" in results:
                for page in results["organic"]:
                    idx += 1
                    date_published = ""
                    if "date" in page:
                        date_published = "\nDate published: " + page["date"]

                    source = ""
                    if "source" in page:
                        source = "\nSource: " + page["source"]

                    snippet = ""
                    if "snippet" in page:
                        snippet = "\n" + page["snippet"]

                    redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
                    redacted_version = redacted_version.replace("Your browser can't play this video.", "")
                    web_snippets.append(redacted_version)

            content = f"A Google search for '{query}' found {len(web_snippets)} results:\n\n## Web Results\n" + "\n\n".join(web_snippets)
            return content
        except:
            return f"No results found for '{query}'. Try with a more general query."


    
    def exa_search(self, query: str):
        payload = {
            "query": query,
            "type": "auto",
            "numResults": 10,
            "contents": {"highlights": True},
        }
        headers = {
            'x-api-key': EXA_API_KEY,
            'Content-Type': 'application/json',
            'x-exa-integration': 'Alibaba-NLP/DeepResearch-integration',
        }

        results = None
        for i in range(5):
            try:
                response = requests.post(
                    "https://api.exa.ai/search",
                    json=payload,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                results = response.json()
                break
            except Exception as e:
                print(e)
                if i == 4:
                    return f"Exa search Timeout, return None, Please try again later."
                continue

        try:
            web_snippets = list()
            for idx, page in enumerate(results.get("results", []), start=1):
                date_published = ""
                if page.get("publishedDate"):
                    date_published = "\nDate published: " + page["publishedDate"]

                source = ""
                if page.get("author"):
                    source = "\nSource: " + page["author"]

                snippet = ""
                if page.get("highlights"):
                    snippet = "\n" + " ... ".join(page["highlights"])

                web_snippets.append(
                    f"{idx}. [{page.get('title') or page.get('url')}]({page.get('url')}){date_published}{source}\n{snippet}"
                )

            return f"An Exa search for '{query}' found {len(web_snippets)} results:\n\n## Web Results\n" + "\n\n".join(web_snippets)
        except:
            return f"No results found for '{query}'. Try with a more general query."

    def search_with_serp(self, query: str):
        if SEARCH_PROVIDER == 'exa':
            return self.exa_search(query)
        result = self.google_search_with_serp(query)
        return result

    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            query = params["query"]
        except:
            return "[Search] Invalid request format: Input must be a JSON object containing 'query' field"
        
        if isinstance(query, str):
            # 单个查询
            response = self.search_with_serp(query)
        else:
            # 多个查询
            assert isinstance(query, List)
            responses = []
            for q in query:
                responses.append(self.search_with_serp(q))
            response = "\n=======\n".join(responses)
            
        return response

