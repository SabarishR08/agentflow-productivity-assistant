from __future__ import annotations

from datetime import datetime
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
                "response": "I couldn't complete that - query is empty.",
                "steps": [],
                "intent": [],
                "planner_reasoning": "No query provided.",
            }

        route = self.router.route(query)
        steps: list[dict[str, Any]] = []

        for action in route.actions:
            tool = str(action.get("tool", "")).strip()
            params = action.get("params") if isinstance(action.get("params"), dict) else {}

            try:
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
                else:
                    steps.append(
                        {
                            "action": tool or "unknown",
                            "success": False,
                            "message": f"Unsupported tool requested: {tool or 'unknown'}",
                            "payload": None,
                        }
                    )
            except Exception as exc:
                steps.append(
                    {
                        "action": tool or "unknown",
                        "success": False,
                        "message": f"{tool or 'tool'} failed: {exc}",
                        "payload": None,
                    }
                )

        if not steps:
            return {
                "success": False,
                "result": (
                    "Intent not recognized. Try: add task, list tasks, complete task <id>, "
                    "save note, summarize notes, calendar events, search <topic>."
                ),
                "response": "I couldn't complete that - I couldn't determine which action to run.",
                "steps": [],
                "intent": [intent.value for intent in route.intents],
                "planner_reasoning": route.reasoning,
            }

        final_result = self._compose_result(steps)
        summary_response = self._build_natural_response(steps)
        succeeded_any = any(step.get("success", False) for step in steps)
        return {
            "success": succeeded_any,
            "result": final_result,
            "response": summary_response,
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

    @staticmethod
    def _format_event_date(event_payload: dict[str, Any] | None) -> str | None:
        if not isinstance(event_payload, dict):
            return None

        event = event_payload.get("event") if isinstance(event_payload.get("event"), dict) else event_payload
        start = event.get("start") if isinstance(event, dict) else None
        if not isinstance(start, str) or not start.strip():
            return None

        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            return dt.strftime("%b %d")
        except ValueError:
            return None

    def _build_natural_response(self, steps: list[dict[str, Any]]) -> str:
        success_steps = [step for step in steps if step.get("success")]
        failed_steps = [step for step in steps if not step.get("success")]

        add_task_step = next((step for step in success_steps if step.get("action") == "add_task"), None)
        create_event_step = next(
            (step for step in success_steps if step.get("action") == "create_calendar_event"),
            None,
        )
        list_task_step = next((step for step in success_steps if step.get("action") == "list_tasks"), None)

        if add_task_step and create_event_step:
            task_name = (
                str(add_task_step.get("payload", {}).get("title", "")).strip()
                if isinstance(add_task_step.get("payload"), dict)
                else "task"
            )
            event_payload = create_event_step.get("payload")
            event = event_payload.get("event") if isinstance(event_payload, dict) else {}
            event_title = str(event.get("title", "event")).strip() or "event"
            event_date = self._format_event_date(event_payload)
            date_text = f" on {event_date}" if event_date else ""
            return f"Created task '{task_name}' and scheduled '{event_title}'{date_text}."

        if list_task_step:
            tasks_payload = list_task_step.get("payload", {})
            tasks = tasks_payload.get("tasks") if isinstance(tasks_payload, dict) else []
            if isinstance(tasks, list) and tasks:
                titles = [str(task.get("title", "")).strip() for task in tasks if isinstance(task, dict)]
                titles = [title for title in titles if title]
                if titles:
                    return "Here are your tasks: " + "; ".join(titles)
            return "Here are your tasks: no tasks found."

        if success_steps:
            fragments = [
                str(step.get("message", "")).strip().rstrip(".")
                for step in success_steps
                if str(step.get("message", "")).strip()
            ]
            if fragments:
                joined = "; ".join(fragments)
                if failed_steps:
                    return f"Completed: {joined}. Some steps failed."
                return f"Completed: {joined}."

        if failed_steps:
            reason = "; ".join(
                str(step.get("message", "")).strip()
                for step in failed_steps
                if str(step.get("message", "")).strip()
            )
            return f"I couldn't complete that - {reason or 'unknown error'}"

        return "I couldn't complete that - no actions were executed."
