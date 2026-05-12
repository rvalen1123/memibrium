#!/usr/bin/env python3
"""Extract a deterministic LOCOMO judge-leniency probe subset from pinned AP baselines.

This is scaffold-only: it reads pinned upstream artifacts and writes a frozen subset
for future scoring. It does not call judges, launch benchmarks, or touch Memibrium runtime state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

CATEGORY_NAMES = {
    "1": "multi_hop",
    "2": "temporal",
    "3": "open_domain",
    "4": "single_hop",
    "5": "adversarial",
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten_ap(path: Path, strategy: str) -> list[dict]:
    obj = json.loads(path.read_text())
    detailed = obj["detailed_results"]
    rows = []
    for conversation_id in sorted(detailed):
        for item in detailed[conversation_id]:
            category = str(item.get("category"))
            rows.append(
                {
                    "conversation_id": conversation_id,
                    "question_id": item["question_id"],
                    "category": category,
                    "category_name": CATEGORY_NAMES.get(category, f"category_{category}"),
                    "question": item["question"],
                    "golden_answer": item["golden_answer"],
                    "probe_answer": item["generated_answer"],
                    "strategy": strategy,
                    "expected_label": "incorrect",
                    "source_artifact": str(path),
                    "source_artifact_sha256": sha256_path(path),
                }
            )
    return rows


def pick_balanced(rows_by_strategy: dict[str, list[dict]], per_category_per_strategy: int) -> list[dict]:
    selected = []
    for strategy in sorted(rows_by_strategy):
        by_cat = defaultdict(list)
        for row in rows_by_strategy[strategy]:
            by_cat[row["category"]].append(row)
        for category in sorted(by_cat):
            if category == "5":
                # Published AP baselines are categories 1-4 only. Keep category-5 explicit.
                continue
            selected.extend(by_cat[category][:per_category_per_strategy])
    return selected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", required=True, type=Path)
    ap.add_argument("--v2", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--per-category-per-strategy", type=int, default=5)
    ap.add_argument("--upstream-commit", required=True)
    ns = ap.parse_args()

    rows_by_strategy = {
        "specific_wrong_v1": flatten_ap(ns.v1, "specific_wrong_v1"),
        "vague_topical_v2": flatten_ap(ns.v2, "vague_topical_v2"),
    }
    selected = pick_balanced(rows_by_strategy, ns.per_category_per_strategy)
    for idx, row in enumerate(selected, start=1):
        row["probe_item_id"] = f"judge_leniency_probe_{idx:03d}"

    out_obj = {
        "artifact_type": "locomo_judge_leniency_probe_subset",
        "version": 1,
        "description": "Frozen intentionally-wrong-but-plausible answer subset from dial481/locomo-audit AP baselines. Use unchanged for judge-leniency comparisons across future LOCOMO runs.",
        "upstream": {
            "repo": "https://github.com/dial481/locomo-audit.git",
            "commit": ns.upstream_commit,
            "v1_source": str(ns.v1),
            "v1_source_sha256": sha256_path(ns.v1),
            "v2_source": str(ns.v2),
            "v2_source_sha256": sha256_path(ns.v2),
        },
        "selection": {
            "method": "deterministic: first N items by conversation/question order for each category 1-4 and each AP strategy",
            "per_category_per_strategy": ns.per_category_per_strategy,
            "categories_included": ["1", "2", "3", "4"],
            "category_5_note": "Upstream AP baselines exclude category 5/adversarial; category-5 scoring must be handled separately and labeled original/corrected/both.",
            "total_items": len(selected),
        },
        "items": selected,
    }
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(out_obj, indent=2, sort_keys=True) + "\n")
    print(f"wrote={ns.out}")
    print(f"sha256={sha256_path(ns.out)}")
    print(f"items={len(selected)}")


if __name__ == "__main__":
    main()
