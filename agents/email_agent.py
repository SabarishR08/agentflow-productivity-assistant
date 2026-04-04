from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import Any


class EmailAgent:
    def __init__(self) -> None:
        self.gmail_user = os.getenv("GMAIL_USER", "sabarish.edu2024@gmail.com").strip()
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    async def send_reminder(self, to: str, subject: str, body: str) -> dict[str, Any]:
        recipient = to.strip() or self.gmail_user
        if not recipient:
            return {
                "action": "send_reminder_email",
                "success": False,
                "message": "Reminder email skipped: no recipient configured.",
                "payload": None,
            }

        if not self.gmail_app_password:
            return {
                "action": "send_reminder_email",
                "success": False,
                "message": "Reminder email failed: GMAIL_APP_PASSWORD is not configured.",
                "payload": {"to": recipient},
            }

        try:
            await self._send_via_smtp(recipient=recipient, subject=subject, body=body)
            return {
                "action": "send_reminder_email",
                "success": True,
                "message": f"Reminder email sent to {recipient}",
                "payload": {"to": recipient},
            }
        except Exception as exc:
            return {
                "action": "send_reminder_email",
                "success": False,
                "message": f"Reminder email failed for {recipient}: {exc}",
                "payload": {"to": recipient},
            }

    async def _send_via_smtp(self, recipient: str, subject: str, body: str) -> None:
        message = MIMEText(body.strip())
        message["Subject"] = f"AgentFlow Reminder: {subject.strip()}"
        message["From"] = self.gmail_user
        message["To"] = recipient

        def _send() -> None:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.gmail_user, self.gmail_app_password)
                server.send_message(message)

        import asyncio

        await asyncio.to_thread(_send)
