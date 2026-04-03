from __future__ import annotations

import asyncio

from sqlalchemy import delete

from db.database import Note, SessionLocal, Task, init_db
from orchestrator.agent import OrchestratorAgent


def _reset_db() -> None:
    init_db()
    with SessionLocal() as session:
        session.execute(delete(Task))
        session.execute(delete(Note))
        session.commit()


def test_workflow_add_task() -> None:
    _reset_db()
    agent = OrchestratorAgent()
    result = asyncio.run(agent.run("Add a task: finish assignment tomorrow"))

    assert result["success"] is True
    assert "add_task" in result["result"]
    assert "task_management" in result["intent"]


def test_workflow_summarize_notes() -> None:
    _reset_db()
    agent = OrchestratorAgent()
    asyncio.run(agent.run("save note: Team sync at 5 PM"))

    result = asyncio.run(agent.run("Summarize my notes"))
    assert result["success"] is True
    assert "summarize_notes" in result["result"]


def test_workflow_pending_tasks_and_summarize() -> None:
    _reset_db()
    agent = OrchestratorAgent()
    asyncio.run(agent.run("Add a task: Prepare hackathon deck tomorrow"))

    result = asyncio.run(agent.run("What are my pending tasks and summarize them"))
    assert result["success"] is True
    assert "list_tasks" in result["result"]
    assert "summarize_tasks" in result["result"]


def test_workflow_task_plus_calendar_block() -> None:
    _reset_db()
    agent = OrchestratorAgent()

    result = asyncio.run(agent.run("Create a task and schedule a calendar block for deep work tomorrow"))
    assert result["success"] is True
    assert "add_task" in result["result"]
    assert "create_calendar_event" in result["result"]
