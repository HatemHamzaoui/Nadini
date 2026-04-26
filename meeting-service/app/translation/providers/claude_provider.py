"""Anthropic Claude Provider — kontextuelle Übersetzung, stark bei JA+KO.

Unterstützt: 80+ Sprachen. Top Intento 2025 für EN>JA und EN>KO.
Env: ANTHROPIC_API_KEY
"""
from __future__ import annotations

import os

import httpx

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

LANG_NAMES = {
    "de": "German", "en": "English", "fr": "French", "es": "Spanish",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
    "ru": "Russian", "ja": "Japanese", "zh": "Chinese", "ko": "Korean",
    "ar": "Arabic", "tr": "Turkish", "sv": "Swedish", "hi": "Hindi",
    "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
}

SUPPORTED_PAIRS = [
    (s, t) for s in LANG_NAMES for t in LANG_NAMES if s != t
]


class ClaudeProvider(TranslationProvider):
    """Anthropic Claude — high-quality contextual translation, strong for CJK."""

    def __init__(self) -> None:
        super().__init__(name="claude-anthropic", provider_type="claude")
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self._base_url = "https://api.anthropic.com/v1/messages"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("Anthropic API key not configured")

        src_name = LANG_NAMES.get(source_lang, source_lang)
        tgt_name = LANG_NAMES.get(target_lang, target_lang)

        prompt = (
            f"Translate this {src_name} text to {tgt_name}. "
            f"Output ONLY the translation, nothing else:\n\n{text}"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._base_url,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": len(text) * 3,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("content", [])
                if not content:
                    raise TranslationError("Claude returned empty response")
                return content[0].get("text", "").strip()
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"Claude API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("Claude API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Claude error: {exc}") from exc

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
