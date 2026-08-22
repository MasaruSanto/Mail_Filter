# Web検索クライアント（Tavily API）

import os


class WebSearchClient:
  """Tavily検索APIのラッパー。TAVILY_API_KEY が必要。"""

  def __init__(self, api_key: str | None = None, max_results: int = 6):
    self._api_key = api_key or os.environ.get("TAVILY_API_KEY")
    self._max_results = max_results

  def search(self, query: str, max_results: int | None = None) -> list[dict]:
    if not self._api_key:
      raise RuntimeError(
        "TAVILY_API_KEY が未設定です。https://tavily.com/ でAPIキーを取得し、"
        "環境変数 TAVILY_API_KEY に設定してください。"
      )
    from tavily import TavilyClient

    client = TavilyClient(api_key=self._api_key)
    response = client.search(
      query=query,
      max_results=max_results or self._max_results,
      search_depth="advanced",
    )
    return [
      {
        "url": r.get("url", ""),
        "title": r.get("title", ""),
        "content": r.get("content", ""),
        "published_at": r.get("published_date"),
      }
      for r in response.get("results", [])
      if r.get("content")
    ]
