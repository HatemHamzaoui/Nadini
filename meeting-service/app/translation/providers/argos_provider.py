"""Argostranslate Provider — offline, open-source."""
from __future__ import annotations

import asyncio
import time

import argostranslate.package
import argostranslate.translate

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

CORE_PAIRS = [
    ("de", "en"), ("en", "de"), ("de", "fr"), ("fr", "de"),
    ("en", "fr"), ("fr", "en"), ("de", "es"), ("es", "de"),
    ("en", "es"), ("es", "en"),
]


class ArgosProvider(TranslationProvider):
    def __init__(self) -> None:
        super().__init__(name="argostranslate", provider_type="argostranslate")
        self._initialized = False

    def ensure_packages(self) -> None:
        if self._initialized:
            return
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        installed = {(p.from_code, p.to_code) for p in argostranslate.package.get_installed_packages()}

        for src, tgt in CORE_PAIRS:
            if (src, tgt) in installed:
                continue
            pkg = next((p for p in available if p.from_code == src and p.to_code == tgt), None)
            if pkg:
                log.info("installing_argos_package", src=src, tgt=tgt)
                argostranslate.package.install_from_path(pkg.download())

        self._initialized = True
        log.info("argos_provider_ready", packages=len(argostranslate.package.get_installed_packages()))

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        def _sync_translate():
            result = argostranslate.translate.translate(text, source_lang, target_lang)
            if not result or result == text:
                raise TranslationError(f"No translation available for {source_lang}->{target_lang}")
            return result

        try:
            return await asyncio.to_thread(_sync_translate)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(str(exc)) from exc

    async def health_check(self) -> ProviderStatus:
        try:
            start = time.monotonic()
            await self.translate("Hallo", "de", "en")
            latency = (time.monotonic() - start) * 1000
            self._record_latency(latency)
            if latency < 500:
                return ProviderStatus.GREEN
            elif latency < 2000:
                return ProviderStatus.YELLOW
            return ProviderStatus.RED
        except Exception:
            return ProviderStatus.RED

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        return list(CORE_PAIRS)
