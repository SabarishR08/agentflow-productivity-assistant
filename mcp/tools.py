from __future__ import annotations

from typing import Any

import httpx


class MCPClient:
    """
    Lightweight MCP-style adapter.
    In production, replace this with an actual MCP client/server transport.
    """

    async def fetch_external_info(self, query: str) -> dict[str, Any]:
        if not query.strip():
            return {"source": "none", "result": "No query provided."}

        # Public API call used as an external tool integration example.
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": 3}

        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        top = [
            {
                "name": item.get("full_name"),
                "stars": item.get("stargazers_count"),
                "url": item.get("html_url"),
            }
            for item in items
        ]
        return {"source": "github_search", "result": top}
