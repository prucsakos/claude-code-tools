# claude-code-tools

A collection of reusable [Claude Code](https://claude.com/claude-code) tools: slash commands, MCP server configs, and agent workflows.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Command | [`/team`](commands/team.md) | Spin up a team of N parallel Sonnet workers to tackle a task |
| Command | [`/teach`](commands/teach.md) | Teach a concept via reusable mental models, linked to a personal Concept Vocabulary repo |
| MCP | [BlenderMCP](https://github.com/ahujasid/blender-mcp) | Connect an MCP-compatible AI client to Blender for scene creation and manipulation |

## Installation

### Commands

Copy any command file into your commands directory:

```bash
# Available in every project (user-level)
cp commands/team.md ~/.claude/commands/

# Or per-project
cp commands/team.md your-project/.claude/commands/
```

Then use it inside Claude Code:

```
/team 4 "Refactor the API layer and add tests"
/team "Audit the codebase for security issues"   # Claude picks the optimal team size
/teach "Kalman filter"
```

### MCP servers

MCP server configs live in [`mcps/`](mcps/). See that folder's README for setup.

Related project: [BlenderMCP](https://github.com/ahujasid/blender-mcp) connects MCP-compatible AI clients to Blender through an MCP server and Blender add-on.

## Repository layout

```
commands/   # Slash commands (markdown files, one per command)
mcps/       # MCP server configurations and docs
```

## Contributing

PRs welcome. Keep each tool self-contained and documented at the top of its file.
