from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from sqlalchemy import select

from db.database import SessionLocal, Task
from tools.mcp_todoist import TodoistMCPClient


@dataclass
class TaskResult:
    action: str
    success: bool
    message: str
    payload: Optional[dict] = None


class TaskAgent:
    def __init__(self) -> None:
        self.todoist_client = TodoistMCPClient()

    async def create_task(self, title: str, due_date: Optional[str] = None) -> dict:
        local_result = add_task(title=title, due_date=due_date)
        if not local_result.get("success"):
            return local_result

        remote_result = await self.todoist_client.create_task(title=title, due_date=due_date)
        payload = local_result.get("payload", {})
        payload["todoist"] = remote_result
        local_result["payload"] = payload
        return local_result

    async def invoke(self, tool: str, params: dict) -> dict:
        if tool == "add_task":
            return await self.create_task(
                title=str(params.get("title", "")).strip(),
                due_date=params.get("due_date"),
            )
        if tool == "list_tasks":
            return list_tasks(status=params.get("status"))
        if tool == "complete_task":
            task_id = params.get("task_id")
            if not isinstance(task_id, int):
                return asdict(
                    TaskResult(
                        action="complete_task",
                        success=False,
                        message="task_id must be an integer.",
                    )
                )
            return complete_task(task_id)

        return asdict(
            TaskResult(
                action=tool,
                success=False,
                message=f"Unsupported task tool: {tool}",
            )
        )


def add_task(title: str, due_date: Optional[str] = None) -> dict:
    cleaned_title = title.strip()
    if not cleaned_title:
        return asdict(
            TaskResult(
                action="add_task",
                success=False,
                message="Task title cannot be empty.",
            )
        )

    with SessionLocal() as session:
        task = Task(title=cleaned_title, status="pending", due_date=due_date)
        session.add(task)
        session.commit()
        session.refresh(task)

    result = TaskResult(
        action="add_task",
        success=True,
        message=f"Task created: {task.title}",
        payload={
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
        },
    )
    return asdict(result)


def list_tasks(status: Optional[str] = None) -> dict:
    with SessionLocal() as session:
        query = select(Task).order_by(Task.id.desc())
        if status:
            query = query.where(Task.status == status)
        tasks = session.execute(query).scalars().all()

    payload = [
        {"id": t.id, "title": t.title, "status": t.status, "due_date": t.due_date}
        for t in tasks
    ]
    result = TaskResult(
        action="list_tasks",
        success=True,
        message=f"Fetched {len(payload)} task(s).",
        payload={"tasks": payload},
    )
    return asdict(result)


def complete_task(task_id: int) -> dict:
    with SessionLocal() as session:
        task = session.get(Task, task_id)
        if not task:
            result = TaskResult(
                action="complete_task",
                success=False,
                message=f"Task with id={task_id} not found.",
            )
            return asdict(result)

        task.status = "completed"
        session.commit()

    result = TaskResult(
        action="complete_task",
        success=True,
        message=f"Task {task_id} marked completed.",
    )
    return asdict(result)
