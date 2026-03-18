# Distribution: Skills-Over-MCP Architecture

> **The line between skill and MCP is dissolving.** People are wrapping
> MCPs in skills, wrapping skills in MCPs, and bundling both into plugins.
> Memibrium ships as **one skill + one MCP server = governed memory for any agent.**

## The Pattern

```
┌─────────────────────────────────────────────────┐
│  SKILL (SKILL.md)                               │
│  ─────────────────                              │
│  Behavioral governance layer                    │
│  "How the agent should think about memory"      │
│  Loaded into system prompt at session start     │
│  No code. No compilation. No deployment.        │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP SERVER (server.py on :9999)          │  │
│  │  ─────────────────────────                │  │
│  │  Execution layer                          │  │
│  │  CT lifecycle, W(k,t), δ-decay, pgvector  │  │
│  │  8 tools called via standard MCP protocol │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Why this is better than exposing 8 raw MCP tools:**

1. **Fewer tokens wasted.** One skill teaches the agent the whole governance
   model. Without it, the agent sees 8 disconnected tools and has to figure
   out when/how to use each one every single call.
2. **Permissions are set.** The skill hardwires rules like "never auto-crystallize"
   and "contradictions don't overwrite." Without the skill, nothing prevents
   an agent from calling `confirm` on its own output.
3. **No RL training needed.** MemSkill (NeurIPS 2024) needs millions of RL
   steps to learn which memory operations to apply. The skill pre-loads the
   governance — the agent just follows instructions.
4. **Distribution is free.** The skill ecosystem already exists: Microsoft has
   132+ installable skills, FastMCP 3.0 has a native Skills Provider,
   Skills-ContextManager exposes skills via MCP dynamically, and 11,000+
   AI agent tools are indexed across platforms.

## Install Paths

### Claude Code (Plugin — recommended)

```bash
# Add the marketplace (one-time)
claude plugin marketplace add rvalen1123/memibrium

# Install the plugin (skill + MCP auto-wired)
claude plugin install memibrium@memibrium

# Or direct install from GitHub
claude plugin install https://github.com/rvalen1123/memibrium
```

This installs:
- The `crystallization-memory` skill (behavioral governance)
- The `.mcp.json` wiring to the Memibrium MCP server

### Copilot CLI

```bash
# Add marketplace and install
/plugin marketplace add rvalen1123/memibrium
/plugin install memibrium@memibrium
```

### Cursor

```jsonc
// Add to .cursor/mcp.json
{
  "mcpServers": {
    "memibrium": {
      "url": "http://localhost:9999/mcp",
      "description": "Sovereign AI memory with CT governance"
    }
  }
}
```

Copy `plugins/memibrium/skills/crystallization-memory/SKILL.md` to
your Cursor rules or custom instructions directory.

### Any MCP-Compatible Client

1. Start the Memibrium server: `python server.py`
2. Point your client's MCP config at `http://localhost:9999/mcp`
3. Load the SKILL.md into your system prompt or custom instructions
4. The agent now has governed memory

## What Ships (Plugin Layout)

```
memibrium/
├── .claude-plugin/
│   └── marketplace.json                    # Marketplace registry
├── plugins/
│   └── memibrium/
│       ├── .claude-plugin/
│       │   └── plugin.json                 # Plugin manifest
│       ├── .mcp.json                       # MCP server config (auto-wired)
│       └── skills/
│           └── crystallization-memory/
│               └── SKILL.md                # The governance skill
├── server.py                               # MCP server (8 tools)
├── deploy/                                 # Terraform for cloud deploy
└── DISTRIBUTION.md                         # This file
```

This follows the same pattern as [microsoft/azure-skills](https://github.com/microsoft/azure-skills):
`.claude-plugin/marketplace.json` at repo root, plugin payload under
`plugins/`, skills + `.mcp.json` bundled inside the plugin directory.

**The governance is the product. Everything else is plumbing.**

## Ecosystem Context (March 2026)

| What | Who | Relevance |
|---|---|---|
| Skills as markdown + YAML frontmatter | Anthropic, Microsoft | Skill format standard |
| FastMCP 3.0 Skills Provider | FastMCP | Skills ↔ MCP bridge |
| Skills-ContextManager | Community | Dynamic skill loading via MCP |
| MCP Skill Server | Community | Skill dirs → MCP API |
| Sentry bundled agent | Sentry | MCP tools wrapped as single skill |
| 11,000+ indexed tools | PulseMCP | Distribution/discovery layer |
| 132+ one-click skills | Microsoft Copilot | Skill marketplace |

## vs. MemSkill (NeurIPS 2024)

MemSkill proved learnable memory skills beat hand-coded operations.
Their approach: train a controller via RL to select which memory
"skill" to apply (write, update, retrieve, delete, consolidate).

Memibrium's approach: **skip the RL entirely.** The skill is pre-loaded
behavioral guidance. The governance is hardwired in the markdown.
The MCP handles execution. No training loop, no skill selection model,
no "closed-loop evolution" where the designer proposes new skills
from failure cases — that's what `/mcp/confirm` does, except governed
by human consensus instead of LLM self-evaluation.

| Dimension | MemSkill | Memibrium |
|---|---|---|
| Skill selection | RL-trained controller | Pre-loaded SKILL.md |
| Training cost | Millions of RL steps | Zero (write once) |
| Governance | ML confidence | Human consensus |
| Distribution | Custom framework | Standard skill + MCP |
| Crystallization | N/A | Patent-pending CT lifecycle |
| Portability | Their framework only | Any MCP client |

---

*"The system gets wiser — not merely smarter — because the wisdom
is human wisdom, accumulated through deliberate consensus and
preserved through sovereign governance."*
