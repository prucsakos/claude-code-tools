# claude-code-tools

A collection of reusable [Claude Code](https://claude.com/claude-code) tools: slash commands, MCP server configs, and agent workflows. Some tools also ship a ChatGPT-compatible version under `chatgpt/`.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Command | [`/team`](commands/team.md) | Spin up a team of N parallel Sonnet workers to tackle a task |
| Command | [`/teach`](commands/teach.md) | Teach a concept via reusable mental models, linked to a personal Concept Vocabulary repo |
| Command | [`/full-code-audit`](commands/full-code-audit.md) | Load a folder's production source code into context, verbatim and unanalyzed |
| Skill | [`fetch-social-data`](skills/fetch-social-data/) | Retrieve structured Facebook posts, feeds, groups, polls, and comments without side effects |
| ChatGPT Prompt | [`full-code-audit`](chatgpt/full-code-audit.md) | ChatGPT/custom-GPT version of the full-code-audit command |
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
/full-code-audit src/
```

### Skills

Copy a skill folder into your Codex skills directory:

```bash
cp -R skills/fetch-social-data ~/.codex/skills/
```

Then invoke it as `$fetch-social-data` in Codex.

### ChatGPT

Files under `chatgpt/` are plain prompt text, not an installable format. Use one of:

- **Custom GPT:** paste the file's content into the GPT's *Instructions* field.
- **One-off chat:** paste the prompt, replace `{{TARGET}}` with what you're auditing (or drop that line and paste/upload the code right after the prompt).

### MCP servers

MCP server configs live in [`mcps/`](mcps/). See that folder's README for setup.

Related project: [BlenderMCP](https://github.com/ahujasid/blender-mcp) connects MCP-compatible AI clients to Blender through an MCP server and Blender add-on.

## Repository layout

```
commands/   # Slash commands (markdown files, one per command)
mcps/       # MCP server configurations and docs
skills/     # Reusable Codex skills (one self-contained folder per skill)
chatgpt/    # ChatGPT/custom-GPT prompt versions of select tools
```

## Contributing

PRs welcome. Keep each tool self-contained and documented at the top of its file.
