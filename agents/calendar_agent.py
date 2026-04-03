from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from tools.mcp_calendar import CalendarMCPClient


@dataclass
class CalendarResult:
    action: str
    success: bool
    message: str
    payload: Optional[dict] = None


class CalendarAgent:
    def __init__(self) -> None:
        self.client = CalendarMCPClient()

    async def create_event(self, title: str, start_hint: str | None = None) -> dict:
        if not title.strip():
            return asdict(
                CalendarResult(
                    action="create_calendar_event",
                    success=False,
                    message="Event title cannot be empty.",
                )
            )

        event = await self.client.create_event(title=title.strip(), start_hint=start_hint)
        return asdict(
            CalendarResult(
                action="create_calendar_event",
                success=True,
                message="Calendar event created.",
                payload=event,
            )
        )

    async def list_events(self, days_ahead: int = 7) -> dict:
        events = await self.client.list_events(days_ahead=days_ahead)
        total = len(events.get("events", [])) if isinstance(events.get("events"), list) else 0
        return asdict(
            CalendarResult(
                action="list_calendar_events",
                success=True,
                message=f"Fetched {total} calendar event(s).",
                payload=events,
            )
        )

    async def invoke(self, tool: str, params: dict) -> dict:
        if tool == "create_calendar_event":
            return await self.create_event(
                title=str(params.get("title", "")).strip(),
                start_hint=params.get("start_hint"),
            )

        if tool in {"list_calendar_events", "get_upcoming_schedule"}:
            days_ahead = int(params.get("days_ahead", 7))
            return await self.list_events(days_ahead=days_ahead)

        return asdict(
            CalendarResult(
                action=tool,
                success=False,
                message=f"Unsupported calendar tool: {tool}",
            )
        )
