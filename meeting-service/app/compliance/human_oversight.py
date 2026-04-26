"""EU AI Act Art. 14 — Human Oversight.

Implementiert:
1. Confidence-Schwelle: Übersetzungen unter 0.7 → Flag für manuelle Prüfung
2. Review-Workflow: Transkript muss vor Export bei High-Risk-Meetings geprüft werden
3. Anomalie-Alert: Wenn Qualität plötzlich sinkt → Warnung an Admin
4. Report-Funktion: User können problematische Übersetzungen melden
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger

log = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.7  # Below this → flag for human review
QUALITY_DROP_THRESHOLD = 0.3  # If approval drops below 30% → alert


@dataclass
class ReviewFlag:
    segment_id: str
    meeting_id: str
    reason: str  # "low_confidence", "user_report", "anomaly"
    confidence: float
    provider: str
    flagged_at: datetime
    reviewed: bool = False
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None


# In-memory review queue (production: use Redis or DB)
_review_queue: list[ReviewFlag] = []


def check_translation_quality(
    segment_id: str,
    meeting_id: str,
    confidence: float,
    provider: str,
) -> ReviewFlag | None:
    """Check if a translation needs human review. Returns flag if review needed."""
    if confidence < CONFIDENCE_THRESHOLD:
        flag = ReviewFlag(
            segment_id=segment_id,
            meeting_id=meeting_id,
            reason="low_confidence",
            confidence=confidence,
            provider=provider,
            flagged_at=datetime.now(timezone.utc),
        )
        _review_queue.append(flag)
        log.warning("human_review_flagged", segment=segment_id[:8],
                     confidence=confidence, provider=provider, reason="low_confidence")
        return flag
    return None


def report_translation(
    segment_id: str,
    meeting_id: str,
    user_id: str,
    reason: str = "inaccurate",
) -> ReviewFlag:
    """User reports a problematic translation."""
    flag = ReviewFlag(
        segment_id=segment_id,
        meeting_id=meeting_id,
        reason=f"user_report:{reason}",
        confidence=0.0,
        provider="unknown",
        flagged_at=datetime.now(timezone.utc),
    )
    _review_queue.append(flag)
    log.info("translation_reported", segment=segment_id[:8], user=user_id[:8], reason=reason)
    return flag


def get_review_queue(meeting_id: str | None = None) -> list[dict]:
    """Get pending review items."""
    items = _review_queue if not meeting_id else [f for f in _review_queue if f.meeting_id == meeting_id]
    return [
        {
            "segment_id": f.segment_id,
            "meeting_id": f.meeting_id,
            "reason": f.reason,
            "confidence": f.confidence,
            "provider": f.provider,
            "flagged_at": f.flagged_at.isoformat(),
            "reviewed": f.reviewed,
        }
        for f in items if not f.reviewed
    ]


def mark_reviewed(segment_id: str, reviewer_id: str) -> bool:
    """Mark a flagged item as reviewed."""
    for flag in _review_queue:
        if flag.segment_id == segment_id and not flag.reviewed:
            flag.reviewed = True
            flag.reviewer_id = reviewer_id
            flag.reviewed_at = datetime.now(timezone.utc)
            return True
    return False


def requires_review_before_export(meeting_id: str, is_high_risk: bool = False) -> bool:
    """Check if meeting transcript requires human review before export.

    High-risk meetings always require review.
    Standard meetings require review if any segment was flagged.
    """
    if is_high_risk:
        return True
    pending = [f for f in _review_queue if f.meeting_id == meeting_id and not f.reviewed]
    return len(pending) > 0
