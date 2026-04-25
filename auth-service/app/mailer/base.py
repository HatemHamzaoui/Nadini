"""Mailer-Interface."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
    enable_async=False,
)


class Mailer(Protocol):
    async def send_magic_link(
        self,
        to: str,
        ui_language: str,
        link: str,
    ) -> None: ...


def render_magic_link_email(ui_language: str, link: str) -> tuple[str, str, str]:
    """Gibt (subject, html_body, text_body) zurück.

    Falls keine Sprachvariante existiert, fällt auf 'en' zurück.
    """
    lang = ui_language if (TEMPLATE_DIR / f"magic_link_{ui_language}.html").exists() else "en"
    html_tmpl = _env.get_template(f"magic_link_{lang}.html")
    text_tmpl = _env.get_template(f"magic_link_{lang}.txt")
    subject_tmpl = _env.get_template(f"magic_link_{lang}.subject.txt")
    return (
        subject_tmpl.render().strip(),
        html_tmpl.render(link=link),
        text_tmpl.render(link=link),
    )
