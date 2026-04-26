"""KI-Zusammenfassung — extrahiert Key Points, Action Items, Entscheidungen aus Transkripten.

Nutzt regelbasierte Extraktion (kein LLM nötig) + optionalen Übersetzungs-Layer.
Für LLM-basierte Zusammenfassungen: SUMMARIZER_MODE=llm + OPENAI_API_KEY setzen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class MeetingSummary:
    title: str = ""
    duration_minutes: int = 0
    participant_count: int = 0
    languages: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    word_count: int = 0
    segment_count: int = 0


# Patterns für Action Items und Entscheidungen (DE/EN/FR)
ACTION_PATTERNS = [
    # DE
    r"(?:ich|wir) (?:werde|werden|soll|muss|müssen|kümmere?)\b.*",
    r"(?:bitte|todo|aufgabe|task)[\s:]+.*",
    r"(?:als nächstes|next step|nächster schritt)[\s:]+.*",
    # EN
    r"(?:i|we) (?:will|shall|should|must|need to|'ll)\b.*",
    r"(?:please|todo|action item|task)[\s:]+.*",
    r"(?:let'?s|going to)\b.*",
    # FR
    r"(?:je|nous) (?:vais|allons|devons|devrai)\b.*",
    r"(?:à faire|action|tâche)[\s:]+.*",
]

DECISION_PATTERNS = [
    # DE
    r"(?:wir haben beschlossen|entscheidung|beschluss|einigung|wir machen)\b.*",
    r"(?:es wurde entschieden|wir gehen mit|die lösung ist)\b.*",
    # EN
    r"(?:we decided|decision|agreed|we'll go with|the plan is)\b.*",
    r"(?:it was decided|consensus|we're going to)\b.*",
    # FR
    r"(?:nous avons décidé|décision|accord|on fait|la solution est)\b.*",
]

KEY_INDICATORS = [
    # Important statements
    r"(?:wichtig|important|crucial|kritisch|critical|essentiel)\b",
    r"(?:ergebnis|result|résultat|fazit|conclusion)\b",
    r"(?:problem|issue|problème|herausforderung|challenge|défi)\b",
    r"(?:verbesser|improv|amélio|wachstum|growth|croissance)\b",
    r"\d+\s*%",  # Percentages indicate metrics
]


def summarize_transcript(
    entries: list[dict],
    meeting_name: str = "",
    duration_seconds: int = 0,
    participants: list[str] | None = None,
    languages: list[str] | None = None,
) -> MeetingSummary:
    """Generate a summary from transcript entries."""
    summary = MeetingSummary(
        title=meeting_name,
        duration_minutes=round(duration_seconds / 60) if duration_seconds else 0,
        participant_count=len(participants) if participants else 0,
        languages=languages or [],
        segment_count=len(entries),
    )

    all_texts = []
    for entry in entries:
        text = entry.get("text", "").strip()
        if not text:
            continue
        all_texts.append(text)
        speaker = entry.get("speaker", "")
        lower = text.lower()

        # Check for action items
        for pattern in ACTION_PATTERNS:
            if re.search(pattern, lower):
                item = f"{speaker}: {text}" if speaker else text
                if item not in summary.action_items and len(summary.action_items) < 10:
                    summary.action_items.append(item)
                break

        # Check for decisions
        for pattern in DECISION_PATTERNS:
            if re.search(pattern, lower):
                item = text
                if item not in summary.decisions and len(summary.decisions) < 5:
                    summary.decisions.append(item)
                break

        # Check for key points (important statements)
        for pattern in KEY_INDICATORS:
            if re.search(pattern, lower):
                if text not in summary.key_points and len(summary.key_points) < 8:
                    summary.key_points.append(text)
                break

    summary.word_count = sum(len(t.split()) for t in all_texts)

    # If no key points found, take the first and last substantial segments
    if not summary.key_points and all_texts:
        substantial = [t for t in all_texts if len(t.split()) > 5]
        if substantial:
            summary.key_points.append(substantial[0])
            if len(substantial) > 2:
                summary.key_points.append(substantial[len(substantial) // 2])
            if len(substantial) > 1:
                summary.key_points.append(substantial[-1])

    return summary


def format_summary_text(summary: MeetingSummary, lang: str = "de") -> str:
    """Format summary as readable text."""
    if lang == "en":
        labels = {"title": "Meeting Summary", "duration": "Duration", "participants": "Participants",
                  "languages": "Languages", "words": "Words", "key": "Key Points",
                  "actions": "Action Items", "decisions": "Decisions", "none": "None identified"}
    elif lang == "fr":
        labels = {"title": "Résumé de la réunion", "duration": "Durée", "participants": "Participants",
                  "languages": "Langues", "words": "Mots", "key": "Points clés",
                  "actions": "Actions à faire", "decisions": "Décisions", "none": "Aucun identifié"}
    else:
        labels = {"title": "Meeting-Zusammenfassung", "duration": "Dauer", "participants": "Teilnehmer",
                  "languages": "Sprachen", "words": "Wörter", "key": "Kernpunkte",
                  "actions": "Action Items", "decisions": "Entscheidungen", "none": "Keine identifiziert"}

    lines = [
        f"{'═' * 40}",
        f"  {labels['title']}: {summary.title}",
        f"{'═' * 40}",
        f"  {labels['duration']}: {summary.duration_minutes} min",
        f"  {labels['participants']}: {summary.participant_count}",
        f"  {labels['languages']}: {', '.join(l.upper() for l in summary.languages)}",
        f"  {labels['words']}: {summary.word_count}",
        "",
        f"── {labels['key']} ──",
    ]

    if summary.key_points:
        for kp in summary.key_points:
            lines.append(f"  • {kp}")
    else:
        lines.append(f"  {labels['none']}")

    lines.append("")
    lines.append(f"── {labels['actions']} ──")
    if summary.action_items:
        for ai in summary.action_items:
            lines.append(f"  ☐ {ai}")
    else:
        lines.append(f"  {labels['none']}")

    lines.append("")
    lines.append(f"── {labels['decisions']} ──")
    if summary.decisions:
        for d in summary.decisions:
            lines.append(f"  ✓ {d}")
    else:
        lines.append(f"  {labels['none']}")

    return "\n".join(lines)
