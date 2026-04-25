"""AI-Disclosure-Texte (Art. 50(1) + 50(5) AI Act).

Wir versionieren die Disclosure-Texte. Bei jeder inhaltlichen Änderung
muss der User die neue Version erneut bestätigen.

Warum hier und nicht in einer DB? Die Texte sind Teil des Quellcodes —
versionsgebunden, codereviewed, in CI getestet, audit-fähig.
"""
from __future__ import annotations

from dataclasses import dataclass

# WICHTIG: Bei jeder Änderung des Disclosure-Texts MUSS diese Version erhöht werden,
# damit User die neue Fassung erneut bestätigen müssen.
CURRENT_DISCLOSURE_VERSION = "2026-04-25"


@dataclass(frozen=True)
class DisclosureText:
    version: str
    locale: str
    title: str
    body: str
    short_label: str  # für persistentes UI-Banner (Art. 50(5) — sichtbar während Nutzung)
    acknowledge_button: str


_DE = DisclosureText(
    version=CURRENT_DISCLOSURE_VERSION,
    locale="de",
    title="Hinweis zur KI-Nutzung",
    body=(
        "Diese Plattform setzt Künstliche Intelligenz für die Echtzeit-Übersetzung "
        "und Verdolmetschung Ihrer Konversationen ein. Sie interagieren nicht mit "
        "menschlichen Dolmetscherinnen oder Dolmetschern.\n\n"
        "Was Sie wissen sollten:\n"
        "• Übersetzungen werden durch KI-Modelle erstellt und können Fehler enthalten.\n"
        "• Verlassen Sie sich nicht auf KI-Übersetzungen für rechtsverbindliche, "
        "medizinische oder sicherheitskritische Entscheidungen.\n"
        "• Ihre Audio-Aufnahmen werden zur Übersetzung an unsere KI-Dienste übermittelt "
        "und nach Verarbeitung gemäß unserer Datenschutzerklärung behandelt.\n"
        "• Übersetzte Inhalte werden technisch als KI-generiert markiert.\n\n"
        "Mit Ihrer Bestätigung erklären Sie, dass Sie diese Information erhalten haben."
    ),
    short_label="🤖 KI-Übersetzung aktiv",
    acknowledge_button="Verstanden, fortfahren",
)


_EN = DisclosureText(
    version=CURRENT_DISCLOSURE_VERSION,
    locale="en",
    title="AI Use Notice",
    body=(
        "This platform uses Artificial Intelligence to translate and interpret your "
        "conversations in real time. You are not interacting with human interpreters.\n\n"
        "What you should know:\n"
        "• Translations are produced by AI models and may contain errors.\n"
        "• Do not rely on AI translations for legally binding, medical, or safety-"
        "critical decisions.\n"
        "• Your audio is transmitted to our AI services for translation and handled "
        "according to our Privacy Policy.\n"
        "• Translated outputs are technically marked as AI-generated.\n\n"
        "By acknowledging, you confirm that you have received this information."
    ),
    short_label="🤖 AI translation active",
    acknowledge_button="Understood, continue",
)


_FR = DisclosureText(
    version=CURRENT_DISCLOSURE_VERSION,
    locale="fr",
    title="Avis d'utilisation de l'IA",
    body=(
        "Cette plateforme utilise l'intelligence artificielle pour traduire et "
        "interpréter vos conversations en temps réel. Vous n'interagissez pas avec "
        "des interprètes humains.\n\n"
        "Points importants :\n"
        "• Les traductions sont produites par des modèles d'IA et peuvent contenir "
        "des erreurs.\n"
        "• Ne vous fiez pas aux traductions par IA pour des décisions juridiques, "
        "médicales ou de sécurité.\n"
        "• Votre audio est transmis à nos services d'IA pour traduction.\n"
        "• Les contenus traduits sont marqués techniquement comme générés par IA.\n\n"
        "En confirmant, vous reconnaissez avoir reçu cette information."
    ),
    short_label="🤖 Traduction IA active",
    acknowledge_button="Compris, continuer",
)


DISCLOSURE_TEXTS: dict[str, DisclosureText] = {
    "de": _DE,
    "en": _EN,
    "fr": _FR,
}


def get_disclosure_text(locale: str) -> DisclosureText:
    """Gibt die Disclosure für die angeforderte Locale, fällt auf 'en' zurück."""
    return DISCLOSURE_TEXTS.get(locale, _EN)
