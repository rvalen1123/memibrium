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
import asyncio
import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "docs/eval/results"
DEFAULT_DATASET_PATH = Path("/tmp/longmemeval-cleaned-pin/longmemeval_oracle.json")
DEFAULT_SELECTION_PATH = RESULTS_DIR / "longmemeval_oracle_canary_25_selection_20260508.json"
EXPECTED_HF_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
EXPECTED_ORACLE_SHA256 = "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"
EXPECTED_SELECTION_SEED = "memibrium-longmemeval-oracle-canary-2026-05-08-v1"
SECOND_SLICE_SELECTION_SEED = "memibrium-longmemeval-oracle-canary-2026-05-08-v2"
ALLOWED_SELECTION_SEEDS = {EXPECTED_SELECTION_SEED, SECOND_SLICE_SELECTION_SEED}
SECOND_SLICE_GATES = {
    "total_score": "category_contract_v1 >= baseline on the same slice",
    "knowledge_update": "knowledge-update >= baseline on the same slice",
    "preference_recovery": "preference_recovered / preference_baseline_wrong >= 50%",
    "preference_recovery_zero_denominator": "if preference_baseline_wrong == 0, preference gate is automatically satisfied because no recovery is needed",
    "moved_row_minimum": "moved_rows = recovered + regressed >= 3",
    "moved_row_win_loss": "moved_rows >= 3 and recovered/regressed >= 2:1",
    "moved_row_win_loss_rationale": "2:1 is the minimum ratio that still constitutes evidence of a working mechanism rather than noise; neutral movement is not replication evidence",
    "zero_movement": "moved_rows == 0 fails the replication/mechanism gate",
    "category_collapse": "no non-watch category drops by more than one row",
    "communication_boundary": "oracle answer-side mechanism evidence only; no retrieval/product benchmark claim",
}
RETRIEVAL_BRIDGE_CONDITION = "longmemeval_bridge_v1_retrieval_plus_category_contract_v1"
RETRIEVAL_BRIDGE_DOMAIN = "longmemeval-bridge-v1-20260508-second-slice"
RETRIEVAL_BRIDGE_SELECTION_SHA256 = "9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb"
RETRIEVAL_BRIDGE_PHASE_A_GATES = {
    "coverage_audit_completeness": "25/25 rows have a coverage class and preserved retrieval artifacts",
    "retrieval_operational_success": "no uncaught 500s, serialization errors, or missing JSON fields",
    "preference_coverage": "at least 3/4 single-session-preference rows are gold_supported or gold_supported_with_conflict",
    "knowledge_update_coverage": "at least 3/5 knowledge-update rows are gold_supported, gold_supported_with_conflict, or partial_support; stale_only counted separately",
    "abstention_contamination": "no more than 1/4 abstention rows may be unanswerable_contaminated",
    "evidence_identity": "every answerable row preserves source refs sufficient for artifact-only review",
}
RETRIEVAL_COVERAGE_CLASSES = {
    "gold_supported",
    "gold_supported_with_conflict",
    "partial_support",
    "stale_only",
    "adjacent_entity_only",
    "unsupported",
    "unanswerable_supported",
    "unanswerable_contaminated",
}
PREFERENCE_COVERAGE_PASS_CLASSES = {"gold_supported", "gold_supported_with_conflict"}
KNOWLEDGE_UPDATE_COVERAGE_PASS_CLASSES = {
    "gold_supported",
    "gold_supported_with_conflict",
    "partial_support",
}
RETRIEVAL_ROW_REQUIRED_FIELDS = {
    "question_id",
    "question_type",
    "coverage_class",
    "retrieval_status",
    "retrieved_memory_ids",
    "source_refs",
    "fallback_error_flags",
}
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ANSWER_SHAPE_TYPES = {"multi-session", "temporal-reasoning"}
DEFAULT_CANDIDATE_CONDITION = "locked_answer_shape"
SUPPORTED_CANDIDATE_CONDITIONS = {"locked_answer_shape", "category_contract_v1"}


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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"jsonl_decode_error:{path}:{line_number}:{exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"jsonl_row_not_object:{path}:{line_number}")
            rows.append(row)
    return rows


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("export ").strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def endpoint_metadata(endpoint: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(endpoint or "")
    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
        "configured": bool(endpoint),
    }


