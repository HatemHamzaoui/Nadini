"""Prometheus Metrics für Meeting-Service + Translation Pipeline.

Exponiert auf /metrics für Grafana-Scraping.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, Info

# ── Translation Metrics ──
TRANSLATION_REQUESTS = Counter(
    "nadini_translation_requests_total",
    "Total translation requests",
    ["provider", "source_lang", "target_lang", "status"],
)

TRANSLATION_LATENCY = Histogram(
    "nadini_translation_latency_seconds",
    "Translation latency in seconds",
    ["provider"],
    buckets=[0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0],
)

TRANSLATION_FAILOVERS = Counter(
    "nadini_translation_failovers_total",
    "Total failover events",
    ["source_provider", "fallback_provider"],
)

# ── Meeting Metrics ──
ACTIVE_MEETINGS = Gauge(
    "nadini_active_meetings",
    "Currently active meetings",
)

ACTIVE_WEBSOCKETS = Gauge(
    "nadini_active_websockets",
    "Currently connected WebSocket clients",
)

MEETING_DURATION = Histogram(
    "nadini_meeting_duration_seconds",
    "Meeting duration in seconds",
    buckets=[60, 300, 600, 1800, 3600, 7200],
)

# ── ASR Metrics ──
ASR_REQUESTS = Counter(
    "nadini_asr_requests_total",
    "Total ASR transcription requests",
    ["language"],
)

# ── Quality Metrics ──
FEEDBACK_TOTAL = Counter(
    "nadini_feedback_total",
    "Total user feedback events",
    ["provider", "rating"],
)

# ── Provider Health ──
PROVIDER_HEALTH = Gauge(
    "nadini_provider_health",
    "Provider health status (1=green, 0.5=yellow, 0=red)",
    ["provider"],
)

# ── Service Info ──
SERVICE_INFO = Info(
    "nadini_service",
    "Service information",
)
SERVICE_INFO.info({
    "version": "4.0.0",
    "service": "meeting-service",
})
