"""Azure Translator Provider — 135+ Sprachen, günstigster kommerzieller Provider.

$10/1M Zeichen. Guter universeller Backup.
Env: AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_REGION (default: westeurope)
"""
from __future__ import annotations

import os
import uuid

import httpx

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

SUPPORTED_PAIRS = [
    (s, t)
    for s in ["de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru", "ja", "zh", "ko",
              "ar", "tr", "sv", "hi", "th", "vi", "id", "uk", "cs", "ro", "el", "da",
              "fi", "no", "hu", "bg", "sk", "hr", "sl", "lt", "lv", "et", "he", "fa"]
    for t in ["de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru", "ja", "zh", "ko",
              "ar", "tr", "sv", "hi", "th", "vi", "id", "uk", "cs", "ro", "el", "da",
              "fi", "no", "hu", "bg", "sk", "hr", "sl", "lt", "lv", "et", "he", "fa"]
    if s != t
]

# Azure uses "zh-Hans" for simplified Chinese
LANG_MAP = {"zh": "zh-Hans"}


class AzureTranslatorProvider(TranslationProvider):
    """Azure Cognitive Services Translator — broadest coverage, lowest cost."""

    def __init__(self) -> None:
        super().__init__(name="azure-translator", provider_type="azure")
        self._api_key = os.environ.get("AZURE_TRANSLATOR_KEY", "")
        self._region = os.environ.get("AZURE_TRANSLATOR_REGION", "westeurope")
        self._base_url = "https://api.cognitive.microsofttranslator.com/translate"

    def _map_lang(self, lang: str) -> str:
        return LANG_MAP.get(lang, lang)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("Azure Translator API key not configured")

        src = self._map_lang(source_lang)
        tgt = self._map_lang(target_lang)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self._base_url,
                    params={"api-version": "3.0", "from": src, "to": tgt},
                    headers={
                        "Ocp-Apim-Subscription-Key": self._api_key,
                        "Ocp-Apim-Subscription-Region": self._region,
                        "Content-Type": "application/json",
                        "X-ClientTraceId": str(uuid.uuid4()),
                    },
                    json=[{"Text": text}],
                )
                resp.raise_for_status()
                data = resp.json()
                if not data or not data[0].get("translations"):
                    raise TranslationError("Azure returned empty translation")
                return data[0]["translations"][0]["text"]
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"Azure API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("Azure API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Azure error: {exc}") from exc

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
