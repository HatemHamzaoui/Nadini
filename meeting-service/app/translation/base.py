"""Translation Provider — Abstract Base Class + Shared Types."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ProviderStatus(str, Enum):
    GREEN = "green"    # < 500ms, healthy
    YELLOW = "yellow"  # 500-2000ms or intermittent errors
    RED = "red"        # timeout/error/down


@dataclass
class ProviderHealth:
    status: ProviderStatus = ProviderStatus.RED
    avg_latency_ms: float = 0.0
    last_check: datetime | None = None
    error_count: int = 0
    success_count: int = 0
    last_error: str | None = None


class TranslationError(Exception):
    pass


class TranslationProvider(ABC):
    """Abstract base for all translation providers."""

    def __init__(self, name: str, provider_type: str) -> None:
        self.name = name
        self.provider_type = provider_type
        self._latencies: deque[float] = deque(maxlen=20)

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text. Raises TranslationError on failure."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Check provider health. Returns GREEN/YELLOW/RED."""
        ...

    @abstractmethod
    def get_supported_pairs(self) -> list[tuple[str, str]]:
        """Return list of (source, target) language pairs."""
        ...

    def get_latency_ms(self) -> float:
        """Rolling average latency in milliseconds."""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    def _record_latency(self, ms: float) -> None:
        self._latencies.append(ms)

    async def timed_translate(self, text: str, source_lang: str, target_lang: str) -> tuple[str, float]:
        """Translate with timing. Returns (translated_text, latency_ms)."""
        start = time.monotonic()
        result = await self.translate(text, source_lang, target_lang)
        latency = (time.monotonic() - start) * 1000
        self._record_latency(latency)
        return result, latency
