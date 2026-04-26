"""DeepL API Provider — höchste Qualität für EU-Sprachen.

Unterstützt: DE, EN, FR, ES, IT, NL, PL, PT, RU, JA, ZH, KO + weitere.
Free Tier: 500.000 Zeichen/Monat.
Env: DEEPL_API_KEY
"""
from __future__ import annotations

import os
import time

import httpx

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

# DeepL language codes differ slightly from ISO 639-1
DEEPL_LANG_MAP = {
    "en": "EN", "de": "DE", "fr": "FR", "es": "ES", "it": "IT",
    "nl": "NL", "pl": "PL", "pt": "PT-BR", "ru": "RU", "ja": "JA",
    "zh": "ZH", "ko": "KO", "ar": "AR", "tr": "TR", "sv": "SV",
}

SUPPORTED_PAIRS = [
    (s, t) for s in DEEPL_LANG_MAP for t in DEEPL_LANG_MAP if s != t
]


class DeepLProvider(TranslationProvider):
    """DeepL Translation API — premium quality for European languages."""

    def __init__(self) -> None:
        super().__init__(name="deepl", provider_type="deepl")
        self._api_key = os.environ.get("DEEPL_API_KEY", "")
        # Free keys use api-free.deepl.com, Pro keys use api.deepl.com
        if self._api_key.endswith(":fx"):
            self._base_url = "https://api-free.deepl.com/v2"
        else:
            self._base_url = "https://api.deepl.com/v2"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("DeepL API key not configured")

        src = DEEPL_LANG_MAP.get(source_lang, source_lang.upper())
        tgt = DEEPL_LANG_MAP.get(target_lang, target_lang.upper())

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/translate",
                    headers={"Authorization": f"DeepL-Auth-Key {self._api_key}"},
                    data={
                        "text": text,
                        "source_lang": src,
                        "target_lang": tgt,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                translations = data.get("translations", [])
                if not translations:
                    raise TranslationError("DeepL returned empty translation")
                return translations[0]["text"]
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"DeepL API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("DeepL API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"DeepL error: {exc}") from exc

    async def health_check(self) -> ProviderStatus:
        if not self._api_key:
            return ProviderStatus.RED
        try:
            _, latency = await self.timed_translate("Hello", "en", "de")
            if latency < 500:
                return ProviderStatus.GREEN
            elif latency < 2000:
                return ProviderStatus.YELLOW
            return ProviderStatus.RED
        except TranslationError:
            return ProviderStatus.RED

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        return list(SUPPORTED_PAIRS)
