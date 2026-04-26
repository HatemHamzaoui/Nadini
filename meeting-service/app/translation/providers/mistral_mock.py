"""Mistral/Voxtral Mock Provider — simuliert EU-Cloud-Provider."""
from __future__ import annotations

import asyncio
import random

from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

ALL_PAIRS = [
    (s, t) for s in ["de", "en", "fr", "es", "it", "pt", "ar", "zh", "ja"]
    for t in ["de", "en", "fr", "es", "it", "pt", "ar", "zh", "ja"] if s != t
]


class MistralMockProvider(TranslationProvider):
    """Simuliert Mistral/Voxtral mit ~200ms Latenz und 5% Fehlerrate."""

    def __init__(self) -> None:
        super().__init__(name="mistral-voxtral", provider_type="mistral")
        self._failure_rate = 0.05
        self._base_latency = 0.15  # 150-250ms

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        # Simulate latency
        latency = self._base_latency + random.uniform(0, 0.1)
        await asyncio.sleep(latency)

        # Simulate random failures
        if random.random() < self._failure_rate:
            raise TranslationError("Mistral API: simulated timeout")

        # Return mock translation
        return f"[Mistral:{source_lang}→{target_lang}] {text}"

    async def health_check(self) -> ProviderStatus:
        try:
            _, latency = await self.timed_translate("test", "de", "en")
            if latency < 500:
                return ProviderStatus.GREEN
            elif latency < 2000:
                return ProviderStatus.YELLOW
            return ProviderStatus.RED
        except TranslationError:
            return ProviderStatus.RED

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        return list(ALL_PAIRS)
