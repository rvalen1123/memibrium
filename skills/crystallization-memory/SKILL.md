# Skills have moved

The Memibrium skill and MCP config are now packaged as a proper plugin:

```
plugins/memibrium/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── .mcp.json                # MCP server config (auto-wired on install)
└── skills/
    └── crystallization-memory/
        └── SKILL.md          # The governance skill
```

## Install

```bash
# Claude Code
claude plugin marketplace add rvalen1123/memibrium
claude plugin install memibrium@memibrium

# Or direct install
claude plugin install https://github.com/rvalen1123/memibrium
```

See [DISTRIBUTION.md](../DISTRIBUTION.md) for all install paths.
