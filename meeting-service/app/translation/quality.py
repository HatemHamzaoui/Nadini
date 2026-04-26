"""Translation Quality Monitoring — Feedback, Latenz-Tracking, A/B-Testing.

Sammelt:
1. User-Feedback (thumbs up/down) pro Übersetzungssegment
2. Provider-Latenz pro Request (P50/P95/P99)
3. A/B-Test-Ergebnisse (welcher Provider besser bewertet wird)
4. Anomalie-Erkennung (plötzlicher Qualitätsabfall)
"""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class FeedbackEntry:
    segment_id: str
    meeting_id: str
    user_id: str
    provider: str
    source_lang: str
    target_lang: str
    rating: int  # 1 = thumbs down, 5 = thumbs up
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LatencyStats:
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    avg: float = 0.0
    count: int = 0


class QualityMonitor:
    """Tracks translation quality metrics per provider."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._prefix = "quality:"
        # In-memory latency buffers per provider
        self._latencies: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=1000))
        # In-memory feedback counters
        self._feedback_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})

    # ── Latency Tracking ──

    def record_latency(self, provider: str, latency_ms: float) -> None:
        """Record a translation latency measurement."""
        self._latencies[provider].append(latency_ms)

    def get_latency_stats(self, provider: str) -> LatencyStats:
        """Get P50/P95/P99 latency for a provider."""
        data = sorted(self._latencies[provider])
        if not data:
            return LatencyStats()

        n = len(data)
        return LatencyStats(
            p50=data[int(n * 0.5)],
            p95=data[int(n * 0.95)] if n >= 20 else data[-1],
            p99=data[int(n * 0.99)] if n >= 100 else data[-1],
            avg=sum(data) / n,
            count=n,
        )

    def get_all_latency_stats(self) -> dict[str, LatencyStats]:
        """Get latency stats for all providers."""
        return {name: self.get_latency_stats(name) for name in self._latencies}

    # ── User Feedback ──

    async def record_feedback(self, feedback: FeedbackEntry) -> None:
        """Store user feedback for a translation segment."""
        key = f"{self._prefix}feedback:{feedback.segment_id}"
        data = {
            "segment_id": feedback.segment_id,
            "meeting_id": feedback.meeting_id,
            "user_id": feedback.user_id,
            "provider": feedback.provider,
            "source_lang": feedback.source_lang,
            "target_lang": feedback.target_lang,
            "rating": feedback.rating,
            "timestamp": feedback.timestamp.isoformat(),
        }
        await self._redis.setex(key, 86400 * 30, json.dumps(data))  # 30 days TTL

        # Update counters
        if feedback.rating >= 4:
            self._feedback_counts[feedback.provider]["up"] += 1
        elif feedback.rating <= 2:
            self._feedback_counts[feedback.provider]["down"] += 1

        log.info("quality_feedback", provider=feedback.provider,
                 rating=feedback.rating, segment=feedback.segment_id[:8])

    def get_feedback_summary(self) -> dict[str, dict]:
        """Get feedback summary per provider."""
        result = {}
        for provider, counts in self._feedback_counts.items():
            total = counts["up"] + counts["down"]
            approval = round(counts["up"] / total * 100, 1) if total > 0 else 0
            result[provider] = {
                "thumbs_up": counts["up"],
                "thumbs_down": counts["down"],
                "total": total,
                "approval_rate": approval,
            }
        return result

    # ── Anomaly Detection ──

    def check_anomalies(self) -> list[dict]:
        """Detect quality anomalies (sudden latency spikes, low approval)."""
        anomalies = []

        for provider, data in self._latencies.items():
            if len(data) < 10:
                continue
            recent = list(data)[-10:]
            older = list(data)[-50:-10] if len(data) >= 50 else list(data)[:max(1, len(data)-10)]

            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older) if older else avg_recent

            # Latency spike: recent 2x worse than baseline
            if avg_recent > avg_older * 2 and avg_recent > 500:
                anomalies.append({
                    "type": "latency_spike",
                    "provider": provider,
                    "current_avg_ms": round(avg_recent, 1),
                    "baseline_avg_ms": round(avg_older, 1),
                    "severity": "warning" if avg_recent < 2000 else "critical",
                })

        for provider, counts in self._feedback_counts.items():
            total = counts["up"] + counts["down"]
            if total >= 10:
                approval = counts["up"] / total
                if approval < 0.5:
                    anomalies.append({
                        "type": "low_approval",
                        "provider": provider,
                        "approval_rate": round(approval * 100, 1),
                        "total_feedback": total,
                        "severity": "warning" if approval > 0.3 else "critical",
                    })

        return anomalies

    # ── Dashboard Data ──

    def get_dashboard(self) -> dict:
        """Get complete quality dashboard data."""
        return {
            "latency": {
                name: {
                    "p50": stats.p50, "p95": stats.p95, "p99": stats.p99,
                    "avg": round(stats.avg, 1), "count": stats.count,
                }
                for name, stats in self.get_all_latency_stats().items()
            },
            "feedback": self.get_feedback_summary(),
            "anomalies": self.check_anomalies(),
        }
