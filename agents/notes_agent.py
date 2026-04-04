from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Optional

from google import genai
from sqlalchemy import select

from db.database import Note, SessionLocal


@dataclass
class NotesResult:
    action: str
    success: bool
    message: str
    payload: Optional[dict] = None


class NotesAgent:
    def save_note(self, content: str) -> dict:
        return save_note(content=content)

    def get_notes(self, query: str, limit: int = 20) -> dict:
        return get_notes(query=query, limit=limit)

    async def invoke(self, tool: str, params: dict) -> dict:
        if tool == "save_note":
            return self.save_note(content=str(params.get("content", "")))
        if tool == "get_notes":
            return self.get_notes(
                query=str(params.get("query", "")),
                limit=int(params.get("limit", 20)),
            )
        if tool == "list_notes":
            return list_notes(limit=int(params.get("limit", 20)))
        if tool == "summarize_notes":
            return summarize_notes(limit=int(params.get("limit", 20)))

        return asdict(
            NotesResult(
                action=tool,
                success=False,
                message=f"Unsupported notes tool: {tool}",
            )
        )


def save_note(content: str) -> dict:
    with SessionLocal() as session:
        note = Note(content=content.strip())
        session.add(note)
        session.commit()
        session.refresh(note)

    result = NotesResult(
        action="save_note",
        success=True,
        message="Note saved.",
        payload={"id": note.id, "content": note.content},
    )
    return asdict(result)


def list_notes(limit: int = 20) -> dict:
    with SessionLocal() as session:
        notes = session.execute(select(Note).order_by(Note.id.desc()).limit(limit)).scalars().all()

    payload = [{"id": n.id, "content": n.content, "created_at": n.created_at.isoformat()} for n in notes]
    result = NotesResult(
        action="list_notes",
        success=True,
        message=f"Fetched {len(payload)} note(s).",
        payload={"notes": payload},
    )
    return asdict(result)


def get_notes(query: str, limit: int = 20) -> dict:
    cleaned_query = query.strip().lower()
    with SessionLocal() as session:
        stmt = select(Note).order_by(Note.id.desc()).limit(limit)
        notes = session.execute(stmt).scalars().all()

    filtered = notes
    if cleaned_query:
        filtered = [n for n in notes if cleaned_query in (n.content or "").lower()]

    payload = [
        {"id": n.id, "content": n.content, "created_at": n.created_at.isoformat()}
        for n in filtered
    ]
    return asdict(
        NotesResult(
            action="get_notes",
            success=True,
            message=f"Fetched {len(payload)} matching note(s).",
            payload={"notes": payload, "query": query},
        )
    )


def summarize_notes(limit: int = 20) -> dict:
    notes_data = list_notes(limit=limit)
    notes = notes_data.get("payload", {}).get("notes", [])
    if not notes:
        return asdict(
            NotesResult(
                action="summarize_notes",
                success=True,
                message="No notes available to summarize.",
                payload={"summary": "No notes found."},
            )
        )

    joined_text = "\n".join([f"- {n['content']}" for n in notes])
    prompt = (
        "Summarize the following personal productivity notes into short action points:\n\n"
        f"{joined_text}"
    )

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    if not api_key:
        fallback = "Gemini key missing. Fallback summary: " + "; ".join(
            n["content"][:80] for n in notes[:5]
        )
        return asdict(
            NotesResult(
                action="summarize_notes",
                success=True,
                message="Generated fallback summary without Gemini.",
                payload={"summary": fallback},
            )
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    summary = response.text if getattr(response, "text", None) else "No summary generated."

    return asdict(
        NotesResult(
            action="summarize_notes",
            success=True,
            message="Notes summarized with Gemini.",
            payload={"summary": summary},
        )
    )
