"""Kontextuelle Übersetzung — Sliding Window + Auto-Glossar + Domain-Erkennung.

Verbessert die Übersetzungsqualität durch:
1. Sliding Context Window: letzte N Sätze als Kontext
2. Auto-Glossar: Fachbegriffe aus den ersten Minuten extrahieren
3. Domain-Erkennung: Tech, Legal, Medical, Business → angepasste Prompts
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field

from app.core.logging import get_logger

log = get_logger(__name__)


# ── Domain Detection ──────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "tech": {
        "de": {"api", "server", "cloud", "deployment", "code", "bug", "feature", "sprint", "release",
               "datenbank", "backend", "frontend", "kubernetes", "docker", "pipeline", "ci", "cd",
               "microservice", "repository", "branch", "merge", "pull request", "framework"},
        "en": {"api", "server", "cloud", "deployment", "code", "bug", "feature", "sprint", "release",
               "database", "backend", "frontend", "kubernetes", "docker", "pipeline", "ci", "cd",
               "microservice", "repository", "branch", "merge", "pull request", "framework"},
    },
    "legal": {
        "de": {"vertrag", "klausel", "haftung", "dsgvo", "datenschutz", "einwilligung", "recht",
               "gesetz", "verordnung", "kläger", "beklagter", "urteil", "compliance", "regulierung",
               "paragraph", "verfahren", "gericht", "anwalt", "mandat"},
        "en": {"contract", "clause", "liability", "gdpr", "privacy", "consent", "law", "regulation",
               "plaintiff", "defendant", "verdict", "compliance", "regulation", "court", "attorney"},
    },
    "medical": {
        "de": {"patient", "diagnose", "therapie", "symptom", "medikament", "dosis", "behandlung",
               "befund", "operation", "klinik", "arzt", "praxis", "rezept", "labor"},
        "en": {"patient", "diagnosis", "therapy", "symptom", "medication", "dose", "treatment",
               "surgery", "clinic", "doctor", "prescription", "laboratory", "prognosis"},
    },
    "business": {
        "de": {"umsatz", "gewinn", "budget", "quartal", "investition", "rendite", "kpi", "strategie",
               "markt", "wettbewerb", "zielgruppe", "wachstum", "expansion", "akquisition"},
        "en": {"revenue", "profit", "budget", "quarter", "investment", "return", "kpi", "strategy",
               "market", "competition", "target group", "growth", "expansion", "acquisition"},
    },
}

DOMAIN_PROMPTS = {
    "tech": "This is a technical/IT meeting. Use precise technical terminology. Keep code-related terms in English.",
    "legal": "This is a legal context. Maintain formal register. Translate legal terms precisely according to the target jurisdiction.",
    "medical": "This is a medical context. Use standard medical terminology. Maintain clinical precision.",
    "business": "This is a business meeting. Use professional business language. Keep KPIs and financial terms clear.",
    "general": "This is a general business meeting. Maintain professional but accessible language.",
}


def detect_domain(texts: list[str], lang: str = "de") -> str:
    """Detect meeting domain from accumulated text."""
    combined = " ".join(texts).lower()
    words = set(combined.split())

    scores = {}
    for domain, lang_keywords in DOMAIN_KEYWORDS.items():
        kw = lang_keywords.get(lang, lang_keywords.get("en", set()))
        matches = sum(1 for w in words if any(w.startswith(k) for k in kw))
        scores[domain] = matches

    if not scores or max(scores.values()) < 3:
        return "general"

    return max(scores, key=scores.get)


# ── Auto-Glossar ──────────────────────────────────────────────

def extract_terms(texts: list[str]) -> list[str]:
    """Extract potential domain-specific terms from text."""
    combined = " ".join(texts)
    # Find capitalized multi-word terms (likely proper nouns / technical terms)
    terms = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+\b', combined)
    # Find acronyms
    acronyms = re.findall(r'\b[A-Z]{2,6}\b', combined)
    # Find terms in quotes
    quoted = re.findall(r'"([^"]+)"', combined)

    all_terms = list(set(terms + acronyms + quoted))
    return all_terms[:20]  # Limit to 20 terms


# ── Meeting Context Manager ──────────────────────────────────

@dataclass
class MeetingContext:
    """Manages translation context for a single meeting."""
    meeting_id: str
    source_lang: str = "de"
    window_size: int = 5
    _history: deque = field(default_factory=lambda: deque(maxlen=50))
    _domain: str = "general"
    _domain_checked: bool = False
    _extracted_terms: list[str] = field(default_factory=list)
    _speaker_styles: dict = field(default_factory=dict)

    def add_segment(self, speaker: str, text: str, lang: str) -> None:
        """Add a transcript segment to the context."""
        self._history.append({"speaker": speaker, "text": text, "lang": lang})

        # Re-detect domain after first 10 segments
        if len(self._history) == 10 and not self._domain_checked:
            texts = [s["text"] for s in self._history]
            self._domain = detect_domain(texts, lang)
            self._extracted_terms = extract_terms(texts)
            self._domain_checked = True
            log.info("domain_detected", meeting=self.meeting_id, domain=self._domain,
                     terms=len(self._extracted_terms))

    def get_context_window(self) -> list[dict]:
        """Get the last N segments as context."""
        return list(self._history)[-self.window_size:]

    def get_domain(self) -> str:
        return self._domain

    def get_domain_prompt(self) -> str:
        return DOMAIN_PROMPTS.get(self._domain, DOMAIN_PROMPTS["general"])

    def get_extracted_terms(self) -> list[str]:
        return self._extracted_terms

    def build_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """Build a context-enriched prompt for LLM translation."""
        parts = []

        # Domain instruction
        parts.append(self.get_domain_prompt())

        # Context window
        context = self.get_context_window()
        if context:
            context_lines = [f"[{s['speaker']}] {s['text']}" for s in context]
            parts.append(f"Previous conversation:\n" + "\n".join(context_lines))

        # Extracted terms
        terms = self.get_extracted_terms()
        if terms:
            parts.append(f"Key terms in this meeting: {', '.join(terms[:10])}")

        # Translation instruction
        lang_names = {"de": "German", "en": "English", "fr": "French", "es": "Spanish",
                      "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ar": "Arabic"}
        src = lang_names.get(source_lang, source_lang)
        tgt = lang_names.get(target_lang, target_lang)
        parts.append(f"Translate the following {src} text to {tgt}. "
                     f"Consider the conversation context above for consistent terminology. "
                     f"Output ONLY the translation:")
        parts.append(text)

        return "\n\n".join(parts)


# ── Global Context Store ──────────────────────────────────────

_contexts: dict[str, MeetingContext] = {}


def get_meeting_context(meeting_id: str, source_lang: str = "de") -> MeetingContext:
    """Get or create context for a meeting."""
    if meeting_id not in _contexts:
        _contexts[meeting_id] = MeetingContext(
            meeting_id=meeting_id,
            source_lang=source_lang,
        )
    return _contexts[meeting_id]


def remove_meeting_context(meeting_id: str) -> None:
    """Clean up context when meeting ends."""
    _contexts.pop(meeting_id, None)
