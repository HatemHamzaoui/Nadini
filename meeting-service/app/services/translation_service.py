"""Übersetzungs-Service mit argostranslate (offline, open-source)."""
from __future__ import annotations

import argostranslate.package
import argostranslate.translate

from app.core.logging import get_logger

log = get_logger(__name__)

# Emoji flags for common languages
LANG_FLAGS = {
    "de": "🇩🇪", "en": "🇬🇧", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
    "pt": "🇵🇹", "ar": "🇸🇦", "zh": "🇨🇳", "ja": "🇯🇵", "ko": "🇰🇷",
    "ru": "🇷🇺", "tr": "🇹🇷", "nl": "🇳🇱", "pl": "🇵🇱",
}

_initialized = False


def ensure_packages_installed() -> None:
    """Download and install language packages if not already present."""
    global _initialized
    if _initialized:
        return

    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    installed_langs = {
        (p.from_code, p.to_code)
        for p in argostranslate.package.get_installed_packages()
    }

    # Core language pairs for Nadini
    desired_pairs = [
        ("de", "en"), ("en", "de"),
        ("de", "fr"), ("fr", "de"),
        ("en", "fr"), ("fr", "en"),
        ("de", "es"), ("es", "de"),
        ("en", "es"), ("es", "en"),
    ]

    for src, tgt in desired_pairs:
        if (src, tgt) in installed_langs:
            continue
        pkg = next(
            (p for p in available if p.from_code == src and p.to_code == tgt),
            None,
        )
        if pkg:
            log.info("installing_language_pack", src=src, tgt=tgt)
            argostranslate.package.install_from_path(pkg.download())

    _initialized = True
    installed = argostranslate.package.get_installed_packages()
    log.info("translation_packages_ready", count=len(installed))


def translate_text(text: str, source_lang: str, target_lang: str) -> str | None:
    """Translate text between languages. Returns None if translation unavailable."""
    try:
        result = argostranslate.translate.translate(text, source_lang, target_lang)
        if result and result != text:
            return result
    except Exception as exc:
        log.warning("translation_failed", src=source_lang, tgt=target_lang, error=str(exc))
    return None


def translate_to_targets(text: str, source_lang: str, target_langs: list[str]) -> list[dict]:
    """Translate text to multiple target languages. Returns list of {lang, flag, text}."""
    translations = []
    for tgt in target_langs:
        if tgt == source_lang:
            continue
        translated = translate_text(text, source_lang, tgt)
        if translated:
            translations.append({
                "lang": tgt.upper(),
                "flag": LANG_FLAGS.get(tgt, ""),
                "text": translated,
            })
    return translations
