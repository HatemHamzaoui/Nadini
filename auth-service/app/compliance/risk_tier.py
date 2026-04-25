"""Risk-Tier-Modell des Hybrid-Compliance-Pfads.

- standard               : niedrigriskante Use Cases (Business-Meetings, Konferenzen).
                           Art. 50 AI Act anwendbar.
- high_risk_ready        : Tenant hat Hochrisiko-Pflichten technisch aktiviert,
                           aber noch keine externe Konformitätsbewertung.
- high_risk_certified    : Externe Konformitätsbewertung abgeschlossen,
                           CE-Kennzeichnung, EU-Datenbank-Eintrag.
"""
from __future__ import annotations

from enum import StrEnum


class RiskTier(StrEnum):
    STANDARD = "standard"
    HIGH_RISK_READY = "high_risk_ready"
    HIGH_RISK_CERTIFIED = "high_risk_certified"


# Welche Tiers benötigen erweitertes Logging (Art. 12 AI Act)?
_EXTENDED_LOGGING_TIERS: frozenset[str] = frozenset(
    {RiskTier.HIGH_RISK_READY.value, RiskTier.HIGH_RISK_CERTIFIED.value}
)


def requires_extended_logging(risk_tier: str | None) -> bool:
    """True, wenn dieser Tenant erweiterte Compliance-Logs benötigt."""
    if risk_tier is None:
        return False
    return risk_tier in _EXTENDED_LOGGING_TIERS


def retention_class_for(risk_tier: str | None) -> str:
    """Gibt die korrekte Retention-Klasse für einen Tenant-Tier zurück."""
    if requires_extended_logging(risk_tier):
        return "extended_compliance"
    return "standard"
