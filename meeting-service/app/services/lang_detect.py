"""Leichtgewichtige Spracherkennung basierend auf Stoppwörtern.

Erkennt die Sprache eines Textes ohne externe Bibliothek.
Unterstützt: DE, EN, FR, ES.
"""
from __future__ import annotations

STOPWORDS = {
    "de": {"der", "die", "das", "und", "ist", "in", "von", "mit", "den", "für", "auf", "ein", "eine",
           "nicht", "sich", "es", "auch", "ich", "wir", "sie", "er", "an", "wie", "aber", "hat",
           "dass", "werden", "kann", "noch", "nach", "über", "so", "oder", "wenn", "nur", "zum",
           "schon", "als", "haben", "aus", "bei", "vor", "zur", "sehr", "dann", "kein", "keine"},
    "en": {"the", "and", "is", "in", "of", "to", "a", "that", "it", "for", "was", "on", "are",
           "with", "as", "at", "be", "this", "have", "from", "or", "an", "but", "not", "by",
           "they", "which", "you", "we", "can", "will", "been", "has", "its", "would", "about",
           "their", "than", "into", "some", "could", "them", "other", "just", "should"},
    "fr": {"le", "la", "les", "de", "des", "et", "est", "en", "un", "une", "du", "que", "qui",
           "dans", "pour", "pas", "sur", "ce", "par", "avec", "plus", "sont", "nous", "vous",
           "mais", "été", "cette", "ils", "aux", "tout", "elle", "ses", "aussi", "même", "ont"},
    "es": {"el", "la", "los", "las", "de", "en", "y", "que", "es", "un", "una", "por", "con",
           "para", "del", "se", "al", "no", "más", "pero", "su", "sus", "como", "está",
           "todo", "han", "hay", "fue", "son", "muy", "también", "entre", "sin", "sobre"},
}


def detect_language(text: str) -> tuple[str, float]:
    """Detect language of text. Returns (lang_code, confidence).

    Confidence: 0.0 (uncertain) to 1.0 (very confident).
    Falls back to "en" if uncertain.
    """
    words = set(text.lower().split())
    if len(words) < 3:
        return "en", 0.1  # Too short to detect

    scores = {}
    for lang, stopwords in STOPWORDS.items():
        matches = len(words & stopwords)
        scores[lang] = matches

    total = sum(scores.values())
    if total == 0:
        return "en", 0.1

    best_lang = max(scores, key=scores.get)
    confidence = scores[best_lang] / total if total > 0 else 0
    # Require at least 40% dominance
    if confidence < 0.4:
        return "en", round(confidence, 2)

    return best_lang, round(confidence, 2)
