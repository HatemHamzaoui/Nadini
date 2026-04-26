"""Glossar-Service — benutzerdefinierte Fachbegriffe für konsistente Übersetzung.

Glossar-Einträge werden pro Meeting gespeichert und bei der Übersetzung
als Post-Processing-Schritt angewendet (Suchen & Ersetzen).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class GlossaryEntry:
    source_term: str
    translations: dict[str, str]  # {"en": "...", "fr": "..."}


# Default-Glossar für häufige KI/Tech-Begriffe
DEFAULT_GLOSSARY: list[GlossaryEntry] = [
    GlossaryEntry("KI", {"en": "AI", "fr": "IA", "es": "IA"}),
    GlossaryEntry("Künstliche Intelligenz", {"en": "Artificial Intelligence", "fr": "Intelligence Artificielle", "es": "Inteligencia Artificial"}),
    GlossaryEntry("Maschinelles Lernen", {"en": "Machine Learning", "fr": "Apprentissage automatique", "es": "Aprendizaje automático"}),
    GlossaryEntry("Echtzeit-Übersetzung", {"en": "Real-time translation", "fr": "Traduction en temps réel", "es": "Traducción en tiempo real"}),
    GlossaryEntry("Spracherkennung", {"en": "Speech recognition", "fr": "Reconnaissance vocale", "es": "Reconocimiento de voz"}),
    GlossaryEntry("Datenschutz", {"en": "Data protection", "fr": "Protection des données", "es": "Protección de datos"}),
    GlossaryEntry("DSGVO", {"en": "GDPR", "fr": "RGPD", "es": "RGPD"}),
]


def apply_glossary(
    text: str,
    glossary: list[GlossaryEntry],
    target_lang: str,
) -> str:
    """Apply glossary terms to a translated text.

    Scans for source terms that were NOT correctly translated
    and replaces with the glossary translation.
    """
    result = text
    for entry in glossary:
        target_term = entry.translations.get(target_lang)
        if not target_term:
            continue

        # If the source term appears in the translated text (wasn't translated),
        # replace it with the correct translation
        if entry.source_term.lower() in result.lower():
            pattern = re.compile(re.escape(entry.source_term), re.IGNORECASE)
            result = pattern.sub(target_term, result)

    return result


def apply_glossary_to_translations(
    translations: list[dict],
    glossary: list[GlossaryEntry] | None = None,
) -> list[dict]:
    """Apply glossary to a list of translation dicts [{lang, text, flag}]."""
    if not glossary:
        glossary = DEFAULT_GLOSSARY

    for t in translations:
        lang = t.get("lang", "").lower()
        text = t.get("text", "")
        if lang and text:
            t["text"] = apply_glossary(text, glossary, lang)

    return translations
