"""OpenAI GPT-4o-mini Provider — kontextuelle Übersetzung mit LLM.

Unterstützt: 100+ Sprachen.
Kosten: ~$0.15/1M input tokens, $0.60/1M output tokens.
Env: OPENAI_API_KEY
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
}

# GPT supports virtually all language pairs
SUPPORTED_PAIRS = [
    (s, t) for s in LANG_NAMES for t in LANG_NAMES if s != t
]


class OpenAIProvider(TranslationProvider):
    """OpenAI GPT-4o-mini — high-quality contextual translation."""

    def __init__(self) -> None:
        super().__init__(name="openai-gpt4o-mini", provider_type="openai")
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._base_url = "https://api.openai.com/v1"

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self._api_key:
            raise TranslationError("OpenAI API key not configured")

        src_name = LANG_NAMES.get(source_lang, source_lang)
        tgt_name = LANG_NAMES.get(target_lang, target_lang)

        system_prompt = (
            f"You are a professional real-time interpreter. "
            f"Translate the following {src_name} text to {tgt_name}. "
            f"Provide ONLY the translation, no explanations. "
            f"Maintain the original tone and register."
        )

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
                            {"role": "system", "content": system_prompt},
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
                    raise TranslationError("OpenAI returned empty response")
                return choices[0]["message"]["content"].strip()
        except httpx.HTTPStatusError as exc:
            raise TranslationError(f"OpenAI API error: {exc.response.status_code}") from exc
        except httpx.TimeoutException:
            raise TranslationError("OpenAI API timeout") from None
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"OpenAI error: {exc}") from exc

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
