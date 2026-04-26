"""DeepSeek Provider — OpenAI-kompatible API, günstig, stark bei CJK.

Env: DEEPSEEK_API_KEY
API: https://api.deepseek.com/v1 (OpenAI-kompatibel)
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
    "ar": "Arabic", "tr": "Turkish", "hi": "Hindi", "th": "Thai",
    "vi": "Vietnamese", "id": "Indonesian",
}

SUPPORTED_PAIRS = [(s, t) for s in LANG_NAMES for t in LANG_NAMES if s != t]


class DeepSeekProvider(TranslationProvider):
    """DeepSeek — cost-effective LLM translation, strong for CJK."""

    def __init__(self) -> None:
        super().__init__(name="deepseek", provider_type="deepseek")
        self._api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self._model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self._base_url = "https://api.deepseek.com/v1"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("DeepSeek API key not configured")

        src_name = LANG_NAMES.get(source_lang, source_lang)
        tgt_name = LANG_NAMES.get(target_lang, target_lang)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": f"You are a professional real-time interpreter. Translate {src_name} to {tgt_name}. Output ONLY the translation."},
                            {"role": "user", "content": text},
                        ],
                        "temperature": 0.1,
                        "max_tokens": len(text) * 3,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise TranslationError("DeepSeek returned empty response")
                return choices[0]["message"]["content"].strip()
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"DeepSeek API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("DeepSeek API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"DeepSeek error: {exc}") from exc

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
