from __future__ import annotations

import os
from typing import Any

import httpx


class TodoistMCPClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("MCP_TODOIST_URL", "").rstrip("/")
        self.auth_token = (
            os.getenv("MCP_TODOIST_TOKEN", "").strip()
            or os.getenv("TODOIST_API_TOKEN", "").strip()
        )

    async def create_task(self, title: str, due_date: str | None = None) -> dict[str, Any]:
        payload = {"content": title}
        if due_date:
            payload["due_string"] = due_date

        # When MCP_TODOIST_URL is not configured but a Todoist token exists,
        # call Todoist's current API base directly.
        if not self.base_url and self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post("https://api.todoist.com/api/v1/tasks", json=payload, headers=headers)
                response.raise_for_status()
                return {
                    "provider": "todoist-api-v1",
                    "status": "ok",
                    "task": response.json(),
                }

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
