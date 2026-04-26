"""ByteDance/Seed Mock Provider — simuliert asiatischen Cloud-Provider."""
from __future__ import annotations

import asyncio
import random

from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

ALL_PAIRS = [
    (s, t) for s in ["de", "en", "fr", "es", "zh", "ja", "ko", "ar"]
    for t in ["de", "en", "fr", "es", "zh", "ja", "ko", "ar"] if s != t
]


class SeedMockProvider(TranslationProvider):
    """Simuliert ByteDance/Seed mit ~300ms Latenz und 5% Fehlerrate."""

    def __init__(self) -> None:
        super().__init__(name="seed-bytedance", provider_type="seed")
        self._failure_rate = 0.05
        self._base_latency = 0.25  # 250-350ms

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        latency = self._base_latency + random.uniform(0, 0.1)
        await asyncio.sleep(latency)

        if random.random() < self._failure_rate:
            raise TranslationError("Seed API: simulated connection error")

        return f"[Seed:{source_lang}→{target_lang}] {text}"

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
