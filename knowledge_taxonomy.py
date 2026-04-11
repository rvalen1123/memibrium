#!/usr/bin/env python3
"""
Memibrium Knowledge Taxonomy
=========================================================

Configurable category taxonomy with CT tier assignments.
Extracted from RV-Brain's run-knowledge-test.py and formalized
as the default taxonomy for Memibrium's ingestion engine.

Each category has:
  - id: stable identifier for the domain partition
  - title: human-readable name
  - tier: CT lifecycle tier (crystallize | hot | archive)
  - keywords: list of keyword triggers for classification

Author: Ricky Valentine / Orchard Holdings LLC
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Category:
    id: str
    title: str
    tier: str  # crystallize | hot | archive
    keywords: list[str] = field(default_factory=list)


# ── Default Taxonomy ───────────────────────────────────────────────

DEFAULT_CATEGORIES: list[Category] = [
    # ── Patents (CRYSTALLIZE) ──────────────────────────────────────
    Category("patent-forward-design", "Patent: Forward Design", "crystallize",
             ["forward design", "conversational workspace", "card composition engine",
              "layout renderer", "intent router", "workflow state machine",
              "information summoning", "workspace orchestration", "information choreography"]),

    Category("patent-ct-keos-stg", "Patent: Crystallization Theory / KEOS / STG", "crystallize",
             ["crystallization theory", "keos", "stg", "mortal knowledge",
              "w(k,t)", "witness chain", "delta-decay", "knowledge governance",
              "gets smarter without getting wiser", "sovereign temporal graph", "knowledge lifecycle"]),

    Category("patent-visiting-ai", "Patent: Visiting AI / Rural Healthcare", "crystallize",
             ["visiting ai", "rural healthcare", "ephemeral ai container",
              "healthcare mesh", "clinical ai infrastructure", "cognitum", "congresswoman garcia"]),

    Category("patent-music-ip", "Patent: Music / DAW / Neuroconnective IP", "crystallize",
             ["neuroconnective", "daw assist", "beatroulette", "production dna",
              "zero-knowledge plugin", "creation attestation", "inner voice",
              "biometric creation provenance", "music patent"]),

    Category("patent-healthcare-general", "Patent: Healthcare Interoperability / Data Fabric", "crystallize",
             ["healthcare data fabric", "fhir translation", "agent-to-agent protocol",
              "healthcare interoperability", "phi-free mesh", "data format translation",
              "insurance negotiation system", "clinical context awareness",
              "healthcare patent", "provisional patent", "uspto", "patent claim",
              "prior art", "patent application"]),

    Category("patent-exosome", "Patent: Exosome / saRNA", "crystallize",
             ["exosome", "sarna", "63/960,158"]),

    # ── Architecture (CRYSTALLIZE) ─────────────────────────────────
    Category("arch-memibrium", "Architecture: Memibrium", "crystallize",
             ["memibrium", "ruvector", "pgvector dual-tier", "mcp/confirm",
              "crystallization path", "memory equilibrium", "leann cold", "rv-brain", "ingestion engine"]),

    Category("arch-azure-infra", "Architecture: Azure Infrastructure", "crystallize",
             ["azure vm", "premier-vm", "azure app service", "azure credits",
              "staging slots", "managed mysql", "azure cdn", "azure ai foundry",
              "azure infrastructure", "azure deployment", "azure resource"]),

    Category("arch-wordpress-woocommerce", "Architecture: WordPress / WooCommerce Stack", "crystallize",
             ["woocommerce", "wordpress optimization", "wp rocket", "redis object cache",
              "php 8.3", "woocommerce template", "wordpress plugin", "gutenberg block", "wp-cli",
              "wordpress theme", "wordpress hook", "wordpress rest api", "wordpress custom",
              "wordpress child theme", "woocommerce product", "woocommerce order"]),

    Category("arch-payment-processing", "Architecture: Payment Processing", "crystallize",
             ["stripe termination", "high-risk merchant", "payment processing",
              "authorize.net", "nmi gateway", "payment plugin", "merchant account"]),

    Category("arch-mcp-tools", "Architecture: MCP / Tool Integrations", "crystallize",
             ["model context protocol", "mcp server", "mcp tool", "mcporter", "mcp integration"]),

    Category("arch-planning", "Architecture: Technical Planning / System Design", "crystallize",
             ["technical plan", "architecture plan", "system design", "project structure",
              "implementation plan", "deployment plan", "technical roadmap",
              "restructur", "codebase review", "directory structure",
              "migration plan", "integration plan"]),

    # ── Business (HOT) ─────────────────────────────────────────────
    Category("biz-medvinci-research", "Business: Medvinci Research", "hot",
             ["medvinci", "dtc peptide", "amber affiliate", "whatsapp group", "medvinci research"]),

    Category("biz-lrs-wholesale", "Business: Limitless Research Supplies (LRS)", "hot",
             ["limitless research", "lrs", "b2b wholesale", "fjord signal", "premier bio labs", "pbl"]),

    Category("biz-prime-wellness", "Business: Prime Wellness", "hot",
             ["prime wellness", "concierge medicine", "el dorado hills", "dr. tuhin",
              "tuhin chaudhury", "repeatmd"]),

    Category("biz-peptide-ops", "Business: Peptide Operations / Supply Chain", "hot",
             ["wwb china", "peptide supplier", "coa verification", "certificate of analysis",
              "bac water", "fulfillment", "peptide compliance", "research chemical",
              "peptide margin", "peptide product", "peptide catalog"]),

    Category("biz-affiliate", "Business: Affiliate Marketing / GoAffPro", "hot",
             ["goaffpro", "affiliate program", "affiliate marketing", "referral tracking",
              "commission structure", "affiliate sync", "affiliate coupon"]),

    Category("biz-deals-ip", "Business: IP Deals / Licensing / M&A", "crystallize",
             ["orchard holdings", "ip licensing", "creator royalty", "field-of-use", "hank",
              "pnc", "10m funding", "enterprise migration", "ip deal", "holding company",
              "operating agreement"]),

    Category("biz-funding", "Business: Funding / Investor Strategy", "hot",
             ["investor pitch", "funding target", "sovereign wealth", "congressional backing",
              "series a", "pitch deck", "investor update"]),

    # ── Projects (HOT) ─────────────────────────────────────────────
    Category("project-whalewatch", "Project: WhaleWatch Sports Analytics", "hot",
             ["whalewatch", "whale watch", "sharp money", "sports betting",
              "discord bot", "betting analytics"]),

    Category("project-music", "Project: Music / Neuroconnective Platform", "hot",
             ["neuroconnective platform", "music production", "ableton", "fl studio", "livekit",
              "paperclip orchestration", "openclaw", "chatterbox turbo", "kokoro tts",
              "artist dna", "studio ui"]),

    Category("project-once-ui", "Project: Once UI / Lorant Partnership", "hot",
             ["once ui", "lorant", "magic agent", "co-invent", "design system partnership"]),

    Category("healthcare-payer", "Healthcare: Payer Integration / Insurance", "hot",
             ["optum", "eligibility", "payer", "claims api", "mirth connect",
              "cms api", "insurance api", "edi 837", "edi 835", "clearinghouse",
              "revenue cycle", "accounts receivable", "national asp"]),

    # ── Meta / Technical ───────────────────────────────────────────
    Category("tech-coding-journey", "Meta: Coding Journey / Builder Stats", "crystallize",
             ["first github repo", "github contributions", "lovable platform",
              "self-taught developer", "sherpa gaming", "surgery tech",
              "coding origin", "builder stats"]),

    Category("tech-fine-tuning", "Technical: Fine-Tuning / AI Training", "hot",
             ["fine-tuning", "fine tuning", "jsonl", "training data", "4.1 mini",
              "4.1 nano", "azure ai foundry", "training pair"]),

    Category("tech-blockchain-coa", "Technical: Blockchain / COA Verification", "hot",
             ["blockchain verification", "coa blockchain", "on-chain",
              "smart contract", "certificate verification"]),

    Category("strategy-brand", "Strategy: Brand Voice / Content / Marketing", "hot",
             ["brand voice", "content strategy", "social media", "linkedin post",
              "twitter post", "marketing strategy", "brand guidelines",
              "rigorous and irreverent"]),

    Category("legal-compliance", "Legal: HIPAA / FDA / Regulatory", "crystallize",
             ["hipaa compliance", "fda regulation", "research use disclaimer",
              "fda approved", "regulatory requirement", "legal structure",
              "wyoming llc", "entity structure", "hipaa violation",
              "regulatory compliance"]),

    # ── Low-priority ───────────────────────────────────────────────
    Category("tech-general-coding", "Technical: General Coding / Debugging", "archive",
             ["react component", "typescript", "node.js", "laravel", "filament",
              "npm install", "docker", "github repo", "pull request",
              "css", "tailwind", "shadcn", "deploy script", "ssh",
              "digital ocean", "error message", "stack trace", "debug"]),

    Category("personal-introspection", "Personal: Reflection / Relationships / Growth", "crystallize",
             ["relationship", "feeling like", "introspect", "self-reflect",
              "personal growth", "my kids", "my daughter", "my son", "my wife",
              "my family", "mental health", "burnout", "work-life",
              "who am i", "what kind of person", "proud of", "regret",
              "grateful", "therapy", "journal", "self-aware"]),
]

UNCATEGORIZED = Category("uncategorized", "Uncategorized", "archive", [])

# ── Skip List (dead projects, noise) ──────────────────────────────

DEFAULT_SKIP_KEYWORDS: list[str] = [
    "wound care", "msc 2.0", "msc mvp", "msc-mv", "icd-10", "icd10",
    "wound codes", "wound coding", "arterial ulcer", "surgical wound",
    "traumatic wound", "wound-care-react", "woundcare", "mscwoundcare",
    "wound distribution",
]


# ── Classifier ─────────────────────────────────────────────────────

class KnowledgeClassifier:
    """
    Keyword-based classifier with CT tier assignment.

    Usage:
        clf = KnowledgeClassifier()
        results = clf.classify("text about memibrium and pgvector")
        # [Category(id='arch-memibrium', tier='crystallize', ...)]
    """

    def __init__(self, categories: Optional[list[Category]] = None,
                 skip_keywords: Optional[list[str]] = None):
        self.categories = categories or DEFAULT_CATEGORIES
        self.skip_keywords = [kw.lower() for kw in (skip_keywords or DEFAULT_SKIP_KEYWORDS)]
        self.uncategorized = UNCATEGORIZED

    def should_skip(self, text: str) -> bool:
        """Check if content matches skip list (dead projects)."""
        t = text.lower()
        return any(kw in t for kw in self.skip_keywords)

    def classify(self, text: str) -> list[Category]:
        """
        Classify text into one or more categories.
        Returns list of matching Category objects, or [UNCATEGORIZED].
        """
        t = text.lower()
        matches = []
        for cat in self.categories:
            for kw in cat.keywords:
                if kw.lower() in t:
                    matches.append(cat)
                    break
        return matches if matches else [self.uncategorized]

    def classify_with_tier(self, text: str) -> tuple[list[Category], str]:
        """
        Classify and return the highest-priority tier.
        Priority: crystallize > hot > archive
        """
        cats = self.classify(text)
        tier_priority = {"crystallize": 0, "hot": 1, "archive": 2}
        best_tier = min(cats, key=lambda c: tier_priority.get(c.tier, 99)).tier
        return cats, best_tier

    def get_category(self, cid: str) -> Category:
        for c in self.categories:
            if c.id == cid:
                return c
        return self.uncategorized

    def add_category(self, category: Category) -> None:
        """Add a new category to the taxonomy."""
        self.categories.append(category)

    def remove_category(self, cid: str) -> bool:
        """Remove a category by ID. Returns True if found."""
        before = len(self.categories)
        self.categories = [c for c in self.categories if c.id != cid]
        return len(self.categories) < before

    def export_taxonomy(self) -> list[dict]:
        """Export taxonomy as serializable dicts."""
        return [{"id": c.id, "title": c.title, "tier": c.tier,
                 "keywords": c.keywords} for c in self.categories]

    def import_taxonomy(self, data: list[dict]) -> None:
        """Import taxonomy from dicts (e.g., loaded from JSON config)."""
        self.categories = [
            Category(d["id"], d["title"], d["tier"], d.get("keywords", []))
            for d in data
        ]
