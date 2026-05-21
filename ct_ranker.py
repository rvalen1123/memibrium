"""Crystallization Theory final ranker for Memibrium retrieval candidates.

All retrieval systems should produce candidates; CTRanker applies the
universal lifecycle/governance score and orders the final result set.
"""

from __future__ import annotations

import math
import os
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from ct_scoring import compute_weight


RETRIEVAL_SCORE_FIELDS = (
    "cosine_score",
    "bm25_score",
    "temporal_score",
    "rrf_score",
    "graph_score",
    "leann_score",
    "combined_score",
)

DEFAULT_RETRIEVAL_WEIGHT = float(os.environ.get("CT_RANKER_RETRIEVAL_WEIGHT", "0.55"))
DEFAULT_CT_WEIGHT = float(os.environ.get("CT_RANKER_CT_WEIGHT", "0.45"))
CT_HEAVY_RETRIEVAL_WEIGHT = float(os.environ.get("CT_RANKER_CT_HEAVY_RETRIEVAL_WEIGHT", "0.40"))
CT_HEAVY_CT_WEIGHT = float(os.environ.get("CT_RANKER_CT_HEAVY_CT_WEIGHT", "0.60"))
SHED_PENALTY = float(os.environ.get("CT_RANKER_SHED_PENALTY", "0.20"))
FROZEN_BONUS = float(os.environ.get("CT_RANKER_FROZEN_BONUS", "0.05"))
FEEDBACK_SCALE = float(os.environ.get("CT_RANKER_FEEDBACK_SCALE", "0.05"))
MAX_FEEDBACK_BONUS = float(os.environ.get("CT_RANKER_MAX_FEEDBACK_BONUS", "0.30"))

LIFECYCLE_BASE = {
    None: 0.45,
    "": 0.45,
    "observation": 0.45,
    "consideration": 0.55,
    "accepted": 0.72,
    "crystallized": 0.88,
    "shed": 0.12,
}

MEMORY_TYPE_ADJUSTMENT = {
    "episodic": -0.04,
    "semantic": 0.0,
    "procedural": 0.05,
}


