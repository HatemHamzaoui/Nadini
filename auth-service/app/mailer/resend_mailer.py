"""Resend-API-Mailer.

Doku: https://resend.com/docs/api-reference/emails/send-email
"""
from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.domain.errors import MailerError
from app.mailer.base import render_magic_link_email

log = get_logger(__name__)


class ResendMailer:
    API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        api_key: str,
        from_email: str,
        from_name: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_key:
            raise ValueError("RESEND_API_KEY ist leer.")
        self._api_key = api_key
        self._from = f"{from_name} <{from_email}>"
        self._timeout = timeout_seconds

    async def send_magic_link(self, to: str, ui_language: str, link: str) -> None:
        subject, html_body, text_body = render_magic_link_email(ui_language, link)
        payload = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "headers": {
                "X-Entity-Ref-ID": "magic-link",
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self.API_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            log.error("resend_request_failed", error=str(exc))
            raise MailerError(f"Resend Request fehlgeschlagen: {exc}") from exc

        if resp.status_code >= 400:
            log.error(
                "resend_response_error",
                status=resp.status_code,
                body=resp.text[:500],
            )
            raise MailerError(f"Resend lieferte HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        log.info("magic_link_email_sent", to=to, resend_id=data.get("id"))
