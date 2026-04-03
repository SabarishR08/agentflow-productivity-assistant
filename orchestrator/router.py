from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from orchestrator.planner import GeminiIntentPlanner


class Intent(str, Enum):
    TASK = "task_management"
    CALENDAR = "calendar"
    NOTES = "notes"
    GENERAL = "general_query"


@dataclass
class RouteDecision:
    intents: list[Intent]
    actions: list[dict[str, Any]]
    reasoning: str


_TOOL_INTENT_MAP: dict[str, Intent] = {
    "add_task": Intent.TASK,
    "list_tasks": Intent.TASK,
    "complete_task": Intent.TASK,
    "summarize_tasks": Intent.TASK,
    "create_calendar_event": Intent.CALENDAR,
    "list_calendar_events": Intent.CALENDAR,
    "get_upcoming_schedule": Intent.CALENDAR,
    "save_note": Intent.NOTES,
    "list_notes": Intent.NOTES,
    "summarize_notes": Intent.NOTES,
    "fetch_info": Intent.GENERAL,
}


class IntentRouter:
    def __init__(self) -> None:
        self.planner = GeminiIntentPlanner()

    def route(self, query: str) -> RouteDecision:
        plan = self.planner.plan(query)
        actions = [a for a in plan.actions if isinstance(a, dict)]
        intents = self._intents_from_actions(actions)

        if not actions:
            fallback_actions = self._fallback_actions(query)
            return RouteDecision(
                intents=self._intents_from_actions(fallback_actions),
                actions=fallback_actions,
                reasoning=f"{plan.reasoning} | router fallback",
            )

        return RouteDecision(intents=intents, actions=actions, reasoning=plan.reasoning)

    def _intents_from_actions(self, actions: list[dict[str, Any]]) -> list[Intent]:
        intents: list[Intent] = []
        for action in actions:
            tool = str(action.get("tool", "")).strip()
            intent = _TOOL_INTENT_MAP.get(tool)
            if intent and intent not in intents:
                intents.append(intent)

        return intents or [Intent.GENERAL]

    @staticmethod
    def _fallback_actions(query: str) -> list[dict[str, Any]]:
        q = query.lower()
        actions: list[dict[str, Any]] = []

        if ("task" in q and "calendar" in q) or ("task" in q and "schedule" in q):
            actions.append({"tool": "add_task", "params": {"title": query}})
            actions.append({"tool": "create_calendar_event", "params": {"title": query, "start_hint": "tomorrow" if "tomorrow" in q else "today"}})
            return actions

        if "task" in q and any(word in q for word in ["add", "create"]):
            return [{"tool": "add_task", "params": {"title": query}}]
        if "complete" in q and "task" in q:
            return [{"tool": "complete_task", "params": {"task_id": _extract_int(q)}}]
        if "task" in q and any(word in q for word in ["week", "due", "upcoming"]):
            return [
                {"tool": "list_tasks", "params": {"status": "pending"}},
                {"tool": "summarize_tasks"},
            ]
        if "task" in q and any(word in q for word in ["list", "pending", "show"]):
            return [{"tool": "list_tasks", "params": {"status": "pending" if "pending" in q else None}}]
        if "note" in q and any(word in q for word in ["add", "save", "store"]):
            return [{"tool": "save_note", "params": {"content": query}}]
        if "note" in q and "summar" in q:
            return [{"tool": "summarize_notes"}]
        if "note" in q and any(word in q for word in ["list", "show"]):
            return [{"tool": "list_notes"}]
        if any(word in q for word in ["calendar", "schedule", "event"]):
            if any(word in q for word in ["create", "book", "block"]):
                return [{"tool": "create_calendar_event", "params": {"title": query, "start_hint": "tomorrow" if "tomorrow" in q else "today"}}]
            return [{"tool": "list_calendar_events"}]

        return [{"tool": "fetch_info", "params": {"query": query}}]


def _extract_int(text: str) -> int | None:
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    return int(digits[0]) if digits else None