class CTRanker:
    """Final CT governance/ranking layer over arbitrary memory candidates."""

    def __init__(
        self,
        store: Any = None,
        retrieval_weight: Optional[float] = None,
        ct_weight: Optional[float] = None,
        ct_heavy_retrieval_weight: Optional[float] = None,
        ct_heavy_ct_weight: Optional[float] = None,
        now: Optional[datetime] = None,
    ):
        self.store = store
        self.default_retrieval_weight = DEFAULT_RETRIEVAL_WEIGHT if retrieval_weight is None else float(retrieval_weight)
        self.default_ct_weight = DEFAULT_CT_WEIGHT if ct_weight is None else float(ct_weight)
        self.ct_heavy_retrieval_weight = CT_HEAVY_RETRIEVAL_WEIGHT if ct_heavy_retrieval_weight is None else float(ct_heavy_retrieval_weight)
        self.ct_heavy_ct_weight = CT_HEAVY_CT_WEIGHT if ct_heavy_ct_weight is None else float(ct_heavy_ct_weight)
        self.now = now

    @staticmethod
    def _to_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError, ArithmeticError):
            return default

    @staticmethod
    def _clamp(value: Any, default: float = 0.0, low: float = 0.0, high: float = 1.0) -> float:
        numeric = CTRanker._to_float(value, default)
        if numeric is None:
            numeric = default
        return max(low, min(high, numeric))

    @staticmethod
    def _safe_datetime(value: Any, now: datetime) -> datetime:
        if value is None:
            return now
        if isinstance(value, datetime):
            dt = value
        else:
            text = str(value)
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(text)
            except (TypeError, ValueError):
                return now
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _has_witness_chain(candidate: dict) -> bool:
        witness = candidate.get("witness_chain")
        if witness is None:
            return False
        if isinstance(witness, str):
            return bool(witness and witness != "[]")
        if isinstance(witness, (list, tuple, dict)):
            return bool(witness)
        return False

    @staticmethod
    def _infer_sources(candidate: dict) -> list[str]:
        sources: list[str] = []
        existing = candidate.get("retrieval_sources")
        if isinstance(existing, str):
            sources.append(existing)
        elif isinstance(existing, (list, tuple, set)):
            sources.extend(str(s) for s in existing if s)
        source = candidate.get("retrieval_source")
        if source:
            sources.append(str(source))
        field_sources = {
            "cosine_score": "semantic",
            "bm25_score": "lexical",
            "temporal_score": "temporal",
            "rrf_score": "hybrid_rrf",
            "graph_score": "graph",
            "leann_score": "leann",
        }
        for field, label in field_sources.items():
            if candidate.get(field) is not None:
                sources.append(label)
        if candidate.get("combined_score") is not None and not sources:
            sources.append("legacy_combined")
        deduped = []
        seen = set()
        for src in sources:
            if src not in seen:
                deduped.append(src)
                seen.add(src)
        return deduped or ["unknown"]

    def _blend_weights(self, ranking_mode: str) -> tuple[float, float]:
        if ranking_mode in {"ct_heavy", "ct-heavy", "ct"}:
            return self.ct_heavy_retrieval_weight, self.ct_heavy_ct_weight
        return self.default_retrieval_weight, self.default_ct_weight

    def _retrieval_score(self, candidate: dict) -> float:
        raw_scores = []
        for field in RETRIEVAL_SCORE_FIELDS:
            if field not in candidate or candidate.get(field) is None:
                continue
            score = self._to_float(candidate.get(field), None)
            if score is None:
                continue
            # RRF scores are small by design; map typical 0.0-0.1 range into 0-1.
            if field == "rrf_score":
                score = min(max(score * 30.0, 0.0), 1.0)
            # Legacy combined_score can exceed 1; squash without destroying order.
            elif field == "combined_score" and score > 1.0:
                score = score / (1.0 + score)
            else:
                score = max(0.0, min(1.0, score))
            raw_scores.append(score)
        if not raw_scores:
            return 0.0
        # Use max as the primary signal so a strong candidate source is enough,
        # with a small multi-source support bump from the mean.
        return max(0.0, min(1.0, (0.85 * max(raw_scores)) + (0.15 * (sum(raw_scores) / len(raw_scores)))))

    def _ct_score(self, candidate: dict, feedback_score: float, allow_shed: bool, now: datetime) -> tuple[float, float, list[str]]:
        state = candidate.get("state")
        state_key = str(state).lower() if state is not None else None
        confirmation_count = int(self._to_float(candidate.get("confirmation_count"), 0) or 0)
        recency_score = self._clamp(candidate.get("recency_score"), 1.0)
        validation_score = self._clamp(candidate.get("validation_score"), 0.0)
        importance_score = self._clamp(candidate.get("importance_score"), 0.0)
        created_at = self._safe_datetime(candidate.get("created_at"), now)
        w_kt = compute_weight(confirmation_count, recency_score, validation_score, created_at, now)

        lifecycle = LIFECYCLE_BASE.get(state_key, LIFECYCLE_BASE[None])
        w_component = min(1.0, math.log1p(max(w_kt, 0.0)) / math.log1p(5.0))
        confirmation_component = min(1.0, math.log1p(max(confirmation_count, 0)) / math.log1p(5.0))
        mem_type = candidate.get("memory_type") or "semantic"
        type_adjust = MEMORY_TYPE_ADJUSTMENT.get(str(mem_type), 0.0)
        feedback_component = max(-MAX_FEEDBACK_BONUS, min(MAX_FEEDBACK_BONUS, feedback_score * FEEDBACK_SCALE))

        score = (
            0.32 * lifecycle
            + 0.24 * w_component
            + 0.18 * validation_score
            + 0.10 * confirmation_component
            + 0.08 * recency_score
            + 0.08 * importance_score
            + type_adjust
            + feedback_component
        )
        if candidate.get("frozen"):
            score += FROZEN_BONUS
        if state_key == "shed" and not allow_shed:
            score *= SHED_PENALTY

        explanation = [
            f"state={state_key or 'missing'}",
            f"w_kt={w_kt:.4f}",
            f"confirmations={confirmation_count}",
            f"validation={validation_score:.3f}",
            f"recency={recency_score:.3f}",
            f"importance={importance_score:.3f}",
            f"memory_type={mem_type}",
        ]
        if feedback_score:
            explanation.append(f"feedback={feedback_score:.3f}")
        if candidate.get("frozen"):
            explanation.append("frozen_bonus")
        explanation.append("witness_chain_present" if self._has_witness_chain(candidate) else "witness_chain_missing")
        if state_key == "shed" and not allow_shed:
            explanation.append("shed_penalty_applied")
        if candidate.get("retrieval_source") == "leann_text_only":
            explanation.append("leann_text_only_safe_defaults")
        return max(0.0, min(1.0, score)), w_kt, explanation

    async def _feedback_score(self, candidate: dict) -> float:
        if not self.store or not hasattr(self.store, "get_memory_feedback_score"):
            return 0.0
        memory_id = candidate.get("id") or candidate.get("memory_id")
        if not memory_id:
            return 0.0
        try:
            return float(await self.store.get_memory_feedback_score(memory_id))
        except Exception:
            return 0.0

    async def rank(
        self,
        candidates: list[dict],
        top_k: Optional[int] = None,
        *,
        ranking_mode: str = "general",
        allow_shed: bool = False,
        include_telemetry: bool = False,
    ):
        """Return candidates ordered by authoritative CT-governed final_score."""
        now = self.now or datetime.now(timezone.utc)
        retrieval_weight, ct_weight = self._blend_weights(ranking_mode)
        total_weight = retrieval_weight + ct_weight
        if total_weight <= 0:
            retrieval_weight, ct_weight, total_weight = 0.55, 0.45, 1.0
        retrieval_weight /= total_weight
        ct_weight /= total_weight

        ranked = []
        for candidate in candidates or []:
            item = deepcopy(dict(candidate))
            if "combined_score" in item and "source_combined_score" not in item:
                item["source_combined_score"] = item.get("combined_score")
            retrieval_score = self._retrieval_score(item)
            feedback_score = await self._feedback_score(item)
            ct_score, w_kt, explanation_parts = self._ct_score(item, feedback_score, allow_shed, now)
            final_score = (retrieval_weight * retrieval_score) + (ct_weight * ct_score)

            sources = self._infer_sources(item)
            item["retrieval_sources"] = sources
            item["retrieval_score"] = round(retrieval_score, 6)
            item["w_kt"] = round(w_kt, 6)
            item["ct_score"] = round(ct_score, 6)
            item["final_score"] = round(final_score, 6)
            if feedback_score:
                item["feedback_score"] = round(feedback_score, 6)
            item["ranking_path"] = f"candidate_retrieval->ct_ranker:{ranking_mode}"
            item["rank_explanation"] = "; ".join(
                [
                    f"retrieval_score={retrieval_score:.4f}",
                    f"ct_score={ct_score:.4f}",
                    f"blend={retrieval_weight:.2f}/{ct_weight:.2f}",
                    f"sources={','.join(sources)}",
                ]
                + explanation_parts
            )
            ranked.append(item)

        ranked.sort(key=lambda x: (x.get("final_score", 0.0), x.get("retrieval_score", 0.0), str(x.get("id", ""))), reverse=True)
        returned = ranked[:top_k] if top_k is not None else ranked
        if not include_telemetry:
            return returned
        telemetry = self.telemetry(
            ranked=returned,
            candidate_count=len(candidates or []),
            ranking_mode=ranking_mode,
            retrieval_weight=retrieval_weight,
            ct_weight=ct_weight,
        )
        return returned, telemetry

    def telemetry(
        self,
        *,
        ranked: list[dict],
        candidate_count: int,
        ranking_mode: str,
        retrieval_weight: Optional[float] = None,
        ct_weight: Optional[float] = None,
    ) -> dict:
        if retrieval_weight is None or ct_weight is None:
            retrieval_weight, ct_weight = self._blend_weights(ranking_mode)
        return {
            "schema": "memibrium.ct_ranking.telemetry.v1",
            "candidate_count_before_ct": candidate_count,
            "returned_count_after_ct": len(ranked),
            "top_ranked_ids": [item.get("id") for item in ranked],
            "blend_weights": {"retrieval": retrieval_weight, "ct": ct_weight},
            "ranking_mode": ranking_mode,
            "score_components": [
                {
                    "id": item.get("id"),
                    "retrieval_score": item.get("retrieval_score"),
                    "ct_score": item.get("ct_score"),
                    "final_score": item.get("final_score"),
                    "w_kt": item.get("w_kt"),
                    "state": item.get("state"),
                    "memory_type": item.get("memory_type"),
                    "confirmation_count": item.get("confirmation_count"),
                    "validation_score": item.get("validation_score"),
                    "recency_score": item.get("recency_score"),
                    "feedback_score": item.get("feedback_score"),
                    "retrieval_sources": item.get("retrieval_sources"),
                }
                for item in ranked
            ],
        }
