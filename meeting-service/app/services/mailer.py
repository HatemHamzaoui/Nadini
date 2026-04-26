"""Meeting-Einladungs-E-Mails — Console oder Resend."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

LANG_NAMES = {
    "de": "Deutsch", "en": "English", "fr": "Français", "es": "Español",
    "it": "Italiano", "ar": "العربية", "zh": "中文", "ja": "日本語",
}


def _format_date(dt: datetime, lang: str = "de") -> str:
    if lang == "en":
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")
    elif lang == "fr":
        return dt.strftime("%d/%m/%Y à %H:%M UTC")
    return dt.strftime("%d.%m.%Y um %H:%M Uhr UTC")


def _build_invite_email(
    meeting_name: str,
    join_url: str,
    source_lang: str,
    target_langs: list[str],
    scheduled_at: datetime | None,
    description: str | None,
    host_name: str,
    ui_lang: str = "de",
) -> tuple[str, str, str]:
    """Returns (subject, html, text) for invitation email."""
    langs_str = ", ".join(LANG_NAMES.get(l, l.upper()) for l in [source_lang] + target_langs)

    if ui_lang == "en":
        subject = f"Meeting Invitation: {meeting_name}"
        greeting = f"{host_name} has invited you to a meeting on Nadini."
        when_label = "When"
        langs_label = "Languages"
        desc_label = "Description"
        btn_text = "Join Meeting"
        footer = "Nadini — Real-time AI interpreting for meetings."
    elif ui_lang == "fr":
        subject = f"Invitation à la réunion : {meeting_name}"
        greeting = f"{host_name} vous invite à une réunion sur Nadini."
        when_label = "Quand"
        langs_label = "Langues"
        desc_label = "Description"
        btn_text = "Rejoindre"
        footer = "Nadini — Interprétation IA en temps réel."
    else:
        subject = f"Meeting-Einladung: {meeting_name}"
        greeting = f"{host_name} lädt Sie zu einem Meeting auf Nadini ein."
        when_label = "Wann"
        langs_label = "Sprachen"
        desc_label = "Beschreibung"
        btn_text = "Meeting beitreten"
        footer = "Nadini — KI-Echtzeit-Dolmetschen für Meetings."

    date_str = _format_date(scheduled_at, ui_lang) if scheduled_at else "—"
    desc_block = f"<p><strong>{desc_label}:</strong> {description}</p>" if description else ""

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{subject}</title></head>
<body style="margin:0;padding:0;background:#f5f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#222">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f6f8;padding:40px 0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,0.05)"><tr><td>
  <h1 style="margin:0 0 8px;font-size:22px;color:#0e4243">{meeting_name}</h1>
  <p style="font-size:15px;line-height:1.5;margin:0 0 20px;color:#444">{greeting}</p>
  <table style="font-size:14px;line-height:1.8;margin:0 0 20px" cellpadding="0" cellspacing="0">
    <tr><td style="color:#888;padding-right:16px">{when_label}</td><td><strong>{date_str}</strong></td></tr>
    <tr><td style="color:#888;padding-right:16px">{langs_label}</td><td>{langs_str}</td></tr>
  </table>
  {desc_block}
  <p style="margin:24px 0"><a href="{join_url}" style="display:inline-block;background:#E8820C;color:#0d0f14;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">{btn_text}</a></p>
  <p style="font-size:12px;color:#999;line-height:1.5;margin:24px 0 0;border-top:1px solid #eee;padding-top:16px">{footer}</p>
</td></tr></table>
</td></tr></table></body></html>"""

    text = f"""{meeting_name}

{greeting}

{when_label}: {date_str}
{langs_label}: {langs_str}
{f'{desc_label}: {description}' if description else ''}

{btn_text}: {join_url}

{footer}"""

    return subject, html, text


async def send_meeting_invites(
    *,
    emails: list[str],
    meeting_name: str,
    join_url: str,
    source_lang: str,
    target_langs: list[str],
    scheduled_at: datetime | None,
    description: str | None,
    host_name: str,
) -> int:
    """Send invitation emails. Returns count of successfully sent."""
    settings = get_settings()
    sent = 0

    for email in emails:
        # Determine language from email TLD or default to de
        ui_lang = "de"
        if email.endswith(".com") or email.endswith(".uk"):
            ui_lang = "en"
        elif email.endswith(".fr"):
            ui_lang = "fr"

        subject, html, text = _build_invite_email(
            meeting_name=meeting_name,
            join_url=join_url,
            source_lang=source_lang,
            target_langs=target_langs,
            scheduled_at=scheduled_at,
            description=description,
            host_name=host_name,
            ui_lang=ui_lang,
        )

        if settings.mailer_driver == "resend" and settings.resend_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                        json={
                            "from": f"{settings.mail_from_name} <{settings.mail_from}>",
                            "to": [email],
                            "subject": subject,
                            "html": html,
                            "text": text,
                        },
                    )
                    resp.raise_for_status()
                    sent += 1
            except Exception as exc:
                log.warning("invite_email_failed", to=email, error=str(exc))
        else:
            # Console mailer (development)
            log.info(
                "invite_email_console",
                to=email,
                subject=subject,
                join_url=join_url,
            )
            sent += 1

    return sent
