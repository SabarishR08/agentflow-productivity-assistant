from __future__ import annotations

from mcp.tools import MCPClient


async def fetch_info(query: str) -> dict:
    client = MCPClient()
    result = await client.fetch_external_info(query)
    return {
        "action": "fetch_info",
        "success": True,
        "message": "Fetched external information using MCP-style adapter.",
        "payload": result,
    }
