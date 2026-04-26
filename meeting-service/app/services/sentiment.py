"""Echtzeit-Sentiment-Analyse — regelbasiert, kein LLM nötig.

Analysiert Text auf positive/negative/neutrale Stimmung anhand von
Keyword-Listen (DE/EN/FR). Leichtgewichtig, läuft inline bei jedem Segment.
"""
from __future__ import annotations

from dataclasses import dataclass

POSITIVE_WORDS = {
    "de": {"gut", "super", "toll", "hervorragend", "perfekt", "genial", "klasse", "prima",
           "freude", "erfolg", "fortschritt", "verbesser", "wachstum", "gewinn", "positiv",
           "einverstanden", "zustimm", "ja", "richtig", "stimmt", "gerne", "danke", "bravo"},
    "en": {"good", "great", "excellent", "perfect", "amazing", "wonderful", "fantastic",
           "progress", "improvement", "growth", "success", "agree", "yes", "right",
           "thanks", "brilliant", "awesome", "happy", "pleased", "impressed"},
    "fr": {"bien", "super", "excellent", "parfait", "formidable", "génial", "bravo",
           "progrès", "amélioration", "croissance", "succès", "accord", "oui",
           "merci", "impressionnant", "content", "heureux"},
}

NEGATIVE_WORDS = {
    "de": {"schlecht", "problem", "fehler", "schwierig", "leider", "nein", "nicht",
           "versagt", "verzöger", "risiko", "mangel", "verlust", "kritisch", "sorge",
           "bedenken", "unmöglich", "scheitern", "abgelehnt", "enttäusch"},
    "en": {"bad", "problem", "error", "difficult", "unfortunately", "no", "not",
           "failed", "delay", "risk", "lack", "loss", "critical", "concern",
           "worry", "impossible", "reject", "disappoint", "issue", "bug"},
    "fr": {"mauvais", "problème", "erreur", "difficile", "malheureusement", "non",
           "échoué", "retard", "risque", "manque", "perte", "critique", "souci",
           "inquiétude", "impossible", "rejeté", "déçu"},
}


@dataclass
class SentimentResult:
    score: float  # -1.0 (very negative) to 1.0 (very positive)
    label: str  # "positive", "neutral", "negative"
    confidence: float  # 0.0 to 1.0


def analyze_sentiment(text: str, lang: str = "de") -> SentimentResult:
    """Analyze sentiment of a text string."""
    words = set(text.lower().split())
    pos_dict = POSITIVE_WORDS.get(lang, POSITIVE_WORDS.get("en", set()))
    neg_dict = NEGATIVE_WORDS.get(lang, NEGATIVE_WORDS.get("en", set()))

    pos_count = sum(1 for w in words if any(w.startswith(p) for p in pos_dict))
    neg_count = sum(1 for w in words if any(w.startswith(n) for n in neg_dict))
    total = pos_count + neg_count

    if total == 0:
        return SentimentResult(score=0.0, label="neutral", confidence=0.3)

    score = (pos_count - neg_count) / total
    confidence = min(total / 5, 1.0)  # More words = more confidence

    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return SentimentResult(score=round(score, 2), label=label, confidence=round(confidence, 2))
