from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from google import genai


@dataclass
class Plan:
    actions: list[dict[str, Any]]
    reasoning: str


class GeminiIntentPlanner:
    """
    Primary reasoning layer for orchestration.
    Produces a compact action plan that the orchestrator executes.
    """

    def __init__(self) -> None:
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    def plan(self, query: str) -> Plan:
        if not self.api_key:
            return self._fallback_plan(query, "GOOGLE_API_KEY is not set; using deterministic routing.")

        prompt = (
            "You are an orchestration planner for a productivity assistant. "
            "Return strictly valid JSON with keys: actions (array), reasoning (string). "
            "Each action item must use one of tools: add_task, list_tasks, complete_task, summarize_tasks, "
            "save_note, list_notes, summarize_notes, create_calendar_event, list_calendar_events, "
            "get_upcoming_schedule, fetch_info. "
            "If parameters are needed, include params object. "
            "\n\nUser query: "
            f"{query}"
        )

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(model=self.model, contents=prompt)
            text = (response.text or "").strip()
            parsed = self._safe_json(text)
            if not parsed:
                return self._fallback_plan(query, "Gemini output was not valid JSON; fallback routing used.")

            actions = parsed.get("actions") if isinstance(parsed.get("actions"), list) else []
            reasoning = str(parsed.get("reasoning", "Planned by Gemini."))
            if not actions:
                return self._fallback_plan(query, "Gemini plan was empty; fallback routing used.")

            return Plan(actions=actions, reasoning=reasoning)
        except Exception as exc:
            return self._fallback_plan(query, f"Gemini planning failed: {exc}. Fallback routing used.")

    @staticmethod
    def _safe_json(text: str) -> dict[str, Any] | None:
        if not text:
            return None

        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(stripped)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _fallback_plan(query: str, reason: str) -> Plan:
        q = query.lower().strip()
        actions: list[dict[str, Any]] = []

        if ("task" in q and "calendar" in q) or ("task" in q and "schedule" in q):
            actions = [
                {"tool": "add_task", "params": {"title": query}},
                {
                    "tool": "create_calendar_event",
                    "params": {
                        "title": query,
                        "start_hint": "tomorrow" if "tomorrow" in q else "today",
                    },
                },
            ]
        elif "pending" in q and "task" in q and "summar" in q:
            actions = [
                {"tool": "list_tasks", "params": {"status": "pending"}},
                {"tool": "summarize_tasks"},
            ]
        elif (("add" in q and "task" in q) or "create task" in q or q.startswith("task:")):
            actions = [{"tool": "add_task", "params": {"title": query}}]
        elif "complete task" in q:
            actions = [{"tool": "complete_task", "params": {"task_id": _extract_int(q)}}]
        elif "list" in q and "task" in q:
            actions = [{"tool": "list_tasks", "params": {"status": "pending" if "pending" in q else None}}]
        elif "save note" in q or q.startswith("note:"):
            actions = [{"tool": "save_note", "params": {"content": query}}]
        elif "summar" in q and "note" in q:
            actions = [{"tool": "summarize_notes"}]
        elif "list" in q and "note" in q:
            actions = [{"tool": "list_notes"}]
        elif ("schedule" in q or "calendar" in q or "event" in q) and (
            "create" in q or "book" in q or "block" in q
        ):
            actions = [
                {
                    "tool": "create_calendar_event",
                    "params": {
                        "title": query,
                        "start_hint": "tomorrow" if "tomorrow" in q else "today",
                    },
                }
            ]
        elif "schedule" in q or "calendar" in q or "event" in q:
            actions = [{"tool": "list_calendar_events"}]
        elif "search" in q or "latest" in q or "info" in q:
            actions = [{"tool": "fetch_info", "params": {"query": query}}]

        return Plan(actions=actions, reasoning=reason)


def _extract_int(text: str) -> int | None:
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    return int(digits[0]) if digits else None


def plan_to_dict(plan: Plan) -> dict[str, Any]:
    return asdict(plan)
