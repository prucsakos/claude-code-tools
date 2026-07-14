# MCP servers

MCP (Model Context Protocol) server configurations for Claude Code.

Nothing here yet — configs will be added as `<name>/` folders, each containing:

- `README.md` — what the server does and how to set it up
- `.mcp.json` — the config snippet to merge into your project's `.mcp.json` or add via `claude mcp add`

## Adding a server to Claude Code

```bash
# Project-scoped (checked into the repo, shared with the team)
claude mcp add --scope project <name> -- <command> [args...]

# User-scoped (available in all your projects)
claude mcp add --scope user <name> -- <command> [args...]
```
