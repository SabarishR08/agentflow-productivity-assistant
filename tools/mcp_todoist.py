from __future__ import annotations

import os
from typing import Any

import httpx


class TodoistMCPClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("MCP_TODOIST_URL", "").rstrip("/")
        self.auth_token = os.getenv("MCP_TODOIST_TOKEN", "").strip()

    async def create_task(self, title: str, due_date: str | None = None) -> dict[str, Any]:
        payload = {"title": title, "due_date": due_date}
        if not self.base_url:
            return {
                "provider": "todoist-mcp",
                "status": "simulated",
                "task": {"id": None, "title": title, "due_date": due_date},
            }

        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self.base_url}/tasks", json=payload, headers=headers)
            response.raise_for_status()
            return {
                "provider": "todoist-mcp",
                "status": "ok",
                "task": response.json(),
            }
