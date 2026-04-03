from __future__ import annotations

from typing import Any

from agents.calendar_agent import CalendarAgent
from agents.info_agent import fetch_info
from agents.notes_agent import NotesAgent
from agents.task_agent import TaskAgent
from db.alloydb_client import init_db
from orchestrator.router import IntentRouter


class OrchestratorAgent:
    """
    Primary coordinating agent. Uses simple intent routing for hackathon reliability.
    You can swap this with ADK planner logic while preserving sub-agent contracts.
    """

    def __init__(self) -> None:
        init_db()
        self.router = IntentRouter()
        self.task_agent = TaskAgent()
        self.calendar_agent = CalendarAgent()
        self.notes_agent = NotesAgent()

    async def run(self, query: str) -> dict[str, Any]:
        if not query.strip():
            return {
                "success": False,
                "result": "Query is empty.",
                "steps": [],
                "intent": [],
                "planner_reasoning": "No query provided.",
            }

        route = self.router.route(query)
        steps: list[dict[str, Any]] = []

        for action in route.actions:
            tool = str(action.get("tool", "")).strip()
            params = action.get("params") if isinstance(action.get("params"), dict) else {}

            if tool in {"add_task", "list_tasks", "complete_task"}:
                params = self._normalize_task_params(tool=tool, params=params, query=query)
                steps.append(await self.task_agent.invoke(tool=tool, params=params))
            elif tool in {"save_note", "list_notes", "summarize_notes"}:
                params = self._normalize_note_params(tool=tool, params=params, query=query)
                steps.append(await self.notes_agent.invoke(tool=tool, params=params))
            elif tool in {"create_calendar_event", "list_calendar_events", "get_upcoming_schedule"}:
                params = self._normalize_calendar_params(params=params, query=query)
                steps.append(await self.calendar_agent.invoke(tool=tool, params=params))
            elif tool == "fetch_info":
                info_query = self._normalize_text(params.get("query"), query)
                steps.append(await fetch_info(info_query))
            elif tool == "summarize_tasks":
                tasks_result = next((s for s in steps if s.get("action") == "list_tasks"), None)
                steps.append(self._summarize_tasks(tasks_result))

        if not steps:
            return {
                "success": False,
                "result": (
                    "Intent not recognized. Try: add task, list tasks, complete task <id>, "
                    "save note, summarize notes, calendar events, search <topic>."
                ),
                "steps": [],
                "intent": [intent.value for intent in route.intents],
                "planner_reasoning": route.reasoning,
            }

        final_result = self._compose_result(steps)
        return {
            "success": all(step.get("success", False) for step in steps),
            "result": final_result,
            "steps": steps,
            "intent": [intent.value for intent in route.intents],
            "planner_reasoning": route.reasoning,
        }

    @staticmethod
    def _normalize_text(value: Any, fallback: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if ":" in fallback:
            return fallback.split(":", maxsplit=1)[-1].strip()
        return fallback.strip()

    @staticmethod
    def _extract_due_date_hint(query: str) -> str | None:
        lowered = query.lower()
        if "tomorrow" in lowered:
            return "tomorrow"
        if "today" in lowered:
            return "today"
        return None

    def _normalize_task_params(self, tool: str, params: dict[str, Any], query: str) -> dict[str, Any]:
        normalized = dict(params)
        if tool == "add_task":
            raw_title = self._normalize_text(normalized.get("title"), query)
            normalized["title"] = self._extract_task_title(raw_title)
            normalized.setdefault("due_date", self._extract_due_date_hint(query))
        return normalized

    def _normalize_note_params(self, tool: str, params: dict[str, Any], query: str) -> dict[str, Any]:
        normalized = dict(params)
        if tool == "save_note":
            normalized["content"] = self._normalize_text(normalized.get("content"), query)
        return normalized

    def _normalize_calendar_params(self, params: dict[str, Any], query: str) -> dict[str, Any]:
        normalized = dict(params)
        normalized.setdefault("title", self._normalize_text(normalized.get("title"), query))
        normalized.setdefault("start_hint", self._extract_due_date_hint(query) or "today")
        return normalized

    @staticmethod
    def _extract_task_title(text: str) -> str:
        lowered = text.lower()
        markers = ["add a task:", "add task:", "create task:", "task:"]
        for marker in markers:
            if marker in lowered:
                idx = lowered.index(marker)
                return text[idx + len(marker):].strip() or text.strip()
        return text.strip()

    @staticmethod
    def _summarize_tasks(tasks_result: dict[str, Any] | None) -> dict[str, Any]:
        if not tasks_result:
            return {
                "action": "summarize_tasks",
                "success": False,
                "message": "No task list available to summarize.",
                "payload": {"summary": "No task data available."},
            }

        tasks = tasks_result.get("payload", {}).get("tasks", [])
        lines = [f"- {t['title']} (id={t['id']}, status={t['status']})" for t in tasks]
        summary = "No tasks found." if not lines else "\n".join(lines)
        return {
            "action": "summarize_tasks",
            "success": True,
            "message": "Task summary generated.",
            "payload": {"summary": summary},
        }

    @staticmethod
    def _compose_result(steps: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for step in steps:
            action = step.get("action", "unknown")
            message = step.get("message", "")
            payload = step.get("payload")
            if payload:
                parts.append(f"{action}: {message} | payload={payload}")
            else:
                parts.append(f"{action}: {message}")
        return "\n".join(parts)
