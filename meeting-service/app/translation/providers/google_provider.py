"""Google Cloud Translation API v2 Provider — breiteste Sprachabdeckung.

Unterstützt: 130+ Sprachen.
Kosten: $20/1M Zeichen.
Env: GOOGLE_TRANSLATE_API_KEY (einfacher API-Key, kein Service Account nötig)
"""
from __future__ import annotations

import os

import httpx

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

# Google uses standard ISO 639-1 codes
SUPPORTED_LANGS = [
    "de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru", "ja", "zh", "ko",
    "ar", "tr", "sv", "hi", "th", "vi", "id", "uk", "cs", "ro", "el", "da",
    "fi", "no", "hu", "bg", "sk", "hr", "sl", "lt", "lv", "et",
]

SUPPORTED_PAIRS = [
    (s, t) for s in SUPPORTED_LANGS for t in SUPPORTED_LANGS if s != t
]


class GoogleTranslateProvider(TranslationProvider):
    """Google Cloud Translation API v2 — broadest language coverage."""

    def __init__(self) -> None:
        super().__init__(name="google-translate", provider_type="google")
        self._api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
        self._base_url = "https://translation.googleapis.com/language/translate/v2"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("Google Translate API key not configured")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self._base_url,
                    params={"key": self._api_key},
                    json={
                        "q": text,
                        "source": source_lang,
                        "target": target_lang,
                        "format": "text",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                translations = data.get("data", {}).get("translations", [])
                if not translations:
                    raise TranslationError("Google returned empty translation")
                return translations[0]["translatedText"]
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"Google API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("Google API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Google error: {exc}") from exc

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
