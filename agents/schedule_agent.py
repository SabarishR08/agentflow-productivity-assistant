from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import and_, select

from db.database import SessionLocal, Task


@dataclass
class ScheduleResult:
    action: str
    success: bool
    message: str
    payload: dict | None = None


def get_upcoming_schedule(limit: int = 20) -> dict:
    """
    Basic schedule view backed by task due_date values.
    Keeps the project lightweight while still demonstrating schedule support.
    """
    with SessionLocal() as session:
        query = (
            select(Task)
            .where(and_(Task.due_date.is_not(None), Task.status != "completed"))
            .order_by(Task.id.desc())
            .limit(limit)
        )
        tasks = session.execute(query).scalars().all()

    payload = [
        {"id": t.id, "title": t.title, "status": t.status, "due_date": t.due_date}
        for t in tasks
    ]

    return asdict(
        ScheduleResult(
            action="get_upcoming_schedule",
            success=True,
            message=f"Fetched {len(payload)} scheduled item(s).",
            payload={"schedule": payload},
        )
    )
