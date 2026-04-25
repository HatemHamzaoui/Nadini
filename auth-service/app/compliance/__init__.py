"""AI-Act-Compliance-Modul.

Geteilte Library für alle Microservices (Auth, Meeting, Routing, etc.).
Bündelt:
- AI-Disclosure-Versionen und -Texte (Art. 50(1)+(5))
- Provenance/Watermarking-Helfer (Art. 50(2)) — Schnittstellen für späteren Compliance-Service
- Audit-Logging-Wrapper mit korrekten Retention-Klassen
- Risk-Tier-Logik (Standard / High-Risk-Ready / High-Risk-Certified)
"""

from app.compliance.disclosure import (
    CURRENT_DISCLOSURE_VERSION,
    DISCLOSURE_TEXTS,
    DisclosureText,
    get_disclosure_text,
)
from app.compliance.risk_tier import RiskTier, requires_extended_logging

__all__ = [
    "CURRENT_DISCLOSURE_VERSION",
    "DISCLOSURE_TEXTS",
    "DisclosureText",
    "get_disclosure_text",
    "RiskTier",
    "requires_extended_logging",
]
