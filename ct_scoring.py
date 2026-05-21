"""Crystallization Theory scoring primitives for Memibrium.

This module is intentionally small and dependency-light so storage,
retrieval, and API layers can all share the same W(k,t) implementation
without importing the server monolith.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _coerce_datetime(value: Any, now: Optional[datetime] = None) -> datetime:
    """Return a timezone-aware datetime for scoring age calculations."""
    if value is None:
        return now or datetime.now(timezone.utc)
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_weight(
    confirmation_count: int,
    recency_score: float,
    validation_score: float,
    created_at: Any,
    now: Optional[datetime] = None,
) -> float:
    """
    W(k,t) = (C × R × V) / A

    CT core formula. Drives retrieval ranking and shedding.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        c = max(int(confirmation_count), 1)
    except (TypeError, ValueError):
        c = 1
    try:
        r = float(recency_score)
    except (TypeError, ValueError):
        r = 1.0
    try:
        v = max(float(validation_score), 0.1)
    except (TypeError, ValueError):
        v = 0.1
    created = _coerce_datetime(created_at, now=now)
    age_hours = max((now - created).total_seconds() / 3600, 1.0)
    return (c * r * v) / age_hours