def chat_completions_call(
    messages: list[dict[str, str]],
    *,
    model: str,
    max_tokens: int,
    endpoint: str | None = None,
    api_key: str | None = None,
    retries: int = 3,
) -> str:
    endpoint = (endpoint or os.environ.get("AZURE_CHAT_ENDPOINT") or "https://sector-7.services.ai.azure.com").rstrip("/")
    api_key = api_key or os.environ.get("AZURE_CHAT_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("missing_azure_chat_api_key")
    url = f"{endpoint}/models/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode("utf-8")
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("empty_chat_completion_content")
            return content.strip()
        except Exception as exc:  # pragma: no cover - network path covered by live run
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            if isinstance(exc, urllib.error.HTTPError):
                body = exc.read().decode("utf-8", errors="replace")[:1000]
                raise RuntimeError(f"azure_chat_http_error:{exc.code}:{body}") from exc
            raise RuntimeError(f"azure_chat_call_failed:{exc}") from exc
    raise RuntimeError(f"azure_chat_call_failed:{last_error}")


def build_judge_prompt(row: dict[str, Any], hypothesis: str) -> str:
    question_type = row.get("question_type")
    question = row.get("question", "")
    answer = row.get("answer", "")
    if str(row.get("question_id", "")).endswith("_abs"):
        template = "I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes if the model correctly identifies the question as unanswerable. The model could say that the information is incomplete, or some other information is given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? Answer yes or no only."
        return template.format(question, answer, hypothesis)
    if question_type in ["single-session-user", "single-session-assistant", "multi-session"]:
        template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
    elif question_type == "temporal-reasoning":
        template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. In addition, do not penalize off-by-one errors for the number of days. If the question asks for the number of days/weeks/months, etc., and the model makes off-by-one errors (e.g., predicting 19 days when the answer is 18), the model's response is still correct. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
    elif question_type == "knowledge-update":
        template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response contains some previous information along with an updated answer, the response should be considered as correct as long as the updated answer is the required answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
    elif question_type == "single-session-preference":
        template = "I will give you a question, a rubric for desired personalized response, and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes the user's personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
    else:
        raise ValueError(f"unsupported_question_type:{question_type}")
    return template.format(question, answer, hypothesis)


def evaluate_predictions(
    selected_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    chat_fn: Callable[..., str],
    judge_model: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id = {row["question_id"]: row for row in selected_rows}
    eval_rows = []
    by_type: dict[str, list[bool]] = {}
    for prediction in predictions:
        row = by_id[prediction["question_id"]]
        prompt = build_judge_prompt(row, prediction["hypothesis"])
        response = chat_fn([{"role": "user", "content": prompt}], model=judge_model, max_tokens=10)
        label = "yes" in response.lower()
        qtype = row.get("question_type", "")
        by_type.setdefault(qtype, []).append(label)
        eval_rows.append({
            "question_id": prediction["question_id"],
            "hypothesis": prediction["hypothesis"],
            "autoeval_label": {
                "model": judge_model,
                "version": "2024-11-20",
                "label": label,
                "raw_response": response,
            },
        })
    labels = [item["autoeval_label"]["label"] for item in eval_rows]
    summary = {
        "accuracy": sum(1 for label in labels if label) / len(labels) if labels else 0.0,
        "correct": sum(1 for label in labels if label),
        "total": len(labels),
        "by_question_type": {
            qtype: {
                "accuracy": sum(1 for label in labels if label) / len(labels) if labels else 0.0,
                "correct": sum(1 for label in labels if label),
                "total": len(labels),
            }
            for qtype, labels in sorted(by_type.items())
        },
    }
    return eval_rows, summary


def generate_predictions(
    prompts: list[dict[str, Any]],
    *,
    chat_fn: Callable[..., str],
    answer_model: str,
) -> list[dict[str, str]]:
    predictions = []
    for item in prompts:
        hypothesis = chat_fn([{"role": "user", "content": item["prompt"]}], model=answer_model, max_tokens=256)
        predictions.append({"question_id": item["question_id"], "hypothesis": hypothesis})
    return predictions


def eval_label(row: dict[str, Any]) -> bool:
    qid = row.get("question_id", "<missing_question_id>")
    if "autoeval_label" not in row or not isinstance(row.get("autoeval_label"), dict):
        raise ValueError(f"missing_autoeval_label:{qid}")
    if "label" not in row["autoeval_label"]:
        raise ValueError(f"missing_autoeval_label:{qid}")
    label = row["autoeval_label"]["label"]
    if isinstance(label, bool):
        return label
    if isinstance(label, str):
        normalized = label.strip().lower()
        if normalized in {"yes", "true", "1"}:
            return True
        if normalized in {"no", "false", "0"}:
            return False
        raise ValueError(f"invalid_autoeval_label:{qid}")
    if isinstance(label, int) and label in {0, 1}:
        return bool(label)
    raise ValueError(f"invalid_autoeval_label:{qid}")


def duplicate_question_ids(rows: list[dict[str, Any]]) -> list[str]:
    seen = set()
    duplicates = set()
    for row in rows:
        qid = row.get("question_id")
        if qid in seen:
            duplicates.add(qid)
        seen.add(qid)
    return sorted(qid for qid in duplicates if qid is not None)


def validate_eval_rows_for_selection(
    selected_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    prefix = f"{label}_" if label else ""
    duplicates = duplicate_question_ids(eval_rows)
    if duplicates:
        raise ValueError(f"duplicate_{prefix}eval_rows:{','.join(duplicates)}")
    source_ids = [row["question_id"] for row in selected_rows]
    by_eval_id = {row["question_id"]: row for row in eval_rows}
    missing = sorted(set(source_ids) - set(by_eval_id))
    extra = sorted(set(by_eval_id) - set(source_ids))
    if missing:
        raise ValueError(f"missing_{prefix}eval_rows:{','.join(missing)}")
    if extra:
        raise ValueError(f"unknown_{prefix}eval_rows:{','.join(extra)}")
    for qid in source_ids:
        eval_label(by_eval_id[qid])
    return by_eval_id


def summarize_labels(selected_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source_id = {row["question_id"]: row for row in selected_rows}
    by_eval_id = validate_eval_rows_for_selection(selected_rows, eval_rows, label="")

    labels_by_type: dict[str, list[bool]] = {}
    for row in selected_rows:
        qid = row["question_id"]
        qtype = row.get("question_type", "")
        labels_by_type.setdefault(qtype, []).append(eval_label(by_eval_id[qid]))
    labels = [label for qtype_labels in labels_by_type.values() for label in qtype_labels]
    return {
        "correct": sum(1 for label in labels if label),
        "total": len(labels),
        "accuracy": sum(1 for label in labels if label) / len(labels) if labels else 0.0,
        "by_question_type": {
            qtype: {
                "correct": sum(1 for label in labels if label),
                "total": len(labels),
                "accuracy": sum(1 for label in labels if label) / len(labels) if labels else 0.0,
            }
            for qtype, labels in sorted(labels_by_type.items())
        },
    }


def evaluate_second_slice_gates(
    selected_rows: list[dict[str, Any]],
    baseline_eval_rows: list[dict[str, Any]],
    treatment_eval_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_by_id = validate_eval_rows_for_selection(selected_rows, baseline_eval_rows, label="baseline")
    treatment_by_id = validate_eval_rows_for_selection(selected_rows, treatment_eval_rows, label="treatment")
    source_ids = [row["question_id"] for row in selected_rows]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("duplicate_selected_question_id")

    baseline_summary = summarize_labels(selected_rows, baseline_eval_rows)
    treatment_summary = summarize_labels(selected_rows, treatment_eval_rows)
    outcomes = {"same_correct": 0, "same_wrong": 0, "recovered": 0, "regressed": 0, "moved_rows": 0}
    preference_baseline_wrong = 0
    preference_recovered = 0
    paired_rows = []
    for row in selected_rows:
        qid = row["question_id"]
        qtype = row.get("question_type", "")
        baseline_correct = eval_label(baseline_by_id[qid])
        treatment_correct = eval_label(treatment_by_id[qid])
        if baseline_correct and treatment_correct:
            outcome = "same_correct"
        elif not baseline_correct and not treatment_correct:
            outcome = "same_wrong"
        elif not baseline_correct and treatment_correct:
            outcome = "recovered"
        else:
            outcome = "regressed"
        outcomes[outcome] += 1
        if outcome in {"recovered", "regressed"}:
            outcomes["moved_rows"] += 1
        if qtype == "single-session-preference":
            if not baseline_correct:
                preference_baseline_wrong += 1
            if outcome == "recovered":
                preference_recovered += 1
        paired_rows.append({
            "question_id": qid,
            "question_type": qtype,
            "baseline_correct": baseline_correct,
            "treatment_correct": treatment_correct,
            "outcome": outcome,
        })

    recovered = outcomes["recovered"]
    regressed = outcomes["regressed"]
    moved_rows = outcomes["moved_rows"]
    if preference_baseline_wrong == 0:
        preference_pass = True
        preference_reason = "zero_denominator_no_recovery_needed"
        preference_rate = None
    else:
        preference_rate = preference_recovered / preference_baseline_wrong
        preference_pass = preference_rate >= 0.5
        preference_reason = "ok" if preference_pass else "preference_recovery_below_50_percent"

    if moved_rows < 3:
        movement_pass = False
        movement_reason = "minimum_moved_rows_not_met"
    elif regressed == 0:
        movement_pass = recovered > 0
        movement_reason = "ok" if movement_pass else "zero_movement"
    elif recovered / regressed >= 2:
        movement_pass = True
        movement_reason = "ok"
    else:
        movement_pass = False
        movement_reason = "recovered_regressed_ratio_below_2_to_1"

    non_watch_drops = {}
    watch_categories = {"knowledge-update"}
    for qtype, baseline_type in baseline_summary["by_question_type"].items():
        treatment_type = treatment_summary["by_question_type"].get(qtype, {"correct": 0})
        delta = treatment_type["correct"] - baseline_type["correct"]
        if qtype not in watch_categories and delta < -1:
            non_watch_drops[qtype] = delta

    knowledge_baseline = baseline_summary["by_question_type"].get("knowledge-update", {"correct": 0, "total": 0})
    knowledge_treatment = treatment_summary["by_question_type"].get("knowledge-update", {"correct": 0, "total": 0})
    gates = {
        "total_score": {
            "pass": treatment_summary["correct"] >= baseline_summary["correct"],
            "baseline_correct": baseline_summary["correct"],
            "treatment_correct": treatment_summary["correct"],
        },
        "knowledge_update": {
            "pass": knowledge_treatment["correct"] >= knowledge_baseline["correct"],
            "baseline_correct": knowledge_baseline["correct"],
            "treatment_correct": knowledge_treatment["correct"],
        },
        "preference_recovery": {
            "pass": preference_pass,
            "reason": preference_reason,
            "recovered": preference_recovered,
            "baseline_wrong": preference_baseline_wrong,
            "rate": preference_rate,
        },
        "moved_row_stability": {
            "pass": movement_pass,
            "reason": movement_reason,
            "moved_rows": moved_rows,
            "recovered": recovered,
            "regressed": regressed,
        },
        "category_collapse": {
            "pass": not non_watch_drops,
            "drops": non_watch_drops,
        },
    }
    gates["overall"] = {"pass": all(gate["pass"] for gate in gates.values())}
    return {
        "mode": "second_slice_gate_evaluation_offline",
        "gates": gates,
        "baseline": baseline_summary,
        "treatment": treatment_summary,
        "paired_outcomes": outcomes,
        "preference": {
            "baseline_wrong": preference_baseline_wrong,
            "recovered": preference_recovered,
            "recovery_rate": preference_rate,
        },
        "paired_rows": paired_rows,
        "preregistered_gates": SECOND_SLICE_GATES,
        "communication_boundary": "oracle answer-side mechanism evidence only; retrieval untested",
    }


def write_second_slice_gate_report(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    baseline_eval_file: Path,
    treatment_eval_file: Path,
    report_file: Path,
    *,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
) -> dict[str, Any]:
    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    by_id = {entry["question_id"]: entry for entry in dataset}
    selected_rows = [by_id[row["question_id"]] for row in selection["rows"]]
    baseline_eval_rows = load_jsonl(baseline_eval_file)
    treatment_eval_rows = load_jsonl(treatment_eval_file)
    report = evaluate_second_slice_gates(selected_rows, baseline_eval_rows, treatment_eval_rows)
    report.update({
        "selection_proof": proof,
        "input_files": {
            "baseline_eval_file": str(baseline_eval_file),
            "treatment_eval_file": str(treatment_eval_file),
            "selection_file": str(selection.get("_selection_file", "")),
        },
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "guardrails": [
            "offline existing eval labels only",
            "no answer generation",
            "no judging/model calls",
            "no prompt retuning",
            "no retrieval ingestion",
            "no DB/Docker/runtime mutation",
        ],
    })
    write_json(report_file, report)
    return report


def validate_selection(dataset: list[dict[str, Any]], selection: dict[str, Any], *, dataset_sha256: str) -> dict[str, Any]:
    if selection.get("hf_revision") != EXPECTED_HF_REVISION:
        raise ValueError(f"hf_revision_mismatch: {selection.get('hf_revision')}")
    if selection.get("source_sha256") != dataset_sha256:
        raise ValueError(
            f"source_sha256_mismatch: selection={selection.get('source_sha256')} dataset={dataset_sha256}"
        )
    seed = selection.get("seed", EXPECTED_SELECTION_SEED)
    if seed not in ALLOWED_SELECTION_SEEDS:
        raise ValueError(f"selection_seed_mismatch:{seed}")
    prior_slice_ids = set(selection.get("prior_slice_question_ids") or [])
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
        if question_id in prior_slice_ids:
            raise ValueError(f"prior_slice_overlap:{question_id}")
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
            f"{seed}:{question_id}:{source.get('question', '')}"
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
        "slice_id": selection.get("slice_id"),
        "seed": seed,
        "prior_slice_overlap_count": len(seen & prior_slice_ids),
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


def build_oracle_prompt(
    row: dict[str, Any],
    *,
    treatment: bool | None = None,
    condition: str | None = None,
) -> dict[str, Any]:
    if condition is None:
        condition = "locked_answer_shape" if treatment else "baseline"
    if condition == "baseline":
        treatment = False
    elif condition == "locked_answer_shape":
        treatment = True
    elif condition == "category_contract_v1":
        treatment = False
    else:
        raise ValueError(f"unsupported_prompt_condition:{condition}")

    evidence_text, evidence_hash = render_evidence(row)
    qtype = row.get("question_type", "")
    directives = [
        "Use only the oracle evidence below.",
        "If the evidence is insufficient, say the information provided is not enough.",
        "Answer concisely and do not invent facts.",
    ]
    if condition == "locked_answer_shape":
        if qtype in ANSWER_SHAPE_TYPES:
            directives.append(
                "Answer with the exact items, counts, names, or dates requested; include all required parts rather than a partial subset."
            )
        if qtype == "knowledge-update":
            directives.append("Prefer the latest updated fact when the evidence contains stale and newer information.")
        if str(row.get("question_id", "")).endswith("_abs"):
            directives.append("For unanswerable questions, explicitly state that the evidence is insufficient.")
    elif condition == "category_contract_v1":
        if qtype == "single-session-preference":
            directives.extend([
                "Use recommender/advisor mode: provide helpful personalized suggestions grounded in the oracle evidence.",
                "Do not say the information provided is not enough merely because no concrete local events, venues, products, or schedules are present; use remembered preferences to shape the recommendation.",
            ])
        elif qtype == "knowledge-update":
            directives.extend([
                "Use the latest matching fact when stale and newer evidence describe the same asked entity and attribute.",
                "Do not substitute adjacent entities; if the asked entity or attribute is absent, state that the evidence is insufficient.",
            ])
        elif qtype == "multi-session":
            directives.append(
                "For numeric or list questions, combine all relevant evidence items across sessions and avoid partial subsets."
            )
        elif qtype == "temporal-reasoning":
            directives.append(
                "Use dates in the evidence for temporal arithmetic; return the supported duration, date, or activity when the evidence supports it."
            )

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
        "condition": condition,
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
    chat_fn: Callable[..., str] | None = None,
    answer_model: str = "gpt-4o",
    judge_model: str = "gpt-4o",
    endpoint_metadata: dict[str, Any] | None = None,
    condition: str = DEFAULT_CANDIDATE_CONDITION,
) -> dict[str, Any]:
    if condition not in SUPPORTED_CANDIDATE_CONDITIONS:
        raise ValueError(f"unsupported_candidate_condition:{condition}")
    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    by_id = {entry["question_id"]: entry for entry in dataset}
    selected_rows = [by_id[row["question_id"]] for row in selection["rows"]]

    baseline_prompts = [build_oracle_prompt(row, condition="baseline") for row in selected_rows]
    treatment_prompts = [build_oracle_prompt(row, condition=condition) for row in selected_rows]
    out_dir.mkdir(parents=True, exist_ok=True)

    if allow_answer_generation:
        if chat_fn is None:
            chat_fn = chat_completions_call
        baseline_jsonl = generate_predictions(baseline_prompts, chat_fn=chat_fn, answer_model=answer_model)
        treatment_jsonl = generate_predictions(treatment_prompts, chat_fn=chat_fn, answer_model=answer_model)
        baseline_path = out_dir / "longmemeval_oracle_canary_baseline_predictions.jsonl"
        treatment_path = out_dir / "longmemeval_oracle_canary_treatment_predictions.jsonl"
        baseline_eval_path = out_dir / "longmemeval_oracle_canary_baseline_eval_results.jsonl"
        treatment_eval_path = out_dir / "longmemeval_oracle_canary_treatment_eval_results.jsonl"
        metadata_path = out_dir / "longmemeval_oracle_canary_scored_metadata.json"
        summary_path = out_dir / "longmemeval_oracle_canary_scored_summary.json"
        write_jsonl(baseline_path, baseline_jsonl)
        write_jsonl(treatment_path, treatment_jsonl)
        baseline_evals, baseline_summary = evaluate_predictions(
            selected_rows, baseline_jsonl, chat_fn=chat_fn, judge_model=judge_model
        )
        treatment_evals, treatment_summary = evaluate_predictions(
            selected_rows, treatment_jsonl, chat_fn=chat_fn, judge_model=judge_model
        )
        write_jsonl(baseline_eval_path, baseline_evals)
        write_jsonl(treatment_eval_path, treatment_evals)
        summary = {
            "mode": "scored_oracle_canary",
            "condition": condition,
            "row_count": proof["row_count"],
            "baseline": baseline_summary,
            "treatment": treatment_summary,
            "answer_model": {"model": answer_model, "temperature": 0},
            "judge_model": {"model": judge_model, "version": "2024-11-20", "temperature": 0},
            "selection_sha256": sha256_file(DEFAULT_SELECTION_PATH) if DEFAULT_SELECTION_PATH.exists() else None,
        }
        metadata = {
            "mode": "scored_oracle_canary",
            "condition": condition,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "selection_proof": proof,
            "baseline_prediction_file": str(baseline_path),
            "treatment_prediction_file": str(treatment_path),
            "baseline_eval_file": str(baseline_eval_path),
            "treatment_eval_file": str(treatment_eval_path),
            "baseline_prompts": baseline_prompts,
            "treatment_prompts": treatment_prompts,
            "answer_model": summary["answer_model"],
            "judge_model": summary["judge_model"],
            "endpoint_metadata": endpoint_metadata or {},
            "guardrails": [
                "oracle evidence only",
                "no DB/Docker/runtime mutation",
                "no full LongMemEval _s/_m run",
            ],
        }
        write_json(summary_path, summary)
        write_json(metadata_path, metadata)
        return {
            "mode": "scored_oracle_canary",
            "condition": condition,
            "row_count": proof["row_count"],
            "baseline_prediction_file": str(baseline_path),
            "treatment_prediction_file": str(treatment_path),
            "baseline_eval_file": str(baseline_eval_path),
            "treatment_eval_file": str(treatment_eval_path),
            "metadata_file": str(metadata_path),
            "summary_file": str(summary_path),
            "baseline_accuracy": baseline_summary["accuracy"],
            "treatment_accuracy": treatment_summary["accuracy"],
        }

    baseline_jsonl = [{"question_id": item["question_id"], "hypothesis": ""} for item in baseline_prompts]
    treatment_jsonl = [{"question_id": item["question_id"], "hypothesis": ""} for item in treatment_prompts]

    treatment_label = "treatment" if condition == DEFAULT_CANDIDATE_CONDITION else condition
    baseline_path = out_dir / "longmemeval_oracle_canary_baseline_placeholder.jsonl"
    treatment_path = out_dir / f"longmemeval_oracle_canary_{treatment_label}_placeholder.jsonl"
    metadata_path = out_dir / "longmemeval_oracle_canary_preparation_metadata.json"
    write_jsonl(baseline_path, baseline_jsonl)
    write_jsonl(treatment_path, treatment_jsonl)
    metadata = {
        "mode": "preparation_only_no_answer_generation",
        "condition": condition,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "selection_proof": proof,
        "preregistered_gates": selection.get("preregistered_gates") or (
            SECOND_SLICE_GATES if selection.get("seed") == SECOND_SLICE_SELECTION_SEED else None
        ),
        "baseline_prediction_file": str(baseline_path),
        "treatment_prediction_file": str(treatment_path),
        "baseline_prompts": baseline_prompts,
        "treatment_prompts": treatment_prompts,
        "candidate_prompts": treatment_prompts,
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
        "condition": condition,
        "row_count": proof["row_count"],
        "baseline_prediction_file": str(baseline_path),
        "treatment_prediction_file": str(treatment_path),
        "metadata_file": str(metadata_path),
    }


def unique_ordered(values: list[Any]) -> list[Any]:
    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _required_retrieval_fields_missing(row: dict[str, Any]) -> list[str]:
    return sorted(field for field in RETRIEVAL_ROW_REQUIRED_FIELDS if field not in row)


def validate_retrieval_rows_for_selection(
    selected_rows: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    duplicates = duplicate_question_ids(retrieval_rows)
    if duplicates:
        raise ValueError(f"duplicate_retrieval_rows:{','.join(duplicates)}")
    selected_ids = [row["question_id"] for row in selected_rows]
    retrieval_by_id = {row.get("question_id"): row for row in retrieval_rows}
    extra = sorted(str(qid) for qid in set(retrieval_by_id) - set(selected_ids) if qid is not None)
    if extra:
        raise ValueError(f"unknown_retrieval_rows:{','.join(extra)}")
    for row in retrieval_rows:
        qid = row.get("question_id", "<missing_question_id>")
        missing_fields = _required_retrieval_fields_missing(row)
        if missing_fields:
            raise ValueError(f"missing_retrieval_fields:{qid}:{','.join(missing_fields)}")
        coverage_class = row.get("coverage_class")
        if coverage_class is None and row.get("retrieval_status") == "not_run_runtime_not_authorized":
            continue
        if coverage_class not in RETRIEVAL_COVERAGE_CLASSES:
            raise ValueError(f"invalid_coverage_class:{qid}")
        source = next((item for item in selected_rows if item["question_id"] == qid), None)
        if source is not None and row.get("question_type") != source.get("question_type"):
            raise ValueError(f"retrieval_question_type_mismatch:{qid}")
    return retrieval_by_id


def _count_by_coverage_class(retrieval_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {coverage_class: 0 for coverage_class in sorted(RETRIEVAL_COVERAGE_CLASSES)}
    for row in retrieval_rows:
        coverage_class = row.get("coverage_class")
        if coverage_class in counts:
            counts[coverage_class] += 1
    return counts


def evaluate_retrieval_bridge_phase_a_gates(
    selected_rows: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    retrieval_by_id = validate_retrieval_rows_for_selection(selected_rows, retrieval_rows)
    selected_ids = [row["question_id"] for row in selected_rows]
    missing_question_ids = sorted(set(selected_ids) - set(retrieval_by_id))
    present_rows = [retrieval_by_id[qid] for qid in selected_ids if qid in retrieval_by_id]

    incomplete_coverage_question_ids = sorted(
        row["question_id"]
        for row in present_rows
        if row.get("coverage_class") is None
    )
    missing_required_field_question_ids = sorted(
        row.get("question_id", "<missing_question_id>")
        for row in retrieval_rows
        if _required_retrieval_fields_missing(row)
    )
    completeness_pass = (
        len(present_rows) == len(selected_rows)
        and not missing_question_ids
        and not incomplete_coverage_question_ids
        and not missing_required_field_question_ids
    )

    error_rows = []
    for row in present_rows:
        retrieval_status = str(row.get("retrieval_status", ""))
        fallback_error_flags = row.get("fallback_error_flags") or []
        if retrieval_status != "ok" or fallback_error_flags:
            error_rows.append({
                "question_id": row["question_id"],
                "retrieval_status": retrieval_status,
                "fallback_error_flags": fallback_error_flags,
            })

    preference_rows = [row for row in selected_rows if row.get("question_type") == "single-session-preference"]
    preference_supported = [
        qid for qid in [row["question_id"] for row in preference_rows]
        if qid in retrieval_by_id and retrieval_by_id[qid].get("coverage_class") in PREFERENCE_COVERAGE_PASS_CLASSES
    ]
    knowledge_rows = [row for row in selected_rows if row.get("question_type") == "knowledge-update"]
    knowledge_adequate = [
        qid for qid in [row["question_id"] for row in knowledge_rows]
        if qid in retrieval_by_id and retrieval_by_id[qid].get("coverage_class") in KNOWLEDGE_UPDATE_COVERAGE_PASS_CLASSES
    ]
    stale_only_question_ids = [
        qid for qid in [row["question_id"] for row in knowledge_rows]
        if qid in retrieval_by_id and retrieval_by_id[qid].get("coverage_class") == "stale_only"
    ]

    abstention_rows = [row for row in selected_rows if str(row.get("question_id", "")).endswith("_abs")]
    unanswerable_contaminated = [
        qid for qid in [row["question_id"] for row in abstention_rows]
        if qid in retrieval_by_id and retrieval_by_id[qid].get("coverage_class") == "unanswerable_contaminated"
    ]

    answerable_rows = [row for row in selected_rows if not str(row.get("question_id", "")).endswith("_abs")]
    evidence_identity_missing = sorted(
        qid for qid in [row["question_id"] for row in answerable_rows]
        if (
            qid in retrieval_by_id
            and retrieval_by_id[qid].get("coverage_class") != "unsupported"
            and not retrieval_by_id[qid].get("source_refs")
        )
    )
    retrieval_artifact_missing = sorted(
        row["question_id"]
        for row in present_rows
        if not row.get("retrieved_memory_ids") and row.get("coverage_class") not in {"unsupported"}
    )

    gates = {
        "coverage_audit_completeness": {
            "pass": completeness_pass,
            "expected_rows": len(selected_rows),
            "observed_rows": len(present_rows),
            "missing_question_ids": missing_question_ids,
            "incomplete_coverage_question_ids": incomplete_coverage_question_ids,
            "missing_required_field_question_ids": missing_required_field_question_ids,
        },
        "retrieval_operational_success": {
            "pass": not error_rows,
            "error_rows": error_rows,
        },
        "preference_coverage": {
            "pass": len(preference_supported) >= 3,
            "adequate_coverage": len(preference_supported),
            "target": "3/4",
            "supported_question_ids": preference_supported,
            "total_preference_rows": len(preference_rows),
        },
        "knowledge_update_coverage": {
            "pass": len(knowledge_adequate) >= 3,
            "adequate_coverage": len(knowledge_adequate),
            "target": "3/5",
            "supported_or_partial_question_ids": knowledge_adequate,
            "stale_only_question_ids": stale_only_question_ids,
            "total_knowledge_update_rows": len(knowledge_rows),
        },
        "abstention_contamination": {
            "pass": len(unanswerable_contaminated) <= 1,
            "unanswerable_contaminated": len(unanswerable_contaminated),
            "target": "<=1/4",
            "contaminated_question_ids": unanswerable_contaminated,
            "total_abstention_rows": len(abstention_rows),
        },
        "evidence_identity": {
            "pass": not evidence_identity_missing and not retrieval_artifact_missing,
            "missing_source_ref_question_ids": evidence_identity_missing,
            "missing_retrieved_memory_id_question_ids": retrieval_artifact_missing,
        },
    }
    gates["overall"] = {"pass": all(gate["pass"] for gate in gates.values())}

    return {
        "mode": "retrieval_bridge_phase_a_gate_evaluation_offline",
        "gates": gates,
        "coverage_counts": {
            "total": len(present_rows),
            "by_class": _count_by_coverage_class(present_rows),
        },
        "preference": {
            "adequate_coverage": len(preference_supported),
            "target": 3,
            "total": len(preference_rows),
        },
        "knowledge_update": {
            "adequate_coverage": len(knowledge_adequate),
            "target": 3,
            "total": len(knowledge_rows),
            "stale_only": len(stale_only_question_ids),
        },
        "abstention": {
            "unanswerable_contaminated": len(unanswerable_contaminated),
            "target_max": 1,
            "total": len(abstention_rows),
        },
        "stale_only_question_ids": stale_only_question_ids,
        "preregistered_gates": RETRIEVAL_BRIDGE_PHASE_A_GATES,
        "phase_b_recommendation": (
            "phase_a_passed_answer_generation_still_requires_explicit_approval"
            if gates["overall"]["pass"]
            else "stop_before_answer_generation_phase_a_failed"
        ),
        "communication_boundary": "retrieval coverage evidence only; no answer/product benchmark claim",
    }


def write_retrieval_bridge_phase_a_report(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    retrieval_results_file: Path,
    report_file: Path,
    *,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
) -> dict[str, Any]:
    if selection.get("seed") != SECOND_SLICE_SELECTION_SEED:
        raise ValueError("retrieval_bridge_requires_second_slice_seed")
    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    by_id = {entry["question_id"]: entry for entry in dataset}
    selected_rows = [by_id[row["question_id"]] for row in selection["rows"]]
    retrieval_rows = load_jsonl(retrieval_results_file)
    report = evaluate_retrieval_bridge_phase_a_gates(selected_rows, retrieval_rows)
    report.update({
        "selection_proof": proof,
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_files": {
            "retrieval_results_file": str(retrieval_results_file),
            "selection_file": str(selection.get("_selection_file", "")),
        },
        "guardrails": [
            "offline existing retrieval artifacts only",
            "no answer generation",
            "no judging/model calls",
            "no Memibrium recall/context calls",
            "no DB/Docker/runtime mutation",
            "no full LongMemEval _s/_m run",
        ],
    })
    write_json(report_file, report)
    return report


def prepare_retrieval_bridge_canary(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    out_dir: Path,
    *,
    allow_runtime_retrieval: bool = False,
    allow_answer_generation: bool = False,
    allow_judge_calls: bool = False,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
    retrieval_fn: Callable[..., Any] | None = None,
    chat_fn: Callable[..., str] | None = None,
) -> dict[str, Any]:
    del retrieval_fn, chat_fn  # preparation mode must not call external runtime/model surfaces
    if allow_runtime_retrieval or allow_answer_generation or allow_judge_calls:
        raise ValueError("retrieval_bridge_launch_not_authorized")
    if selection.get("seed") != SECOND_SLICE_SELECTION_SEED:
        raise ValueError("retrieval_bridge_requires_second_slice_seed")

    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    by_id = {entry["question_id"]: entry for entry in dataset}
    selected_rows = [by_id[row["question_id"]] for row in selection["rows"]]
    selected_question_ids = [row["question_id"] for row in selected_rows]
    source_session_ids = unique_ordered([
        session_id
        for row in selected_rows
        for session_id in (row.get("haystack_session_ids") or [])
    ])
    answer_session_ids = unique_ordered([
        session_id
        for row in selected_rows
        for session_id in (row.get("answer_session_ids") or [])
    ])

    out_dir.mkdir(parents=True, exist_ok=True)
    ingest_manifest_path = out_dir / "ingest_manifest_placeholder.json"
    retrieval_results_path = out_dir / "retrieval_results_placeholder.jsonl"
    coverage_audit_path = out_dir / "retrieval_coverage_audit_placeholder.json"
    baseline_answer_path = out_dir / "answer_baseline_predictions_blocked_placeholder.jsonl"
    treatment_answer_path = out_dir / "answer_category_contract_v1_predictions_blocked_placeholder.jsonl"
    metadata_path = out_dir / "longmemeval_retrieval_bridge_preparation_metadata.json"
    cleanup_path = out_dir / "cleanup_report_placeholder.json"

    retrieval_rows = []
    coverage_rows = []
    for row in selected_rows:
        qid = row["question_id"]
        qtype = row.get("question_type", "")
        retrieval_rows.append({
            "question_id": qid,
            "question_type": qtype,
            "question": row.get("question", ""),
            "query_variants": [],
            "retrieved_memory_ids": [],
            "scores": [],
            "source_refs": [],
            "evidence_snippets": [],
            "timestamp_source_metadata": [],
            "fallback_error_flags": [],
            "coverage_class": None,
            "retrieval_status": "not_run_runtime_not_authorized",
        })
        coverage_rows.append({
            "question_id": qid,
            "question_type": qtype,
            "coverage_class": None,
            "gold_supporting_evidence_present": [],
            "gold_supporting_evidence_missing": [],
            "stale_conflicting_evidence_present": [],
            "proceed_to_answer_score": False,
            "stop_reason": "retrieval_not_run_runtime_not_authorized",
        })

    baseline_placeholders = [{"question_id": qid, "hypothesis": ""} for qid in selected_question_ids]
    treatment_placeholders = [{"question_id": qid, "hypothesis": ""} for qid in selected_question_ids]
    ingest_manifest = {
        "mode": "retrieval_bridge_ingest_placeholder_no_db_writes",
        "dataset_sha256": dataset_sha256,
        "hf_revision": EXPECTED_HF_REVISION,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "selected_question_ids": selected_question_ids,
        "source_session_ids": source_session_ids,
        "answer_session_ids": answer_session_ids,
        "memory_ids_created": [],
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "redacted_runtime_metadata": {},
        "ingest_status": "not_run_db_writes_not_authorized",
    }
    coverage_audit = {
        "mode": "retrieval_bridge_phase_a_coverage_placeholder",
        "coverage_status": "not_evaluated_retrieval_not_run",
        "phase_a_stop_rule": "if coverage is missing, stop before answer generation",
        "phase_a_gates": RETRIEVAL_BRIDGE_PHASE_A_GATES,
        "coverage_classes": sorted(RETRIEVAL_COVERAGE_CLASSES),
        "rows": coverage_rows,
    }
    cleanup_report = {
        "mode": "cleanup_placeholder_no_deletes",
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "created_memory_count": 0,
        "deleted_memory_count": 0,
        "final_domain_count_verified": None,
        "cleanup_status": "not_applicable_no_ingest_run",
    }
    metadata = {
        "mode": "retrieval_bridge_preparation_only_no_runtime_calls",
        "phase": "phase_a_retrieval_coverage_preparation",
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "selection_proof": proof,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "phase_a_gates": RETRIEVAL_BRIDGE_PHASE_A_GATES,
        "artifact_files": {
            "ingest_manifest": str(ingest_manifest_path),
            "retrieval_results": str(retrieval_results_path),
            "retrieval_coverage_audit": str(coverage_audit_path),
            "answer_baseline_predictions": str(baseline_answer_path),
            "answer_treatment_predictions": str(treatment_answer_path),
            "cleanup_report": str(cleanup_path),
        },
        "answer_conditions": {
            "baseline": {
                "condition": "retrieval_context_baseline_prompt",
                "retrieved_evidence_source": "shared_retrieval_results_after_phase_a",
            },
            "treatment": {
                "condition": "category_contract_v1",
                "retrieved_evidence_source": "shared_retrieval_results_after_phase_a",
            },
            "evidence_identity_requirement": "baseline and treatment must share identical retrieved evidence per question_id",
        },
        "communication_boundary": "retrieval bridge preparation only; no retrieval/product benchmark claim",
        "guardrails": [
            "no LongMemEval conversation ingestion",
            "no Memibrium recall/context calls",
            "no DB/Docker/runtime mutation",
            "no answer model calls",
            "no judge calls",
            "no full LongMemEval _s/_m run",
            "no direct /mcp/tools inspection",
        ],
    }

    write_json(ingest_manifest_path, ingest_manifest)
    write_jsonl(retrieval_results_path, retrieval_rows)
    write_json(coverage_audit_path, coverage_audit)
    write_jsonl(baseline_answer_path, baseline_placeholders)
    write_jsonl(treatment_answer_path, treatment_placeholders)
    write_json(cleanup_path, cleanup_report)
    write_json(metadata_path, metadata)
    return {
        "mode": "retrieval_bridge_preparation_only_no_runtime_calls",
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "row_count": proof["row_count"],
        "metadata_file": str(metadata_path),
        "retrieval_results_file": str(retrieval_results_path),
        "coverage_audit_file": str(coverage_audit_path),
    }


def _redacted_url_metadata(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url or "")
    host = parsed.netloc.split("@")[-1]
    return {
        "scheme": parsed.scheme,
        "host": host,
        "path": parsed.path,
        "configured": bool(url),
    }


def redacted_memibrium_runtime_metadata(base_url: str) -> dict[str, Any]:
    return {"memibrium_base_url": _redacted_url_metadata(base_url)}


def memibrium_http_post(
    path: str,
    payload: dict[str, Any],
    *,
    base_url: str,
    timeout: int = 30,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # pragma: no cover - live path
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # pragma: no cover - live path
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"memibrium_http_error:{path}:{exc.code}:{body}") from exc
    except Exception as exc:  # pragma: no cover - live path
        raise RuntimeError(f"memibrium_http_call_failed:{path}:{exc}") from exc
    if not body:
        return {}
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        return {"response": parsed}
    return parsed


def _parse_longmemeval_session_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = dt.datetime.strptime(text, "%Y/%m/%d (%a) %H:%M")
    except ValueError:
        return text
    return parsed.replace(tzinfo=dt.timezone.utc).isoformat()


def make_memibrium_ingest_fn(
    *,
    base_url: str,
    post_fn: Callable[..., dict[str, Any]] = memibrium_http_post,
    timeout: int = 30,
) -> Callable[..., list[str]]:
    def ingest(planned_memories: list[dict[str, Any]], *, domain: str) -> list[str]:
        created_ids: list[str] = []
        for item in planned_memories:
            metadata = item.get("metadata") or {}
            bridge_refs = {
                "source_ref": item.get("source_ref"),
                "source_dataset": metadata.get("source_dataset", "longmemeval_oracle_cleaned_pin"),
                "session_id": metadata.get("session_id"),
                "session_date": metadata.get("session_date"),
                "turn_index": metadata.get("turn_index"),
                "role": metadata.get("role"),
                "has_answer": bool(metadata.get("has_answer")),
                "question_ids": list(metadata.get("question_ids") or []),
            }
            payload = {
                "content": item.get("content", ""),
                "source": "longmemeval_bridge_phase_a",
                "domain": domain,
                "event_at": _parse_longmemeval_session_date(metadata.get("session_date")),
                "refs": {"longmemeval_bridge": bridge_refs},
            }
            response = post_fn("/mcp/retain", payload, base_url=base_url, timeout=timeout)
            memory_id = response.get("id") or response.get("memory_id")
            if not memory_id:
                raise RuntimeError("memibrium_retain_missing_memory_id")
            created_ids.append(str(memory_id))
        return created_ids
    return ingest


def _memory_id_from_evidence(item: dict[str, Any]) -> str | None:
    value = item.get("memory_id") or item.get("id")
    return str(value) if value else None


def _score_from_evidence(item: dict[str, Any]) -> float | None:
    for key in ("combined_score", "cosine_score", "score"):
        value = item.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _source_ref_from_evidence(item: dict[str, Any]) -> str | None:
    refs = item.get("refs") if isinstance(item.get("refs"), dict) else {}
    bridge_refs = refs.get("longmemeval_bridge") if isinstance(refs.get("longmemeval_bridge"), dict) else {}
    source_ref = bridge_refs.get("source_ref") or item.get("source_ref")
    return str(source_ref) if source_ref else None


def _extract_context_packet_evidence(packet: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("episodic_evidence", "memories", "results"):
        value = packet.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    source_attribution = packet.get("source_attribution")
    if isinstance(source_attribution, dict) and isinstance(source_attribution.get("evidence"), list):
        return [item for item in source_attribution["evidence"] if isinstance(item, dict)]
    return []


def _heuristic_coverage_class(row: dict[str, Any], evidence: list[dict[str, Any]], source_refs: list[str]) -> str:
    if not evidence:
        return "unsupported"
    question_id = str(row.get("question_id", ""))
    if question_id.endswith("_abs"):
        return "unanswerable_supported" if not source_refs else "unanswerable_contaminated"
    answer = str(row.get("answer", "")).lower()
    if answer and any(answer in str(item.get("content") or item.get("text") or "").lower() for item in evidence):
        return "gold_supported"
    if source_refs:
        return "partial_support"
    return "adjacent_entity_only"


def make_memibrium_retrieval_fn(
    *,
    base_url: str,
    post_fn: Callable[..., dict[str, Any]] = memibrium_http_post,
    top_k: int = 8,
    timeout: int = 30,
) -> Callable[..., dict[str, Any]]:
    def retrieve(row: dict[str, Any], *, domain: str, memory_ids: list[str]) -> dict[str, Any]:
        query = row.get("question", "")
        payload = {
            "query": query,
            "domain": domain,
            "top_k": top_k,
            "include_source_attribution": True,
            "include_decision_traces": False,
            "expand": True,
        }
        packet = post_fn("/mcp/context_packet", payload, base_url=base_url, timeout=timeout)
        evidence = _extract_context_packet_evidence(packet)
        retrieved_ids = [mid for mid in (_memory_id_from_evidence(item) for item in evidence) if mid]
        scores = [score for score in (_score_from_evidence(item) for item in evidence) if score is not None]
        source_refs = [ref for ref in (_source_ref_from_evidence(item) for item in evidence) if ref]
        snippets = [str(item.get("content") or item.get("text") or "") for item in evidence if item.get("content") or item.get("text")]
        source_attribution = packet.get("source_attribution") if isinstance(packet.get("source_attribution"), dict) else {}
        retrieval_path = source_attribution.get("retrieval_path", "unknown")
        return {
            "retrieval_status": "ok",
            "query_variants": [query],
            "retrieved_memory_ids": retrieved_ids,
            "scores": scores,
            "source_refs": source_refs,
            "evidence_snippets": snippets,
            "timestamp_source_metadata": [{
                "retrieval_path": retrieval_path,
                "candidate_memory_count": len(memory_ids),
                "source_attribution_present": bool(source_attribution),
            }],
            "fallback_error_flags": [],
            "coverage_class": _heuristic_coverage_class(row, evidence, source_refs),
        }
    return retrieve


def _parse_delete_count(status: Any) -> int:
    if not isinstance(status, str):
        return 0
    parts = status.strip().split()
    if len(parts) >= 2 and parts[-1].isdigit():
        return int(parts[-1])
    return 0


def make_memibrium_cleanup_fn(
    *,
    db_dsn: str,
    connect_fn: Callable[..., Any] | None = None,
) -> Callable[..., dict[str, Any]]:
    async def _cleanup(domain: str, memory_ids: list[str]) -> dict[str, Any]:
        if not domain or domain != RETRIEVAL_BRIDGE_DOMAIN:
            raise ValueError("cleanup_requires_exact_retrieval_bridge_domain")
        connector = connect_fn
        if connector is None:  # pragma: no cover - live path
            import asyncpg  # type: ignore
            connector = asyncpg.connect
        conn = await connector(db_dsn)
        try:
            counts = await conn.fetchrow("""
                SELECT
                  (SELECT COUNT(*) FROM memories WHERE domain = $1) AS memory_count,
                  (SELECT COUNT(*) FROM user_feedback WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)) AS feedback_count,
                  (SELECT COUNT(*) FROM memory_snapshots WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)) AS snapshot_count,
                  (SELECT COUNT(*) FROM memory_edges WHERE source_id IN (SELECT id FROM memories WHERE domain = $1) OR target_id IN (SELECT id FROM memories WHERE domain = $1)) AS edge_count,
                  (SELECT COUNT(*) FROM contradictions WHERE memory_a_id IN (SELECT id FROM memories WHERE domain = $1) OR memory_b_id IN (SELECT id FROM memories WHERE domain = $1)) AS contradiction_count,
                  (SELECT COUNT(*) FROM temporal_expressions WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)) AS temporal_expression_count,
                  (SELECT COUNT(*) FROM context_graph_edges WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)) AS context_graph_edge_count,
                  (SELECT COUNT(*) FROM decision_traces WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)) AS decision_trace_count,
                  (SELECT COUNT(*) FROM self_model_observations WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)) AS self_model_observation_count
            """, domain)
            linked_rows_deleted: dict[str, int] = {}
            delete_statements = [
                ("user_feedback", "DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)"),
                ("memory_snapshots", "DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)"),
                ("memory_edges", "DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM memories WHERE domain = $1) OR target_id IN (SELECT id FROM memories WHERE domain = $1)"),
                ("contradictions", "DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM memories WHERE domain = $1) OR memory_b_id IN (SELECT id FROM memories WHERE domain = $1)"),
                ("temporal_expressions", "DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM memories WHERE domain = $1)"),
                ("context_graph_edges", "DELETE FROM context_graph_edges WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)"),
                ("decision_traces", "DELETE FROM decision_traces WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)"),
                ("self_model_observations", "DELETE FROM self_model_observations WHERE evidence_memory_ids ?| ARRAY(SELECT id FROM memories WHERE domain = $1)"),
            ]
            for table, sql in delete_statements:
                linked_rows_deleted[table] = _parse_delete_count(await conn.execute(sql, domain))
            deleted_memory_count = _parse_delete_count(await conn.execute("DELETE FROM memories WHERE domain = $1", domain))
            final_count = await conn.fetchval("SELECT COUNT(id) FROM memories WHERE domain = $1", domain)
            return {
                "requested_memory_ids": list(memory_ids),
                "pre_cleanup_counts": dict(counts) if counts else {},
                "linked_rows_deleted": linked_rows_deleted,
                "deleted_memory_count": deleted_memory_count,
                "final_domain_count_verified": int(final_count or 0),
            }
        finally:
            close = getattr(conn, "close", None)
            if close is not None:
                result = close()
                if hasattr(result, "__await__"):
                    await result

    def cleanup(*, domain: str, memory_ids: list[str]) -> dict[str, Any]:
        return asyncio.run(_cleanup(domain, memory_ids))
    return cleanup


def _selected_rows_from_selection(dataset: list[dict[str, Any]], selection: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {entry["question_id"]: entry for entry in dataset}
    return [by_id[row["question_id"]] for row in selection["rows"]]


def _source_session_ids(selected_rows: list[dict[str, Any]]) -> list[Any]:
    return unique_ordered([
        session_id
        for row in selected_rows
        for session_id in (row.get("haystack_session_ids") or [])
    ])


def _answer_session_ids(selected_rows: list[dict[str, Any]]) -> list[Any]:
    return unique_ordered([
        session_id
        for row in selected_rows
        for session_id in (row.get("answer_session_ids") or [])
    ])


def build_retrieval_bridge_ingest_manifest(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    *,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
) -> dict[str, Any]:
    if selection.get("seed") != SECOND_SLICE_SELECTION_SEED:
        raise ValueError("retrieval_bridge_requires_second_slice_seed")
    proof = validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    selected_rows = _selected_rows_from_selection(dataset, selection)
    planned_by_ref: dict[str, dict[str, Any]] = {}
    for row in selected_rows:
        qid = row["question_id"]
        sessions = row.get("haystack_sessions") or []
        session_ids = row.get("haystack_session_ids") or []
        dates = row.get("haystack_dates") or []
        for session_index, session in enumerate(sessions):
            session_id = session_ids[session_index] if session_index < len(session_ids) else f"session_{session_index + 1}"
            session_date = dates[session_index] if session_index < len(dates) else None
            for turn_index, turn in enumerate(session, start=1):
                role = turn.get("role", "unknown")
                source_ref = f"{session_id}:turn_{turn_index}:{role}"
                item = planned_by_ref.setdefault(source_ref, {
                    "source_ref": source_ref,
                    "content": turn.get("content", ""),
                    "metadata": {
                        "domain": RETRIEVAL_BRIDGE_DOMAIN,
                        "source_dataset": "longmemeval_oracle_cleaned_pin",
                        "session_id": session_id,
                        "session_date": session_date,
                        "turn_index": turn_index,
                        "role": role,
                        "has_answer": bool(turn.get("has_answer")),
                        "question_ids": [],
                    },
                })
                if qid not in item["metadata"]["question_ids"]:
                    item["metadata"]["question_ids"].append(qid)
    planned_memories = list(planned_by_ref.values())
    return {
        "mode": "retrieval_bridge_phase_a_ingest_manifest",
        "dataset_sha256": dataset_sha256,
        "hf_revision": EXPECTED_HF_REVISION,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "selection_proof": proof,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "selected_question_ids": [row["question_id"] for row in selected_rows],
        "source_session_ids": _source_session_ids(selected_rows),
        "answer_session_ids": _answer_session_ids(selected_rows),
        "planned_memory_count": len(planned_memories),
        "planned_memories": planned_memories,
        "memory_ids_created": [],
        "created_memory_ids": [],
        "ingest_status": "planned_no_db_writes",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def run_retrieval_bridge_phase_a(
    dataset: list[dict[str, Any]],
    selection: dict[str, Any],
    out_dir: Path,
    *,
    allow_db_writes: bool = False,
    allow_runtime_retrieval: bool = False,
    allow_cleanup_deletes: bool = False,
    allow_answer_generation: bool = False,
    allow_judge_calls: bool = False,
    dataset_sha256: str = EXPECTED_ORACLE_SHA256,
    ingest_fn: Callable[..., list[str]] | None = None,
    retrieval_fn: Callable[..., dict[str, Any]] | None = None,
    cleanup_fn: Callable[..., dict[str, Any]] | None = None,
    chat_fn: Callable[..., str] | None = None,
    runtime_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del chat_fn  # Phase A must never call answer or judge models.
    if allow_answer_generation or allow_judge_calls:
        raise ValueError("retrieval_bridge_phase_a_disallows_answer_or_judge_calls")
    if not (allow_db_writes and allow_runtime_retrieval and allow_cleanup_deletes):
        raise ValueError("retrieval_bridge_phase_a_requires_explicit_side_effect_approval")
    if ingest_fn is None or retrieval_fn is None or cleanup_fn is None:
        raise ValueError("retrieval_bridge_phase_a_requires_injected_runtime_functions")

    manifest = build_retrieval_bridge_ingest_manifest(dataset, selection, dataset_sha256=dataset_sha256)
    selected_rows = _selected_rows_from_selection(dataset, selection)
    out_dir.mkdir(parents=True, exist_ok=True)

    created_memory_ids = ingest_fn(manifest["planned_memories"], domain=RETRIEVAL_BRIDGE_DOMAIN)
    manifest["memory_ids_created"] = list(created_memory_ids)
    manifest["created_memory_ids"] = list(created_memory_ids)
    manifest["ingest_status"] = "completed_with_injected_ingest_fn"
    manifest["redacted_runtime_metadata"] = runtime_metadata or {}
    write_json(out_dir / "ingest_manifest.json", manifest)

    retrieval_rows = []
    coverage_rows = []
    for row in selected_rows:
        qid = row["question_id"]
        try:
            retrieved = retrieval_fn(row, domain=RETRIEVAL_BRIDGE_DOMAIN, memory_ids=list(created_memory_ids))
            coverage_class = retrieved.get("coverage_class")
            retrieval_row = {
                "question_id": qid,
                "question_type": row.get("question_type", ""),
                "question": row.get("question", ""),
                "query_variants": retrieved.get("query_variants", [row.get("question", "")]),
                "retrieved_memory_ids": retrieved.get("retrieved_memory_ids", []),
                "scores": retrieved.get("scores", []),
                "source_refs": retrieved.get("source_refs", []),
                "evidence_snippets": retrieved.get("evidence_snippets", []),
                "timestamp_source_metadata": retrieved.get("timestamp_source_metadata", []),
                "fallback_error_flags": retrieved.get("fallback_error_flags", []),
                "coverage_class": coverage_class,
                "retrieval_status": retrieved.get("retrieval_status", "ok"),
            }
        except Exception as exc:  # pragma: no cover - exercised by future live failures
            retrieval_row = {
                "question_id": qid,
                "question_type": row.get("question_type", ""),
                "question": row.get("question", ""),
                "query_variants": [row.get("question", "")],
                "retrieved_memory_ids": [],
                "scores": [],
                "source_refs": [],
                "evidence_snippets": [],
                "timestamp_source_metadata": [],
                "fallback_error_flags": [str(exc)],
                "coverage_class": "unsupported",
                "retrieval_status": "runtime_exception",
            }
        retrieval_rows.append(retrieval_row)
        coverage_rows.append({
            "question_id": qid,
            "question_type": row.get("question_type", ""),
            "coverage_class": retrieval_row["coverage_class"],
            "gold_supporting_evidence_present": retrieval_row.get("source_refs", []),
            "gold_supporting_evidence_missing": [],
            "stale_conflicting_evidence_present": [],
            "source_refs": retrieval_row.get("source_refs", []),
            "classification_notes": "coverage supplied by injected retrieval function for Phase A scaffold",
        })

    write_jsonl(out_dir / "retrieval_results.jsonl", retrieval_rows)
    coverage_audit = {
        "mode": "retrieval_bridge_phase_a_coverage_audit",
        "coverage_status": "evaluated_artifact_only",
        "phase_a_gates": RETRIEVAL_BRIDGE_PHASE_A_GATES,
        "coverage_classes": sorted(RETRIEVAL_COVERAGE_CLASSES),
        "rows": coverage_rows,
    }
    write_json(out_dir / "retrieval_coverage_audit.json", coverage_audit)

    phase_a_report = evaluate_retrieval_bridge_phase_a_gates(selected_rows, retrieval_rows)
    phase_a_report.update({
        "selection_proof": manifest["selection_proof"],
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "input_files": {"retrieval_results_file": str(out_dir / "retrieval_results.jsonl")},
        "guardrails": [
            "runtime functions injected by caller",
            "no answer generation",
            "no judge/model calls",
            "no full LongMemEval _s/_m run",
        ],
    })
    write_json(out_dir / "longmemeval_retrieval_bridge_phase_a_gate_report.json", phase_a_report)

    cleanup_result = cleanup_fn(domain=RETRIEVAL_BRIDGE_DOMAIN, memory_ids=list(created_memory_ids))
    cleanup_report = {
        "mode": "retrieval_bridge_phase_a_cleanup",
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "created_memory_count": len(created_memory_ids),
        "deleted_memory_count": cleanup_result.get("deleted_memory_count", 0),
        "final_domain_count_verified": cleanup_result.get("final_domain_count_verified"),
        "linked_rows_deleted": cleanup_result.get("linked_rows_deleted", {}),
        "cleanup_status": "complete" if cleanup_result.get("final_domain_count_verified") == 0 else "verification_failed",
    }
    write_json(out_dir / "cleanup_report.json", cleanup_report)

    run_metadata = {
        "mode": "retrieval_bridge_phase_a_runtime_scaffold",
        "condition": RETRIEVAL_BRIDGE_CONDITION,
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dataset_sha256": dataset_sha256,
        "selection_sha256": RETRIEVAL_BRIDGE_SELECTION_SHA256,
        "overall_pass": phase_a_report["gates"]["overall"]["pass"],
        "phase_b_recommendation": phase_a_report["phase_b_recommendation"],
        "communication_boundary": "retrieval coverage evidence only; no answer/product benchmark claim",
        "guardrails": [
            "no answer model calls",
            "no judge calls",
            "no full LongMemEval _s/_m run",
            "no direct /mcp/tools inspection",
        ],
    }
    write_json(out_dir / "run_metadata.json", run_metadata)
    return {
        "mode": "retrieval_bridge_phase_a_runtime_scaffold",
        "domain": RETRIEVAL_BRIDGE_DOMAIN,
        "row_count": len(selected_rows),
        "overall_pass": phase_a_report["gates"]["overall"]["pass"],
        "phase_b_recommendation": phase_a_report["phase_b_recommendation"],
        "phase_a_report_file": str(out_dir / "longmemeval_retrieval_bridge_phase_a_gate_report.json"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or run LongMemEval oracle canary artifacts.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION_PATH)
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR / f"longmemeval_oracle_canary_prepare_{RUN_ID}")
    parser.add_argument("--allow-answer-generation", action="store_true", help="Explicit scored oracle canary launch path; makes answer and judge model calls.")
    parser.add_argument("--answer-model", default=os.environ.get("ANSWER_MODEL", "gpt-4o"))
    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "gpt-4o"))
    parser.add_argument("--dotenv", type=Path, default=ROOT / ".env", help="Load non-exported env vars from this .env without printing secrets.")
    parser.add_argument("--preflight-only", action="store_true", help="Validate dataset/selection/env and run one tiny chat call, then exit.")
    parser.add_argument("--condition", choices=sorted(SUPPORTED_CANDIDATE_CONDITIONS), default=DEFAULT_CANDIDATE_CONDITION, help="Candidate prompt condition for the non-baseline arm.")
    parser.add_argument("--offline-gate-report", action="store_true", help="Evaluate preregistered second-slice gates from existing eval JSONL files only; no model or judge calls.")
    parser.add_argument("--baseline-eval-file", type=Path, help="Existing baseline eval_results JSONL for --offline-gate-report.")
    parser.add_argument("--treatment-eval-file", type=Path, help="Existing treatment eval_results JSONL for --offline-gate-report.")
    parser.add_argument("--gate-report-file", type=Path, help="Output JSON report path for --offline-gate-report; defaults under --out-dir.")
    parser.add_argument("--prepare-retrieval-bridge", action="store_true", help="Prepare retrieval-coupled bridge Phase A placeholder artifacts only; no runtime/model/judge calls.")
    parser.add_argument("--retrieval-bridge-phase-a-report", action="store_true", help="Evaluate retrieval bridge Phase A gates from existing retrieval JSONL artifacts only; no runtime/model/judge calls.")
    parser.add_argument("--run-retrieval-bridge-phase-a", action="store_true", help="Run Phase A scaffold with explicit side-effect approvals; requires runtime function wiring before live use.")
    parser.add_argument("--retrieval-results-file", type=Path, help="Existing retrieval results JSONL for --retrieval-bridge-phase-a-report.")
    parser.add_argument("--phase-a-report-file", type=Path, help="Output JSON report path for --retrieval-bridge-phase-a-report; defaults under --out-dir.")
    parser.add_argument("--allow-db-writes", action="store_true", help="Explicit approval flag for namespaced DB ingest writes in Phase A scaffold.")
    parser.add_argument("--allow-runtime-retrieval", action="store_true", help="Reserved future launch flag; currently rejected for retrieval bridge preparation/reporting unless --run-retrieval-bridge-phase-a is used.")
    parser.add_argument("--allow-cleanup-deletes", action="store_true", help="Explicit approval flag for namespaced cleanup deletes in Phase A scaffold.")
    parser.add_argument("--allow-judge-calls", action="store_true", help="Reserved future launch flag; currently rejected for retrieval bridge preparation/reporting.")
    parser.add_argument("--memibrium-base-url", default=os.environ.get("MEMIBRIUM_BASE_URL", "http://localhost:9999"), help="Memibrium server base URL for --run-retrieval-bridge-phase-a; redacted in artifacts/stdout.")
    parser.add_argument("--memibrium-db-dsn", default=os.environ.get("MEMIBRIUM_DB_DSN", ""), help="Postgres DSN for namespaced cleanup in --run-retrieval-bridge-phase-a; never written to artifacts/stdout.")
    args = parser.parse_args(argv)
    if args.offline_gate_report and args.allow_answer_generation:
        parser.error("--offline-gate-report cannot be combined with --allow-answer-generation")
    if args.retrieval_bridge_phase_a_report and args.allow_answer_generation:
        parser.error("--retrieval-bridge-phase-a-report cannot be combined with --allow-answer-generation")
    if args.retrieval_bridge_phase_a_report and (args.allow_runtime_retrieval or args.allow_judge_calls or args.allow_db_writes or args.allow_cleanup_deletes):
        parser.error("--retrieval-bridge-phase-a-report cannot be combined with runtime, answer, judge, DB, or cleanup launch flags")
    if args.run_retrieval_bridge_phase_a and (args.allow_answer_generation or args.allow_judge_calls):
        parser.error("--run-retrieval-bridge-phase-a cannot be combined with answer or judge calls")
    if args.run_retrieval_bridge_phase_a and (args.offline_gate_report or args.retrieval_bridge_phase_a_report or args.prepare_retrieval_bridge):
        parser.error("--run-retrieval-bridge-phase-a cannot be combined with prep/report modes")
    if args.run_retrieval_bridge_phase_a and not args.memibrium_db_dsn:
        parser.error("--run-retrieval-bridge-phase-a requires --memibrium-db-dsn or MEMIBRIUM_DB_DSN for cleanup verification")
    if args.offline_gate_report and args.retrieval_bridge_phase_a_report:
        parser.error("--offline-gate-report cannot be combined with --retrieval-bridge-phase-a-report")
    if args.offline_gate_report and (args.baseline_eval_file is None or args.treatment_eval_file is None):
        parser.error("--offline-gate-report requires --baseline-eval-file and --treatment-eval-file")
    if args.retrieval_bridge_phase_a_report and args.retrieval_results_file is None:
        parser.error("--retrieval-bridge-phase-a-report requires --retrieval-results-file")
    return args


def main() -> None:
    args = parse_args()
    load_dotenv(args.dotenv)
    dataset_sha256 = sha256_file(args.dataset)
    dataset = load_json(args.dataset)
    selection = load_json(args.selection)
    selection["_selection_file"] = str(args.selection)
    validate_selection(dataset, selection, dataset_sha256=dataset_sha256)
    if args.offline_gate_report:
        report_file = args.gate_report_file or (args.out_dir / "longmemeval_oracle_canary_second_slice_gate_report.json")
        result = write_second_slice_gate_report(
            dataset,
            selection,
            args.baseline_eval_file,
            args.treatment_eval_file,
            report_file,
            dataset_sha256=dataset_sha256,
        )
        print(json.dumps({
            "mode": result["mode"],
            "gate_report_file": str(report_file),
            "overall_pass": result["gates"]["overall"]["pass"],
            "communication_boundary": result["communication_boundary"],
        }, indent=2))
        return
    if args.retrieval_bridge_phase_a_report:
        report_file = args.phase_a_report_file or (args.out_dir / "longmemeval_retrieval_bridge_phase_a_gate_report.json")
        result = write_retrieval_bridge_phase_a_report(
            dataset,
            selection,
            args.retrieval_results_file,
            report_file,
            dataset_sha256=dataset_sha256,
        )
        print(json.dumps({
            "mode": result["mode"],
            "phase_a_report_file": str(report_file),
            "overall_pass": result["gates"]["overall"]["pass"],
            "phase_b_recommendation": result["phase_b_recommendation"],
            "communication_boundary": result["communication_boundary"],
        }, indent=2))
        return
    if args.prepare_retrieval_bridge:
        result = prepare_retrieval_bridge_canary(
            dataset,
            selection,
            args.out_dir,
            allow_runtime_retrieval=args.allow_runtime_retrieval,
            allow_answer_generation=args.allow_answer_generation,
            allow_judge_calls=args.allow_judge_calls,
            dataset_sha256=dataset_sha256,
        )
        print(json.dumps(result, indent=2))
        return
    if args.run_retrieval_bridge_phase_a:
        result = run_retrieval_bridge_phase_a(
            dataset,
            selection,
            args.out_dir,
            allow_db_writes=args.allow_db_writes,
            allow_runtime_retrieval=args.allow_runtime_retrieval,
            allow_cleanup_deletes=args.allow_cleanup_deletes,
            allow_answer_generation=args.allow_answer_generation,
            allow_judge_calls=args.allow_judge_calls,
            dataset_sha256=dataset_sha256,
            ingest_fn=make_memibrium_ingest_fn(base_url=args.memibrium_base_url),
            retrieval_fn=make_memibrium_retrieval_fn(base_url=args.memibrium_base_url),
            cleanup_fn=make_memibrium_cleanup_fn(db_dsn=args.memibrium_db_dsn),
            chat_fn=None,
            runtime_metadata=redacted_memibrium_runtime_metadata(args.memibrium_base_url),
        )
        print(json.dumps(result, indent=2))
        return
    if args.preflight_only:
        chat_completions_call([{"role": "user", "content": "Reply with exactly OK."}], model=args.answer_model, max_tokens=5)
        print(json.dumps({
            "mode": "preflight_only",
            "dataset_sha256": dataset_sha256,
            "selection_rows": len(selection.get("rows") or []),
            "answer_model": args.answer_model,
            "judge_model": args.judge_model,
            "condition": args.condition,
            "endpoint_metadata": endpoint_metadata(os.environ.get("AZURE_CHAT_ENDPOINT", "")),
        }, indent=2))
        return
    result = prepare_oracle_canary(
        dataset,
        selection,
        args.out_dir,
        allow_answer_generation=args.allow_answer_generation,
        dataset_sha256=dataset_sha256,
        answer_model=args.answer_model,
        judge_model=args.judge_model,
        endpoint_metadata=endpoint_metadata(os.environ.get("AZURE_CHAT_ENDPOINT", "")),
        condition=args.condition,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
