"""Naver Papago Provider — bester Koreanisch-Übersetzer mit Höflichkeitsformen.

Unterstützt: KO↔DE/EN/FR/ES/JA/ZH/IT/RU/PT/TH/VI/ID (14 Sprachen).
Env: PAPAGO_CLIENT_ID, PAPAGO_CLIENT_SECRET (Naver Cloud Platform)
"""
from __future__ import annotations

import os

import httpx

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

PAPAGO_LANGS = ["ko", "en", "ja", "zh-CN", "zh-TW", "es", "fr", "de", "ru", "pt", "it", "vi", "th", "id"]
LANG_MAP = {"zh": "zh-CN"}  # Nadini uses "zh", Papago uses "zh-CN"

SUPPORTED_PAIRS = [
    (s, t)
    for s in ["ko", "en", "de", "fr", "es", "ja", "zh", "it", "ru", "pt", "vi", "th", "id"]
    for t in ["ko", "en", "de", "fr", "es", "ja", "zh", "it", "ru", "pt", "vi", "th", "id"]
    if s != t
]


class PapagoProvider(TranslationProvider):
    """Naver Papago — Korean language specialist with honorific support."""

    def __init__(self) -> None:
        super().__init__(name="naver-papago", provider_type="papago")
        self._client_id = os.environ.get("PAPAGO_CLIENT_ID", "")
        self._client_secret = os.environ.get("PAPAGO_CLIENT_SECRET", "")
        self._base_url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"

    def _map_lang(self, lang: str) -> str:
        return LANG_MAP.get(lang, lang)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._client_id or not self._client_secret:
            raise TranslationError("Papago API credentials not configured")

        src = self._map_lang(source_lang)
        tgt = self._map_lang(target_lang)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self._base_url,
                    headers={
                        "X-NCP-APIGW-API-KEY-ID": self._client_id,
                        "X-NCP-APIGW-API-KEY": self._client_secret,
                        "Content-Type": "application/json",
                    },
                    json={
                        "source": src,
                        "target": tgt,
                        "text": text,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("message", {}).get("result", {})
                translated = result.get("translatedText", "")
                if not translated:
                    raise TranslationError("Papago returned empty translation")
                return translated
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"Papago API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("Papago API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Papago error: {exc}") from exc

    async def health_check(self) -> ProviderStatus:
        if not self._client_id:
            return ProviderStatus.RED
        try:
            _, latency = await self.timed_translate("안녕하세요", "ko", "en")
            if latency < 500:
                return ProviderStatus.GREEN
            elif latency < 2000:
                return ProviderStatus.YELLOW
            return ProviderStatus.RED
        except TranslationError:
            return ProviderStatus.RED

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        return list(SUPPORTED_PAIRS)
