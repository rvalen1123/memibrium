---
name: crystallization-memory
description: >
  Governed memory management using Crystallization Theory (CT) lifecycle.
  Use this skill whenever managing persistent memory, storing knowledge
  across sessions, recalling past context, confirming or validating
  knowledge, or governing what an agent remembers and forgets. Also
  trigger when: user mentions "remember this", "what do you know about",
  "forget", "memory", "knowledge lifecycle", "crystallize", "freeze
  memory", "revert memory", or any memory governance operation. This
  skill wraps the Memibrium MCP server — the agent follows behavioral
  rules here, the MCP handles storage/lifecycle/math underneath.
---

# Crystallization Memory

> "It gets smarter without getting wiser." — That's the failure mode
> this skill prevents.

## What This Skill Does

This skill teaches the agent **how to think about memory governance**.
The Memibrium MCP server underneath handles storage, embeddings,
lifecycle transitions, and the W(k,t) scoring math. The agent never
touches governance internals directly — it follows these behavioral
rules, and all memory operations route through the MCP.

## Architecture: Skill Over MCP

```
Agent (any: Claude Code, Cursor, Copilot, etc.)
  │
  ├─ This skill (SKILL.md) — behavioral rules, loaded into system prompt
  │   "How to think about memory"
  │
  └─ Memibrium MCP Server — 8 tools, via .mcp.json bundled with this plugin
      "How to store/retrieve/govern memory"
      retain, recall, reflect, confirm, freeze, revert, consolidate, dashboard
```

The skill is the **governance layer**. The MCP is the **execution layer**.
The agent never needs to understand W(k,t) math, δ-decay rates, or
witness chain hashing. It follows the rules below.

## Core Rules (Always Apply)

### Rule 1: All Knowledge Enters as Untrusted

When storing new information via `retain`:
- New knowledge starts in OBSERVATION state — never treat it as authoritative
- The MCP scores importance and may auto-promote to ACCEPTED, but this is
  informational — it does NOT make the knowledge trustworthy
- Only human confirmation (`confirm`) can move knowledge to CRYSTALLIZED

### Rule 2: Check State Before Citing

When retrieving knowledge via `recall`:
- **CRYSTALLIZED** knowledge → cite with confidence, this has been human-validated
- **ACCEPTED** knowledge → cite but flag as "believed but unconfirmed"
- **OBSERVATION** knowledge → mention only if directly relevant, flag as "preliminary"
- **DECAYING** knowledge (low W(k,t)) → flag with: "This information may be outdated"
- **SHED** knowledge → do not surface unless specifically asked for historical context
- Always prefer CRYSTALLIZED over ACCEPTED over OBSERVATION when multiple memories match

### Rule 3: Human Confirmation is the ONLY Crystallization Path

- When a user validates, corrects, or explicitly confirms a piece of knowledge,
  call `confirm` with the memory_id
- NEVER assume knowledge is crystallized because it "seems right" or has been
  repeated — only `confirm` can crystallize
- This is the architectural distinction: ML confidence ≠ human consensus

### Rule 4: Classify Knowledge on Storage

When storing knowledge via `retain`, include domain context:
- **Universal** (applies across all contexts) → use domain: "universal"
- **Project-specific** (tied to a codebase, product, or context) → use domain: "{project-name}"
- **Personal** (user preferences, biographical) → use domain: "personal"
- **Temporal** (events, deadlines, states that expire) → use domain: "temporal"

### Rule 5: Contradictions Trigger Investigation, Not Overwrites

When `recall` returns knowledge that contradicts new information:
1. DO NOT silently overwrite the stored memory
2. Surface the contradiction to the user explicitly
3. If the existing memory is CRYSTALLIZED, it takes precedence until the user
   explicitly confirms the new information
4. Store the new contradicting information as a new OBSERVATION — let the
   lifecycle engine resolve it through human confirmation
5. If both are CRYSTALLIZED and contradict, flag for manual review via `freeze`

