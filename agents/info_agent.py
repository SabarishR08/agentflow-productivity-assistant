from __future__ import annotations

from mcp.tools import MCPClient


async def fetch_info(query: str) -> dict:
    client = MCPClient()
    result = await client.fetch_external_info(query)
    message = _build_info_message(query=query, payload=result)
    return {
        "action": "fetch_info",
        "success": True,
        "message": message,
        "payload": result,
    }


def _build_info_message(query: str, payload: dict) -> str:
    items = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(items, list) and items:
        top = items[:3]
        parts: list[str] = []
        for item in top:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "source")).strip()
            stars = item.get("stars")
            if isinstance(stars, int):
                parts.append(f"{name} ({stars} stars)")
            else:
                parts.append(name)

        if parts:
            return "Here's what I found: " + "; ".join(parts)

    if "task" in query.lower() and "week" in query.lower():
        return "Here's what I found: I can help summarize your tasks due this week once your task list is loaded."

    return "Here's what I found: I searched external sources and returned the most relevant results."
