"""Konsolen-Mailer: schreibt die E-Mail in den Log statt sie zu versenden.

Nützlich für lokale Tests ohne Resend-API-Key. Token kann aus dem Log
extrahiert werden.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.mailer.base import render_magic_link_email

log = get_logger(__name__)


class ConsoleMailer:
    def __init__(self, from_email: str, from_name: str) -> None:
        self._from = f"{from_name} <{from_email}>"

    async def send_magic_link(self, to: str, ui_language: str, link: str) -> None:
        subject, _html, text_body = render_magic_link_email(ui_language, link)
        log.warning(
            "magic_link_email_console",
            to=to,
            from_=self._from,
            subject=subject,
            link=link,
            text_body=text_body,
        )
