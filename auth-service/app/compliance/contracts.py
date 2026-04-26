"""EU AI Act Art. 25 + 27 — Provider-Deployer Verträge + FRIA.

Art. 25: Klare Rollenzuweisung Provider (LexAdQ) ↔ Deployer (Tenant)
Art. 27: Fundamental Rights Impact Assessment für High-Risk-Tenants
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ContractType(str, Enum):
    AGB = "agb"              # Allgemeine Geschäftsbedingungen
    AVV = "avv"              # Auftragsverarbeitungsvereinbarung (DSGVO Art. 28)
    AUP = "aup"              # Acceptable Use Policy
    DEPLOYER = "deployer"    # Art. 25 Deployer-Pflichten
    FRIA = "fria"            # Art. 27 Fundamental Rights Impact Assessment


# FRIA Template — 5 Bewertungsbereiche
FRIA_DOMAINS = [
    {
        "domain": "discrimination",
        "title_de": "Diskriminierung",
        "title_en": "Discrimination",
        "description": "Risiko dass KI-Übersetzung bestimmte Gruppen benachteiligt (Dialekte, Akzente, Geschlecht)",
        "questions": [
            "Werden alle Sprachen/Dialekte gleichwertig unterstützt?",
            "Gibt es Qualitätsunterschiede nach Geschlecht der Sprechenden?",
            "Werden kulturelle Nuancen angemessen berücksichtigt?",
        ],
    },
    {
        "domain": "privacy",
        "title_de": "Datenschutz",
        "title_en": "Privacy",
        "description": "Risiko für personenbezogene Daten in Audio-Aufnahmen und Transkripten",
        "questions": [
            "Werden Audio-Daten nach Verarbeitung gelöscht?",
            "Wer hat Zugriff auf gespeicherte Transkripte?",
            "Werden personenbezogene Daten in Übersetzungen anonymisiert?",
        ],
    },
    {
        "domain": "autonomy",
        "title_de": "Autonomie",
        "title_en": "Autonomy",
        "description": "Risiko dass User sich blind auf KI-Übersetzung verlassen",
        "questions": [
            "Wird klar kommuniziert dass Übersetzungen Fehler enthalten können?",
            "Können User die Übersetzung manuell korrigieren?",
            "Gibt es einen Rückfallmechanismus (menschlicher Dolmetscher)?",
        ],
    },
    {
        "domain": "transparency",
        "title_de": "Transparenz",
        "title_en": "Transparency",
        "description": "Verständlichkeit der KI-Funktionsweise für Endnutzer",
        "questions": [
            "Wird offengelegt welches KI-Modell die Übersetzung erstellt?",
            "Können User nachvollziehen warum eine bestimmte Übersetzung gewählt wurde?",
            "Sind Fehlergrenzen und Konfidenzwerte sichtbar?",
        ],
    },
    {
        "domain": "accountability",
        "title_de": "Verantwortlichkeit",
        "title_en": "Accountability",
        "description": "Klarheit über Verantwortung bei Fehlübersetzungen",
        "questions": [
            "Ist definiert wer bei Fehlübersetzungen haftet?",
            "Gibt es einen Eskalationsprozess für schwerwiegende Fehler?",
            "Werden Incidents innerhalb von 72h an Behörden gemeldet?",
        ],
    },
]


@dataclass
class FRIAAssessment:
    tenant_id: str
    assessor: str  # Email of person who conducted assessment
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    domain_scores: dict[str, int] = field(default_factory=dict)  # domain → 1-5 risk score
    mitigations: dict[str, str] = field(default_factory=dict)  # domain → mitigation description
    overall_risk: str = "medium"  # low, medium, high
    approved: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None


def generate_fria_template() -> dict:
    """Generate a blank FRIA template for a tenant to fill out."""
    return {
        "version": "1.0",
        "domains": FRIA_DOMAINS,
        "instructions": {
            "de": "Bewerten Sie jedes Risikobereiche mit 1 (niedrig) bis 5 (hoch). "
                  "Beschreiben Sie für jedes Risiko die geplanten Maßnahmen.",
            "en": "Rate each risk domain from 1 (low) to 5 (high). "
                  "For each risk, describe planned mitigation measures.",
        },
        "required_for": "High-Risk-Certified tier (Art. 27 EU AI Act)",
    }


def evaluate_fria(domain_scores: dict[str, int]) -> str:
    """Evaluate overall risk from domain scores."""
    if not domain_scores:
        return "unknown"
    avg = sum(domain_scores.values()) / len(domain_scores)
    if avg <= 2:
        return "low"
    elif avg <= 3.5:
        return "medium"
    return "high"