### Rule 6: Use Reflect for Synthesis, Not Recall

- `recall` = "find specific memories matching this query"
- `reflect` = "synthesize everything known about this topic"
- For decision-making, strategic planning, or "what do we know about X" → use `reflect`
- For specific lookups like "what was the API key format" → use `recall`

### Rule 7: Freeze Before Destructive Changes

When the user is about to make a major decision based on stored knowledge:
- Call `freeze` on the relevant memories before proceeding
- This creates a snapshot and exempts memories from δ-decay
- If the decision turns out wrong, `revert` restores the pre-decision state

### Rule 8: Proactive Consolidation Awareness

- The MCP runs background δ-decay every 30 minutes automatically
- Memories that aren't confirmed will naturally decay and eventually shed
- This is by design — memories must earn survival through human validation
- If a user references knowledge that has been shed, inform them:
  "This was previously stored but decayed due to lack of confirmation.
   Would you like me to re-store and confirm it?"

## MCP Tool Reference (Quick Guide)

| Tool | When to Use | Key Parameters |
|---|---|---|
| `retain` | Storing new information | `content` (required), `source`, `domain` |
| `recall` | Finding specific memories | `query` (required), `top_k`, `domain` |
| `reflect` | Synthesizing knowledge about a topic | `topic` (required), `top_k`, `domain` |
| `confirm` | User validates/confirms knowledge | `memory_id` (required), `weight` |
| `freeze` | Protecting knowledge from decay | `memory_id` (required), `reason` |
| `revert` | Restoring from snapshot | `memory_id` (required), `snapshot_id` |
| `consolidate` | Manual decay/promote cycle | (none) |
| `dashboard` | System health/status | (none) |

## MCP Connection

The Memibrium MCP server is configured automatically via the `.mcp.json`
bundled with this plugin. When installed, your agent gets both the skill
(this file) and the MCP wiring in one step.

If running standalone, the server exposes tools at:

```
Base URL: http://localhost:9999/mcp
Tool manifest: GET /mcp/tools
Each tool:     POST /mcp/{tool_name}
```

## Anti-Patterns (Never Do These)

1. **Never store everything** — If it's not worth remembering, don't `retain` it.
   Transient conversation, greetings, meta-discussion about memory itself → skip.
2. **Never auto-crystallize** — Even if you're "very confident" something is true,
   it MUST go through `confirm`. This is the patent's core negative limitation.
3. **Never ignore lifecycle state** — A SHED memory cited as fact is a governance
   failure. Always check state.
4. **Never bypass the MCP** — Don't store memory in local files, env vars, or
   conversation context as a substitute. All persistent knowledge goes through
   Memibrium.
5. **Never expose raw W(k,t) scores to users** — The weight function is internal.
   Translate to human terms: "highly confirmed", "preliminary", "fading".

## Example Interaction Patterns

**User says something worth remembering:**
```
User: "Our API rate limit is 1000 req/min on the Pro plan."
Agent: [calls retain with content="API rate limit: 1000 req/min on Pro plan",
        source="user_statement", domain="project-api"]
Agent: "Got it — I've stored that. Want me to confirm it as validated knowledge?"
```

**User asks about past context:**
```
User: "What do we know about the deployment architecture?"
Agent: [calls reflect with topic="deployment architecture"]
Agent: [synthesizes results, flagging lifecycle states]
```

**User confirms knowledge:**
```
User: "Yes, that rate limit is correct."
Agent: [calls confirm with memory_id from the recall result]
Agent: "Confirmed — that's now crystallized knowledge."
```

**Contradiction detected:**
```
Agent: [recalls "API rate limit is 1000 req/min" (CRYSTALLIZED)]
User: "Actually they changed it to 2000 req/min last week."
Agent: "I have crystallized knowledge saying 1000 req/min. You're saying
        it's now 2000. I'll store the update as a new observation —
        would you like to confirm the new rate and shed the old one?"
```
