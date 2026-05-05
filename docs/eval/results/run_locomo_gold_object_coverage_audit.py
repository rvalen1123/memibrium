#!/usr/bin/env python3
"""Artifact-only LOCOMO gold-object coverage audit.

This script does not call the live Memibrium server, mutate DB state, or launch a
benchmark. It inspects pinned canary artifacts and checks whether answer atoms
from each gold answer appear in the frozen final_context used by that row.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "being",
    "by", "did", "do", "does", "for", "from", "had", "has", "have", "he",
    "her", "hers", "him", "his", "how", "i", "in", "into", "is", "it", "its",
    "me", "mel", "melanie", "my", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "they", "this", "to", "was", "we", "what", "when",
    "where", "who", "why", "with", "would", "you", "your", "caroline",
}

# Small manual atom overrides keep the diagnostic auditable and avoid pretending
# a generic tokenizer can infer answer objects perfectly from free-form gold.
MANUAL_ATOMS: dict[int, list[str]] = {
    24: ["Nothing is Impossible", "Charlotte's Web"],
    41: ["beach"],
    113: ["sunset", "palm tree"],
    123: ["catch the eye", "make people smile"],
    163: ["nature", "roasted marshmallows", "hike"],
    185: ["clarinet", "violin"],
}

# Contradictory/conflicting terms seen during the prior row-level audit. These
# are not scored as gold hits; they mark rows where the context may contain a
# plausible wrong answer or role-conflicting evidence.
CONFLICT_TERMS: dict[int, list[str]] = {
    113: ["flowers", "nature-inspired"],
    123: ["express emotions", "self-expression", "relax"],
    185: ["acoustic guitar", "guitar"],
}


def normalize_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text)
    return text


def atom_present(atom: str, context_text: str) -> bool:
    a = normalize_text(atom)
    if a in context_text:
        return True
    # For multi-word atoms, require all significant words. This catches variants
    # such as "make people smile" when punctuation/inflection differs.
    words = [w for w in re.findall(r"[a-z0-9']+", a) if w not in STOPWORDS]
    if len(words) >= 2:
        return all(re.search(rf"\b{re.escape(w)}\b", context_text) for w in words)
    if len(words) == 1:
        return re.search(rf"\b{re.escape(words[0])}\b", context_text) is not None
    return False


def derive_atoms(row_index: int, ground_truth: Any) -> list[str]:
    if row_index in MANUAL_ATOMS:
        return MANUAL_ATOMS[row_index]
    text = str(ground_truth)
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted
    # Split list-like answers first.
    parts = re.split(r"\s*(?:,|;|\band\b|\bor\b)\s*", text)
    atoms: list[str] = []
    for part in parts:
        clean = part.strip(" .;:,\n\t\"'")
        if not clean:
            continue
        words = [w for w in re.findall(r"[A-Za-z0-9']+", clean) if w.lower() not in STOPWORDS]
        if len(words) == 1 and len(words[0]) <= 2:
            continue
        if words:
            atoms.append(clean)
    if atoms:
        return atoms[:8]
    return [text.strip()]


def row_index(detail: dict[str, Any]) -> int:
    ident = detail.get("row_identity") or {}
    if isinstance(ident, dict) and "one_based_index" in ident:
        return int(ident["one_based_index"])
    return int(detail["one_based_index"])


def context_for_detail(detail: dict[str, Any]) -> str:
    context = detail.get("frozen_baseline_context")
    if context is None:
        context = detail.get("final_context") or detail.get("answer_prompt_context_preview") or ""
    return normalize_text(context)


def classify(atom_count: int, present_count: int, conflict_count: int) -> str:
    if atom_count and present_count == atom_count:
        if conflict_count:
            return "all_atoms_present_with_conflicts"
        return "all_atoms_present"
    if present_count > 0:
        if conflict_count:
            return "partial_atoms_present_with_conflicts"
        return "partial_atoms_present"
    if conflict_count:
        return "no_atoms_present_conflicting_context"
    return "no_atoms_present"


def load_details(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    details = data.get("details")
    if not isinstance(details, list):
        raise ValueError(f"{path} does not contain a details list")
    return details


def audit_artifact(path: Path, label: str) -> dict[str, Any]:
    rows = []
    for detail in load_details(path):
        idx = row_index(detail)
        context_text = context_for_detail(detail)
        atoms = derive_atoms(idx, detail.get("ground_truth", ""))
        present = [atom for atom in atoms if atom_present(atom, context_text)]
        missing = [atom for atom in atoms if atom not in present]
        conflicts = [term for term in CONFLICT_TERMS.get(idx, []) if atom_present(term, context_text)]
        klass = classify(len(atoms), len(present), len(conflicts))
        rows.append({
            "one_based_index": idx,
            "cat": detail.get("cat"),
            "question": detail.get("question"),
            "ground_truth": detail.get("ground_truth"),
            "predicted": detail.get("predicted"),
            "score": detail.get("score"),
            "n_memories": detail.get("n_memories"),
            "atoms": atoms,
            "present_atoms": present,
            "missing_atoms": missing,
            "conflict_terms_present": conflicts,
            "coverage_class": klass,
        })
    rows.sort(key=lambda r: r["one_based_index"])
    counts = Counter(r["coverage_class"] for r in rows)
    by_category: dict[str, Counter[str]] = {}
    for r in rows:
        by_category.setdefault(str(r["cat"]), Counter())[r["coverage_class"]] += 1
    return {
        "label": label,
        "artifact": str(path),
        "row_count": len(rows),
        "coverage_counts": dict(sorted(counts.items())),
        "coverage_by_category": {k: dict(sorted(v.items())) for k, v in sorted(by_category.items())},
        "rows": rows,
    }


def best_row_view(audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_idx: dict[int, list[dict[str, Any]]] = {}
    for audit in audits:
        for row in audit["rows"]:
            item = dict(row)
            item["source_label"] = audit["label"]
            by_idx.setdefault(row["one_based_index"], []).append(item)
    # Prefer higher score; ties prefer more present atoms and fewer conflicts.
    def key(row: dict[str, Any]) -> tuple[float, int, int]:
        score = row.get("score")
        return (float(score if score is not None else -1), len(row["present_atoms"]), -len(row["conflict_terms_present"]))
    best = []
    for idx in sorted(by_idx):
        best.append(max(by_idx[idx], key=key))
    return best


def write_markdown(result: dict[str, Any], path: Path) -> None:
    best = result["best_rows"]
    counts = Counter(r["coverage_class"] for r in best)
    lines = [
        "# LOCOMO Gold-Object Coverage Audit — 2026-05-05",
        "",
        "Scope: artifact-only diagnostic over pinned 25-row canary artifacts; no live benchmark, no DB/runtime mutation.",
        "",
        "## Inputs",
        "",
    ]
    for audit in result["audits"]:
        lines.append(f"- `{audit['label']}`: `{audit['artifact']}`")
    lines.extend([
        "",
        "## Best-Row Coverage Summary",
        "",
        f"- Rows audited: `{len(best)}`",
    ])
    for klass, n in sorted(counts.items()):
        lines.append(f"- `{klass}`: `{n}`")
    lines.extend([
        "",
        "## Rows With Missing or Conflicting Gold Objects",
        "",
        "| Row | Cat | Score | Coverage | Present atoms | Missing atoms | Conflicts |",
        "|---:|---|---:|---|---|---|---|",
    ])
    for row in best:
        if row["coverage_class"] == "all_atoms_present":
            continue
        lines.append(
            f"| {row['one_based_index']} | {row['cat']} | {row.get('score')} | `{row['coverage_class']}` | "
            f"{', '.join(row['present_atoms']) or '—'} | {', '.join(row['missing_atoms']) or '—'} | "
            f"{', '.join(row['conflict_terms_present']) or '—'} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `all_atoms_present` rows are primarily synthesis/judge/answer-contract candidates if they still score below full credit.",
        "- `partial_atoms_present` rows need targeted retrieval expansion or evidence-completion before more answer shaping.",
        "- `no_atoms_present` rows are retrieval/context misses under the pinned final_context substrate.",
        "- `*_with_conflicts` rows need entity/role/source-provenance audit before tuning.",
        "",
        "## Next Step",
        "",
        "Use this audit to drive a default-off evidence coverage intervention: entity/time anchored expansion with explicit expected-object coverage telemetry on the preregistered 25-row slice only.",
    ])
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", required=True, help="LABEL=PATH treatment artifact JSON")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    audits = []
    for spec in args.artifact:
        if "=" not in spec:
            raise SystemExit(f"artifact must be LABEL=PATH: {spec}")
        label, raw_path = spec.split("=", 1)
        audits.append(audit_artifact(Path(raw_path), label))
    result = {
        "schema": "memibrium.locomo.gold_object_coverage_audit.v1",
        "scope": "artifact_only_pinned_25row_canary_no_runtime_mutation",
        "audits": audits,
        "best_rows": best_row_view(audits),
    }
    out_json = Path(args.out_json)
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_markdown(result, Path(args.out_md))
    print(json.dumps({
        "ok": True,
        "out_json": str(out_json),
        "out_md": args.out_md,
        "best_counts": dict(Counter(r["coverage_class"] for r in result["best_rows"])),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
