"""EU AI Act Art. 4 — AI Literacy + Art. 5 — Prohibited Practices.

Art. 4: Personal mit KI-Verantwortung muss geschult sein
Art. 5: Bestimmte KI-Anwendungen sind verboten
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger

log = get_logger(__name__)

# ── Art. 5: Prohibited Use Cases ──────────────────────────────

PROHIBITED_USE_CASES = {
    "emotion_recognition_workplace": {
        "de": "Emotionserkennung am Arbeitsplatz",
        "en": "Emotion recognition in the workplace",
        "article": "Art. 5(1)(f)",
    },
    "social_scoring": {
        "de": "Social Scoring",
        "en": "Social scoring",
        "article": "Art. 5(1)(c)",
    },
    "manipulative_practices": {
        "de": "Manipulative oder täuschende KI-Praktiken",
        "en": "Manipulative or deceptive AI practices",
        "article": "Art. 5(1)(a)",
    },
    "biometric_realtime": {
        "de": "Biometrische Echtzeit-Identifizierung im öffentlichen Raum",
        "en": "Real-time biometric identification in public spaces",
        "article": "Art. 5(1)(h)",
    },
}

# Use cases that require High-Risk tier (Annex III)
HIGH_RISK_USE_CASES = {
    "asylum_migration": {"de": "Asyl-, Migrations- und Grenzkontrollverfahren", "annex": "III Nr. 7"},
    "law_enforcement": {"de": "Strafverfolgung, Polizeivernehmungen", "annex": "III Nr. 6"},
    "judicial": {"de": "Gerichtsverfahren, Justizdolmetschen", "annex": "III Nr. 8"},
    "education_grading": {"de": "Bildungs-Prüfungen mit verbindlicher Bewertung", "annex": "III Nr. 3"},
    "medical_diagnosis": {"de": "Medizinische Diagnose-Gespräche", "annex": "Separate Regelung"},
    "safety_critical": {"de": "Sicherheitskritische Live-Übersetzung (Notfall, Luftverkehr)", "annex": "—"},
}


def validate_use_case(use_case_category: str, risk_tier: str) -> dict:
    """Validate if a use case is allowed in the given risk tier.

    Returns: {allowed: bool, reason: str, required_tier: str | None}
    """
    # Check prohibited
    if use_case_category in PROHIBITED_USE_CASES:
        return {
            "allowed": False,
            "reason": f"Prohibited by {PROHIBITED_USE_CASES[use_case_category]['article']}",
            "required_tier": None,
        }

    # Check high-risk requirement
    if use_case_category in HIGH_RISK_USE_CASES:
        if risk_tier == "standard":
            return {
                "allowed": False,
                "reason": f"Requires High-Risk tier (Annex {HIGH_RISK_USE_CASES[use_case_category]['annex']})",
                "required_tier": "high_risk_certified",
            }
        elif risk_tier == "high_risk_ready":
            return {
                "allowed": True,
                "reason": "Allowed in high_risk_ready (pending certification)",
                "required_tier": "high_risk_certified",
            }

    return {"allowed": True, "reason": "Standard tier sufficient", "required_tier": None}


# ── Art. 4: AI Literacy ──────────────────────────────────────

LITERACY_CURRICULUM = [
    {
        "module": "ai_basics",
        "title_de": "KI-Grundlagen",
        "title_en": "AI Basics",
        "description": "Was ist KI? Wie funktioniert maschinelle Übersetzung?",
        "duration_minutes": 30,
        "required_for": ["admin", "tenant_admin", "interpreter"],
    },
    {
        "module": "ai_act_overview",
        "title_de": "EU AI Act Übersicht",
        "title_en": "EU AI Act Overview",
        "description": "Risikoklassen, Transparenzpflichten, Meldepflichten",
        "duration_minutes": 45,
        "required_for": ["admin", "tenant_admin"],
    },
    {
        "module": "translation_quality",
        "title_de": "Übersetzungsqualität bewerten",
        "title_en": "Evaluating Translation Quality",
        "description": "Fehlertypen, Konfidenzwerte, wann menschliche Prüfung nötig",
        "duration_minutes": 30,
        "required_for": ["interpreter", "moderator"],
    },
    {
        "module": "data_protection",
        "title_de": "Datenschutz & DSGVO",
        "title_en": "Data Protection & GDPR",
        "description": "Personenbezogene Daten, Aufbewahrungsfristen, Löschrechte",
        "duration_minutes": 30,
        "required_for": ["admin", "tenant_admin"],
    },
    {
        "module": "incident_management",
        "title_de": "Vorfallmanagement",
        "title_en": "Incident Management",
        "description": "Erkennen, Melden, Eskalieren von schwerwiegenden Vorfällen (Art. 73)",
        "duration_minutes": 20,
        "required_for": ["admin"],
    },
]


def get_required_modules(role: str) -> list[dict]:
    """Get required training modules for a role."""
    return [m for m in LITERACY_CURRICULUM if role in m["required_for"]]


def check_literacy_compliance(role: str, completed_modules: list[str]) -> dict:
    """Check if a user has completed required AI literacy training.

    Returns: {compliant: bool, missing_modules: list, completion_rate: float}
    """
    required = get_required_modules(role)
    required_ids = {m["module"] for m in required}
    completed_set = set(completed_modules)
    missing = required_ids - completed_set

    return {
        "compliant": len(missing) == 0,
        "missing_modules": list(missing),
        "completed": len(completed_set & required_ids),
        "total_required": len(required_ids),
        "completion_rate": round(len(completed_set & required_ids) / max(len(required_ids), 1) * 100, 1),
    }
