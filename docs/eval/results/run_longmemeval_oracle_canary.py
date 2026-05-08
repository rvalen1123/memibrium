#!/usr/bin/env python3
"""Preparation-only LongMemEval oracle canary harness for Memibrium.

This script validates the preregistered 25-row oracle slice and writes
placeholder prediction files in upstream LongMemEval JSONL shape. It deliberately
refuses answer generation unless a future explicit launch path is implemented.

It does not call LLMs, judge answers, ingest memories, mutate DB/Docker/runtime
state, or run full LongMemEval.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "docs/eval/results"
DEFAULT_DATASET_PATH = Path("/tmp/longmemeval-cleaned-pin/longmemeval_oracle.json")
DEFAULT_SELECTION_PATH = RESULTS_DIR / "longmemeval_oracle_canary_25_selection_20260508.json"
EXPECTED_HF_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
EXPECTED_ORACLE_SHA256 = "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"
EXPECTED_SELECTION_SEED = "memibrium-longmemeval-oracle-canary-2026-05-08-v1"
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ANSWER_SHAPE_TYPES = {"multi-session", "temporal-reasoning"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False), file=f)


def validate_selection(dataset: list[dict[str, Any]], selection: dict[str, Any], *, dataset_sha256: str) -> dict[str, Any]:
    if selection.get("hf_revision") != EXPECTED_HF_REVISION:
        raise ValueError(f"hf_revision_mismatch: {selection.get('hf_revision')}")
    if selection.get("source_sha256") != dataset_sha256:
        raise ValueError(
            f"source_sha256_mismatch: selection={selection.get('source_sha256')} dataset={dataset_sha256}"
        )
    if "seed" in selection and selection.get("seed") != EXPECTED_SELECTION_SEED:
        raise ValueError(f"selection_seed_mismatch:{selection.get('seed')}")
    rows = selection.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("selection_rows_invalid")

    by_id = {entry.get("question_id"): entry for entry in dataset}
    seen: set[str] = set()
    qtype_counts: dict[str, int] = {}
    abstention_count = 0
    proof_rows = []
    for expected_index, row in enumerate(rows, start=1):
        question_id = row.get("question_id")
        if not question_id:
            raise ValueError(f"missing_question_id:index={expected_index}")
        if question_id in seen:
            raise ValueError(f"duplicate_question_id:{question_id}")
        seen.add(question_id)
        source = by_id.get(question_id)
        if source is None:
            raise ValueError(f"question_id_not_found:{question_id}")
        if row.get("selection_index") != expected_index:
            raise ValueError(f"selection_index_mismatch:{question_id}")
        question_type = source.get("question_type")
        if row.get("question_type") != question_type:
            raise ValueError(f"question_type_mismatch:{question_id}")
        abstention = str(question_id).endswith("_abs")
        if bool(row.get("abstention")) != abstention:
            raise ValueError(f"abstention_flag_mismatch:{question_id}")
        expected_selection_hash = sha256_text(
            f"{selection.get('seed', EXPECTED_SELECTION_SEED)}:{question_id}:{source.get('question', '')}"
        )
        if row.get("selection_hash") != expected_selection_hash:
            raise ValueError(f"selection_hash_mismatch:{question_id}")
        if "selection_group" in row:
            actual_group = row.get("selection_group")
            allowed_groups = {f"{question_type}:hash-fill"}
            if abstention:
                allowed_groups.add(f"{question_type}:reserved-abstention")
            else:
                allowed_groups.add(f"{question_type}:non-abstention-fill")
            if question_type == "knowledge-update" and expected_index > 4 and not abstention:
                allowed_groups.add(f"{question_type}:extra-product-telemetry")
            if actual_group not in allowed_groups:
                raise ValueError(f"selection_group_mismatch:{question_id}")
        qtype_counts[question_type] = qtype_counts.get(question_type, 0) + 1
        abstention_count += 1 if abstention else 0
        proof_rows.append({
            "selection_index": expected_index,
            "question_id": question_id,
            "question_type": question_type,
            "abstention": abstention,
            "question_sha256": sha256_text(source.get("question", "")),
            "selection_hash": expected_selection_hash,
        })

    counts = selection.get("counts") or {}
    if counts.get("total") != len(rows):
        raise ValueError(f"selection_total_mismatch:{counts.get('total')} != {len(rows)}")
    if counts.get("abstention") != abstention_count:
        raise ValueError(f"selection_abstention_mismatch:{counts.get('abstention')} != {abstention_count}")
    if counts.get("by_question_type") != qtype_counts:
        raise ValueError(f"selection_qtype_counts_mismatch:{counts.get('by_question_type')} != {qtype_counts}")

    return {
        "ok": True,
        "row_count": len(rows),
        "question_type_counts": qtype_counts,
        "abstention_count": abstention_count,
        "rows": proof_rows,
    }


def render_evidence(row: dict[str, Any]) -> tuple[str, str]:
    session_ids = row.get("haystack_session_ids") or []
    sessions = row.get("haystack_sessions") or []
    dates = row.get("haystack_dates") or []
    chunks: list[str] = []
    for session_index, turns in enumerate(sessions):
        session_id = session_ids[session_index] if session_index < len(session_ids) else f"session_{session_index + 1}"
        date = dates[session_index] if session_index < len(dates) else "unknown-date"
        chunks.append(f"[session {session_id} | date {date}]")
        for turn_index, turn in enumerate(turns or [], start=1):
            role = turn.get("role", "unknown")
            has_answer = turn.get("has_answer")
            content = turn.get("content", "")
            chunks.append(f"[session {session_id} | turn {turn_index} | {role} | has_answer={has_answer}] {content}")
    evidence_text = "\n".join(chunks)
    return evidence_text, sha256_text(evidence_text)


def build_oracle_prompt(row: dict[str, Any], *, treatment: bool) -> dict[str, Any]:
    evidence_text, evidence_hash = render_evidence(row)
    qtype = row.get("question_type", "")
    directives = [
        "Use only the oracle evidence below.",
        "If the evidence is insufficient, say the information provided is not enough.",
        "Answer concisely and do not invent facts.",
    ]
    if treatment and qtype in ANSWER_SHAPE_TYPES:
        directives.append(
            "Answer with the exact items, counts, names, or dates requested; include all required parts rather than a partial subset."
        )
    if treatment and qtype == "knowledge-update":
        directives.append("Prefer the latest updated fact when the evidence contains stale and newer information.")
    if treatment and str(row.get("question_id", "")).endswith("_abs"):
        directives.append("For unanswerable questions, explicitly state that the evidence is insufficient.")

    prompt = "\n".join([
        "LongMemEval oracle answer task.",
        "\n".join(f"- {item}" for item in directives),
        "",
        f"Question date: {row.get('question_date', '')}",
        f"Question type: {qtype}",
        f"Question: {row.get('question', '')}",
        "",
        "Oracle evidence:",
        evidence_text,
        "",
        "Answer:",
    ])
    return {
        "question_id": row.get("question_id"),
        "question_type": qtype,
        "abstention": str(row.get("question_id", "")).endswith("_abs"),
        "evidence_session_ids": list(row.get("haystack_session_ids") or []),
        "answer_session_ids": list(row.get("answer_session_ids") or []),
        "evidence_hash": evidence_hash,
        "prompt": prompt,
        "prompt_sha256": sha256_text(prompt),
        "metadata_projection": "no-op",
    }


def prepare_oracle_canary(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    out_dir: Path,
    *,
    allow_answer_generation: bool = False,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
) -> dict[str, Any]:
    if allow_answer_generation:
        raise ValueError("answer_generation_requires_explicit_launch_path_not_implemented")
    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    by_id = {entry["question_id"]: entry for entry in dataset}
    selected_rows = [by_id[row["question_id"]] for row in selection["rows"]]

    baseline_prompts = [build_oracle_prompt(row, treatment=False) for row in selected_rows]
    treatment_prompts = [build_oracle_prompt(row, treatment=True) for row in selected_rows]
    baseline_jsonl = [{"question_id": item["question_id"], "hypothesis": ""} for item in baseline_prompts]
    treatment_jsonl = [{"question_id": item["question_id"], "hypothesis": ""} for item in treatment_prompts]

    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = out_dir / "longmemeval_oracle_canary_baseline_placeholder.jsonl"
    treatment_path = out_dir / "longmemeval_oracle_canary_treatment_placeholder.jsonl"
    metadata_path = out_dir / "longmemeval_oracle_canary_preparation_metadata.json"
    write_jsonl(baseline_path, baseline_jsonl)
    write_jsonl(treatment_path, treatment_jsonl)
    metadata = {
        "mode": "preparation_only_no_answer_generation",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "selection_proof": proof,
        "baseline_prediction_file": str(baseline_path),
        "treatment_prediction_file": str(treatment_path),
        "baseline_prompts": baseline_prompts,
        "treatment_prompts": treatment_prompts,
        "judge_target": {
            "provider": "Azure AI Foundry Sector 7",
            "model": "gpt-4o",
            "version": "2024-11-20",
            "temperature": 0,
        },
        "guardrails": [
            "no answer generation",
            "no judging",
            "no benchmark score",
            "no DB/Docker/runtime mutation",
        ],
    }
    write_json(metadata_path, metadata)
    return {
        "mode": "preparation_only_no_answer_generation",
        "row_count": proof["row_count"],
        "baseline_prediction_file": str(baseline_path),
        "treatment_prediction_file": str(treatment_path),
        "metadata_file": str(metadata_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare LongMemEval oracle canary placeholder artifacts without model calls.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION_PATH)
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR / f"longmemeval_oracle_canary_prepare_{RUN_ID}")
    parser.add_argument("--allow-answer-generation", action="store_true", help="Reserved for future explicit launch path; currently refuses.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_sha256 = sha256_file(args.dataset)
    dataset = load_json(args.dataset)
    selection = load_json(args.selection)
    result = prepare_oracle_canary(
        dataset,
        selection,
        args.out_dir,
        allow_answer_generation=args.allow_answer_generation,
        dataset_sha256=dataset_sha256,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
