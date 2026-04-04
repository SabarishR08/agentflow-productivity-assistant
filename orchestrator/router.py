from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from orchestrator.planner import GeminiIntentPlanner


class Intent(str, Enum):
    TASK = "task_management"
    CALENDAR = "calendar"
    NOTES_MANAGEMENT = "notes_management"
    DAILY_BRIEFING = "daily_briefing"
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
    "daily_briefing": Intent.DAILY_BRIEFING,
    "save_note": Intent.NOTES_MANAGEMENT,
    "get_notes": Intent.NOTES_MANAGEMENT,
    "list_notes": Intent.NOTES_MANAGEMENT,
    "summarize_notes": Intent.NOTES_MANAGEMENT,
    "fetch_info": Intent.GENERAL,
}


class IntentRouter:
    def __init__(self) -> None:
        self.planner = GeminiIntentPlanner()

    def route(self, query: str) -> RouteDecision:
        if self._is_daily_briefing_query(query):
            return RouteDecision(
                intents=[Intent.DAILY_BRIEFING],
                actions=[{"tool": "daily_briefing", "params": {}}],
                reasoning="router matched daily briefing keywords",
            )

        plan = self.planner.plan(query)
        actions = [a for a in plan.actions if isinstance(a, dict)]

        if self._is_multi_step_query(query):
            actions = self._ensure_multi_step_actions(actions, query)
            return RouteDecision(
                intents=[Intent.TASK, Intent.CALENDAR],
                actions=actions,
                reasoning=f"{plan.reasoning} | router enforced multi-step task+calendar execution",
            )

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
    def _is_daily_briefing_query(query: str) -> bool:
        q = query.lower()
        keywords = [
            "my day",
            "daily briefing",
            "what's today",
            "what do i have today",
            "morning briefing",
            "today's schedule",
        ]
        return any(keyword in q for keyword in keywords)

    @staticmethod
    def _is_multi_step_query(query: str) -> bool:
        q = query.lower()
        task_keywords = ["task", "todo", "remind me to", "don't forget", "add to my list"]
        calendar_keywords = ["schedule", "meeting", "calendar"]
        day_words = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "tomorrow",
            "today",
            "next",
        ]

        has_task = any(keyword in q for keyword in task_keywords)
        has_calendar_word = any(keyword in q for keyword in calendar_keywords)
        has_time = re.search(r"\bat\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b", q) is not None
        has_day_phrase = re.search(r"\bon\s+([a-z]+\s+)?(" + "|".join(day_words) + r")\b", q) is not None

        has_calendar = has_calendar_word or has_time or has_day_phrase
        return has_task and has_calendar

    @staticmethod
    def _ensure_multi_step_actions(actions: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        normalized = [action for action in actions if isinstance(action, dict)]
        has_task_action = any(str(action.get("tool", "")).strip() in {"add_task", "list_tasks", "complete_task", "summarize_tasks"} for action in normalized)
        has_calendar_action = any(str(action.get("tool", "")).strip() in {"create_calendar_event", "list_calendar_events", "get_upcoming_schedule"} for action in normalized)

        if not has_task_action:
            normalized.append({"tool": "add_task", "params": {"title": query}})
        if not has_calendar_action:
            normalized.append(
                {
                    "tool": "create_calendar_event",
                    "params": {"title": query, "start_hint": "tomorrow" if "tomorrow" in query.lower() else "today"},
                }
            )
        return normalized

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
        if any(phrase in q for phrase in ["save a note", "remember that", "note this", "write down"]):
            return [{"tool": "save_note", "params": {"content": query}}]
        if any(phrase in q for phrase in ["what did i note", "find my note about", "show my notes"]):
            note_query = query
            marker = "about"
            if marker in q:
                note_query = query[q.index(marker) + len(marker):].strip()
            return [{"tool": "get_notes", "params": {"query": note_query}}]
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
