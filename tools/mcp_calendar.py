from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import google.auth
import httpx
from google.oauth2 import service_account


class CalendarMCPClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("MCP_CALENDAR_URL", "").rstrip("/")
        self.auth_token = os.getenv("MCP_CALENDAR_TOKEN", "").strip()
        self.google_credentials = self._load_calendar_credentials()

    @staticmethod
    def _load_calendar_credentials() -> service_account.Credentials | None:
        raw = os.environ.get("GOOGLE_CALENDAR_KEY", "").strip()
        if not raw:
            return None

        try:
            key_info = json.loads(raw)
            if not isinstance(key_info, dict) or not key_info:
                return None
            return service_account.Credentials.from_service_account_info(key_info)
        except Exception:
            return None

    async def create_event(self, title: str, start_hint: str | None = None) -> dict[str, Any]:
        start_time = self._resolve_start(start_hint)
        end_time = start_time + timedelta(hours=1)
        payload = {
            "title": title,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }

        if not self.base_url:
            return {
                "provider": "calendar-mcp",
                "status": "simulated",
                "event": payload,
            }

        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self.base_url}/events", json=payload, headers=headers)
            response.raise_for_status()
            return {
                "provider": "calendar-mcp",
                "status": "ok",
                "event": response.json(),
            }

    async def list_events(self, days_ahead: int = 7) -> dict[str, Any]:
        if not self.base_url:
            now = datetime.now(UTC)
            sample_events = [
                {
                    "title": "Sample focus block",
                    "start": (now + timedelta(days=1)).isoformat(),
                    "end": (now + timedelta(days=1, hours=1)).isoformat(),
                }
            ]
            return {
                "provider": "calendar-mcp",
                "status": "simulated",
                "events": sample_events,
            }

        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        params = {"days_ahead": days_ahead}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/events", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            events = data.get("events", data if isinstance(data, list) else [])
            return {
                "provider": "calendar-mcp",
                "status": "ok",
                "events": events,
            }

    @staticmethod
    def _resolve_start(start_hint: str | None) -> datetime:
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        if start_hint and start_hint.lower() == "tomorrow":
            return now + timedelta(days=1, hours=1)
        return now + timedelta(hours=1)
