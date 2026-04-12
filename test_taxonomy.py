#!/usr/bin/env python3
"""
Unit Tests — Knowledge Taxonomy
=================================
Tests the 28-category classifier, tier assignment, skip list,
and taxonomy import/export. No DB or LLM dependencies.

Usage:
  python test_taxonomy.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from knowledge_taxonomy import (
    KnowledgeClassifier, Category, DEFAULT_CATEGORIES,
    DEFAULT_SKIP_KEYWORDS, UNCATEGORIZED,
)

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")
    return condition


def run_tests():
    global PASS, FAIL

    clf = KnowledgeClassifier()

    # ── 1. Category count ──
    print("\n--- 1. Taxonomy Structure ---")
    test("30 categories loaded", len(clf.categories) == 30,
         f"got {len(clf.categories)}")

    tiers = {}
    for c in clf.categories:
        tiers[c.tier] = tiers.get(c.tier, 0) + 1
    test("Has crystallize tier", "crystallize" in tiers)
    test("Has hot tier", "hot" in tiers)
    test("Has archive tier", "archive" in tiers)
    test("Crystallize count = 16", tiers.get("crystallize") == 16,
         f"got {tiers.get('crystallize')}")
    test("Hot count = 13", tiers.get("hot") == 13,
         f"got {tiers.get('hot')}")
    test("Archive count = 1+", tiers.get("archive", 0) >= 1,
         f"got {tiers.get('archive')}")

    # ── 2. Classification accuracy ──
    print("\n--- 2. Classification Accuracy ---")

    # Patent CT/KEOS
    cats = clf.classify("Crystallization theory implements delta-decay for knowledge governance")
    ids = [c.id for c in cats]
    test("CT/KEOS classified", "patent-ct-keos-stg" in ids, f"got {ids}")

    # Memibrium architecture
    cats = clf.classify("The memibrium server uses pgvector dual-tier with mcp/confirm")
    ids = [c.id for c in cats]
    test("Memibrium classified", "arch-memibrium" in ids, f"got {ids}")

    # Medvinci business
    cats = clf.classify("Medvinci research DTC peptide launch went well")
    ids = [c.id for c in cats]
    test("Medvinci classified", "biz-medvinci-research" in ids, f"got {ids}")

    # Music project
    cats = clf.classify("OpenClaw integration with Ableton via the DAW chain")
    ids = [c.id for c in cats]
    test("Music project classified", "project-music" in ids, f"got {ids}")

    # WordPress
    cats = clf.classify("WooCommerce template override for product pages")
    ids = [c.id for c in cats]
    test("WordPress classified", "arch-wordpress-woocommerce" in ids, f"got {ids}")

    # Legal/compliance
    cats = clf.classify("HIPAA compliance requirements for the FDA regulation")
    ids = [c.id for c in cats]
    test("Legal classified", "legal-compliance" in ids, f"got {ids}")

    # Personal
    cats = clf.classify("I'm feeling like I need to self-reflect on my relationship")
    ids = [c.id for c in cats]
    test("Personal classified", "personal-introspection" in ids, f"got {ids}")

    # ── 3. Multi-category hits ──
    print("\n--- 3. Multi-Category Classification ---")
    cats = clf.classify(
        "The memibrium architecture uses crystallization theory with witness chains")
    ids = [c.id for c in cats]
    test("Multi-hit: memibrium + CT", len(cats) >= 2, f"got {ids}")

    # ── 4. Uncategorized fallback ──
    print("\n--- 4. Uncategorized Fallback ---")
    cats = clf.classify("The weather is nice today and I had coffee")
    test("Falls to uncategorized", cats[0].id == "uncategorized",
         f"got {cats[0].id}")
    test("Uncategorized tier is archive", cats[0].tier == "archive")

    # ── 5. Tier assignment ──
    print("\n--- 5. Tier Priority ---")
    cats, tier = clf.classify_with_tier(
        "The crystallization theory patent was filed for memibrium")
    test("Highest tier = crystallize", tier == "crystallize",
         f"got {tier}")

    cats, tier = clf.classify_with_tier("Medvinci research shipping update")
    test("Business tier = hot", tier == "hot", f"got {tier}")

    cats, tier = clf.classify_with_tier("generic react component debugging")
    test("Coding tier = archive", tier == "archive", f"got {tier}")

    # ── 6. Skip list ──
    print("\n--- 6. Skip List ---")
    test("Wound care skipped",
         clf.should_skip("wound care MSC 2.0 project update"))
    test("ICD-10 skipped",
         clf.should_skip("icd-10 coding for arterial ulcer"))
    test("Normal content not skipped",
         not clf.should_skip("Memibrium architecture review"))
    test("Empty not skipped", not clf.should_skip(""))

    # ── 7. Category lookup ──
    print("\n--- 7. Category Lookup ---")
    cat = clf.get_category("patent-ct-keos-stg")
    test("Lookup by ID works", cat.id == "patent-ct-keos-stg")
    test("Has correct title", "Crystallization" in cat.title)
    test("Has correct tier", cat.tier == "crystallize")

    cat = clf.get_category("nonexistent-xyz")
    test("Unknown returns uncategorized", cat.id == "uncategorized")

    # ── 8. Export / Import ──
    print("\n--- 8. Export / Import ---")
    exported = clf.export_taxonomy()
    test("Export returns list", isinstance(exported, list))
    test("Export count matches", len(exported) == 30,
         f"got {len(exported)}")
    test("Export has id/title/tier/keywords",
         all({"id", "title", "tier", "keywords"} <= set(e.keys())
             for e in exported))

    # Roundtrip
    clf2 = KnowledgeClassifier()
    clf2.import_taxonomy(exported)
    test("Roundtrip preserves count", len(clf2.categories) == 30)
    cats2 = clf2.classify("crystallization theory knowledge governance")
    test("Roundtrip classifies same",
         cats2[0].id == "patent-ct-keos-stg",
         f"got {cats2[0].id}")

    # JSON serialization roundtrip
    json_str = json.dumps(exported)
    reimported = json.loads(json_str)
    clf3 = KnowledgeClassifier()
    clf3.import_taxonomy(reimported)
    test("JSON roundtrip works", len(clf3.categories) == 30)

    # ── 9. Add / Remove ──
    print("\n--- 9. Dynamic Taxonomy ---")
    clf.add_category(Category("test-cat", "Test Category", "hot", ["test keyword xyz"]))
    test("Add increases count", len(clf.categories) == 31)
    cats = clf.classify("this has test keyword xyz in it")
    test("New category classifies", cats[0].id == "test-cat")

    removed = clf.remove_category("test-cat")
    test("Remove returns True", removed)
    test("Remove decreases count", len(clf.categories) == 30)

    not_removed = clf.remove_category("nonexistent")
    test("Remove nonexistent returns False", not not_removed)

    # ── 10. Case insensitivity ──
    print("\n--- 10. Case Insensitivity ---")
    cats = clf.classify("CRYSTALLIZATION THEORY KEOS STG")
    ids = [c.id for c in cats]
    test("Uppercase text matches", "patent-ct-keos-stg" in ids, f"got {ids}")

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'='*50}")
    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
