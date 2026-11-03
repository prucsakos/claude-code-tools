# claude-code-tools

A collection of reusable [Claude Code](https://claude.com/claude-code) tools: slash commands, MCP server configs, and agent workflows. Some tools also ship a ChatGPT-compatible version under `chatgpt/`.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Command | [`/team`](commands/team.md) | Spin up a team of N parallel Haiku workers to tackle a task |
| Command | [`/explain`](commands/explain.md) | Explain a concept in ASD-STE100 Simplified Technical English via reusable mental models, linked to a personal Concept Vocabulary repo |
| Command | [`/explain-simple`](commands/explain-simple.md) | Same ASD-STE100 rules and Concept Vocabulary as `/explain`, without the fixed explanation structure |
| Command | [`/full-code-audit`](commands/full-code-audit.md) | Load a folder's production source code into context, verbatim and unanalyzed |
| Command | [`/my-code-simplify`](commands/my-code-simplify.md) | Aggressively simplify the current changes and prune their tests, preserving behavior |
| Skill | [`fetch-social-data`](skills/fetch-social-data/) | Retrieve structured Facebook posts, feeds, groups, polls, and comments without side effects |
| Skill | [`explain`](skills/explain/) | Codex version of the `/explain` command |
| Skill | [`explain-simple`](skills/explain-simple/) | Codex version of the `/explain-simple` command |
| Skill | [`my-iterative-optimization`](skills/my-iterative-optimization/) | Claude Code skill: work on the targets you pick inside pillars from four groups (Product: Performance, UX, UI, Features · Reach: Accessibility, SEO, i18n · Engineering: Quality, DX, OX, Security · Code health: Code hygiene, Dependency health, Documentation). Optimize targets (e.g. Performance: Speed or Memory) improve a measurable metric; build targets (UI: Redesign, New screens · Features) add new features or designs against fixed acceptance criteria. Uses one researcher per pillar that searches widely and sends both conservative and bold ideas, N parallel experimenters divided evenly over the pillars, and one integrator that migrates accepted changes to main in batches. Profiles `low`, `medium` and `high` set the spend; mode `auto` decides on its own, `review` asks you to approve each batch |
| Plugin | [`preference-tracker`](plugins/preference-tracker/) | Claude Code plugin: after each Claude turn, a background worker writes taste notes when you had to step in (a correction, a follow-up question, something unclear, or a request Claude could have handled itself) and pushes them to [`preferences/preferences.jsonl`](preferences/preferences.jsonl) |
| ChatGPT Prompt | [`full-code-audit`](chatgpt/full-code-audit.md) | ChatGPT/custom-GPT version of the full-code-audit command |
| MCP | [BlenderMCP](https://github.com/ahujasid/blender-mcp) | Connect an MCP-compatible AI client to Blender for scene creation and manipulation |

## Plugins I use

Claude Code plugins enabled in my user settings (`name@marketplace`).

| Plugin | Marketplace |
|--------|-------------|
| `you-should-know` (`cc-plugin-you-should-know`) | `builtin` |
| `code-review` | `anthropics/claude-plugins-official` |
| `feature-dev` | `anthropics/claude-plugins-official` |
| `security-guidance` | `anthropics/claude-plugins-official` |
| `playwright` | `anthropics/claude-plugins-official` |
| `linear` | `anthropics/claude-plugins-official` |
| `github` | `anthropics/claude-plugins-official` |

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
/explain "Kalman filter" --diagram mermaid
/explain-simple "Kalman filter"
/full-code-audit src/
/my-code-simplify
```

### Skills

Copy a skill folder into your Codex skills directory:

```bash
cp -R skills/explain ~/.codex/skills/
```

Then invoke it as `$explain` in Codex.

`my-iterative-optimization` is a Claude Code skill. Copy it into your Claude Code skills directory instead:

```bash
cp -R skills/my-iterative-optimization ~/.claude/skills/
```

Then use it inside Claude Code:

```
/my-iterative-optimization "Make scripts/build_report.py faster without changing its output"
/my-iterative-optimization "Improve this project"   # offers the pillars, then their targets, as a multiple choice
/my-iterative-optimization "Improve DX and Quality"
/my-iterative-optimization high auto "Make the build faster"   # profile and mode skip their form rows
/my-iterative-optimization low review "Improve Code hygiene"
/my-iterative-optimization review "Make it faster and add a CSV export of reports"   # an optimize and a build target
```

### Plugins

This repository is also a Claude Code plugin marketplace (`prucsakos-tools`):

```bash
claude plugin marketplace add prucsakos/claude-code-tools
claude plugin install preference-tracker@prucsakos-tools
```

`preference-tracker` needs `node` and `git` on your PATH, plus push access to the preference repository. Each note records the trigger, a short summary of the situation, what Claude did, your words, the taste note and what Claude should do next time. By default the notes go to this repository, which is public. The extractor is told to replace secrets, other people's names, company names and internal URLs with placeholders. A pattern check then removes tokens, keys, passwords, email addresses and URLs from every note before it is written. Names and other free-text details depend on the model alone, and each note and commit message names the project folder unchanged. Set the `repo_url` option to use another repository, and the `model` option to change the extraction model (default `sonnet`). If a background run fails, the error is shown after the next Claude turn.

### ChatGPT

Files under `chatgpt/` are plain prompt text, not an installable format. Use one of:

- **Custom GPT:** paste the file's content into the GPT's *Instructions* field.
- **One-off chat:** paste the prompt, replace `{{TARGET}}` with what you're auditing (or drop that line and paste/upload the code right after the prompt).

### MCP servers

MCP server configs live in [`mcps/`](mcps/). See that folder's README for setup.

Related project: [BlenderMCP](https://github.com/ahujasid/blender-mcp) connects MCP-compatible AI clients to Blender through an MCP server and Blender add-on.

## Repository layout

```
.claude-plugin/  # Plugin marketplace manifest
commands/        # Slash commands (markdown files, one per command)
mcps/            # MCP server configurations and docs
plugins/         # Claude Code plugins (one folder per plugin)
preferences/     # Taste notes written by preference-tracker
skills/          # Reusable skills, Codex unless noted (one self-contained folder per skill)
chatgpt/         # ChatGPT/custom-GPT prompt versions of select tools
```

## Contributing

PRs welcome. Keep each tool self-contained and documented at the top of its file.
