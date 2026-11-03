# claude-code-tools

A collection of reusable [Claude Code](https://claude.com/claude-code) tools: slash commands, MCP server configs, and agent workflows. Some tools also ship a ChatGPT-compatible version under `chatgpt/`.

[Quickstart](#quickstart) · [Commands](#commands) · [Skills](#skills) · [Plugin](#plugin-preference-tracker) · [ChatGPT](#chatgpt) · [MCP](#mcp) · [Layout](#repository-layout)

## Quickstart

Install the `preference-tracker` plugin from this repository's marketplace (`prucsakos-tools`):

```bash
claude plugin marketplace add prucsakos/claude-code-tools
claude plugin install preference-tracker@prucsakos-tools
```

Install a command (here `/team`) for every project:

```bash
git clone https://github.com/prucsakos/claude-code-tools && cd claude-code-tools
cp commands/team.md ~/.claude/commands/
```

Install a Codex skill (here `explain`), from the same clone:

```bash
cp -R skills/explain ~/.codex/skills/
```

## Tools

| Tool | What it does |
|------|--------------|
| [`/team`](commands/team.md) | Command: run N parallel Haiku workers on a task |
| [`/explain`](commands/explain.md) | Command: explain a concept in Simplified English |
| [`/explain-simple`](commands/explain-simple.md) | Command: `/explain` without the fixed structure |
| [`/full-code-audit`](commands/full-code-audit.md) | Command: load a folder's source code into context |
| [`/my-code-simplify`](commands/my-code-simplify.md) | Command: simplify current changes, keep behavior |
| [`explain`](skills/explain/) | Codex skill: version of `/explain` |
| [`explain-simple`](skills/explain-simple/) | Codex skill: version of `/explain-simple` |
| [`my-iterative-optimization`](skills/my-iterative-optimization/) | Skill: improve a project with parallel experiments |
| [`preference-tracker`](plugins/preference-tracker/) | Plugin: record taste notes to a private repo |
| [`full-code-audit`](chatgpt/full-code-audit.md) | ChatGPT prompt: version of `/full-code-audit` |
| [BlenderMCP](https://github.com/ahujasid/blender-mcp) | MCP: connect an AI client to Blender |

## Commands

Clone this repository and copy a command file into your commands directory:

```bash
git clone https://github.com/prucsakos/claude-code-tools && cd claude-code-tools

# Available in every project (user-level)
cp commands/team.md ~/.claude/commands/

# Or per-project
cp commands/team.md your-project/.claude/commands/
```

Then use it inside Claude Code. Arguments come from each command's `argument-hint`:

| Command | Arguments | Example |
|---------|-----------|---------|
| `/team` | `[N] "task description"` | `/team 4 "Refactor the API layer and add tests"` |
| `/explain` | `<topic> [--diagram mermaid\|image] [--web static\|interactive] [--video storyboard\|full]` | `/explain "Kalman filter" --diagram mermaid` |
| `/explain-simple` | `<topic> [--diagram mermaid\|image] [--web static\|interactive] [--video storyboard\|full]` | `/explain-simple "Kalman filter"` |
| `/full-code-audit` | `path to the folder to load` | `/full-code-audit src/` |
| `/my-code-simplify` | `optional scope (files, folder, PR); defaults to the current changes` | `/my-code-simplify` |

`/team` without N lets Claude pick the team size, e.g. `/team "Audit the codebase for security issues"`.

### `/team`

Spin up a team of N parallel Haiku workers to tackle a task.

```bash
cp commands/team.md ~/.claude/commands/
```

### `/explain`

Explain a concept in ASD-STE100 Simplified Technical English via reusable mental models, linked to a personal Concept Vocabulary repo.

```bash
cp commands/explain.md ~/.claude/commands/
```

### `/explain-simple`

Same ASD-STE100 rules and Concept Vocabulary as `/explain`, without the fixed explanation structure.

```bash
cp commands/explain-simple.md ~/.claude/commands/
```

### `/full-code-audit`

Load a folder's production source code into context, verbatim and unanalyzed.

```bash
cp commands/full-code-audit.md ~/.claude/commands/
```

### `/my-code-simplify`

Aggressively simplify the current changes and prune their tests, preserving behavior.

```bash
cp commands/my-code-simplify.md ~/.claude/commands/
```

## Skills

### `explain` and `explain-simple` (Codex)

Codex versions of the `/explain` and `/explain-simple` commands. Copy a skill folder into your Codex skills directory:

```bash
cp -R skills/explain ~/.codex/skills/
cp -R skills/explain-simple ~/.codex/skills/
```

Then invoke it as `$explain` (or `$explain-simple`) in Codex.

### `my-iterative-optimization` (Claude Code)

Claude Code skill: work on the targets you pick inside pillars from four groups (Product: Performance, UX, UI, Features · Reach: Accessibility, SEO, i18n · Engineering: Quality, DX, OX, Security · Code health: Code hygiene, Dependency health, Documentation). Optimize targets (e.g. Performance: Speed or Memory) improve a measurable metric; build targets (UI: Redesign, New screens · Features) add new features or designs against fixed acceptance criteria. Uses one researcher per pillar that searches widely and sends both conservative and bold ideas, N parallel experimenters divided evenly over the pillars, and one integrator that migrates accepted changes to main in batches. Profiles `low`, `medium` and `high` set the spend; mode `auto` decides on its own, `review` asks you to approve each batch.

It is a Claude Code skill, so copy it into your Claude Code skills directory:

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

## Plugin: preference-tracker

Claude Code plugin: after each Claude turn, a background worker writes taste notes when you had to step in (a correction, a follow-up question, something unclear, or a request Claude could have handled itself) and pushes them to `preferences/preferences.jsonl` in a private repository.

This repository is also a Claude Code plugin marketplace (`prucsakos-tools`):

```bash
claude plugin marketplace add prucsakos/claude-code-tools
claude plugin install preference-tracker@prucsakos-tools
```

**Requires**

- `node` and `git` on your PATH
- push access to the preference repository
- in that repository, the `.gitattributes` line `preferences/preferences.jsonl merge=union`, so notes from several machines merge

**Options**

| Option | Default (when empty) | What it sets |
|---|---|---|
| `repo_url` | `https://github.com/prucsakos/claude-preferences.git` (my private repository) | Git URL of the repository that stores the notes. Set it to use your own. |
| `model` | `sonnet` | Model alias or name that extracts the notes from your messages. |

**When it writes a note**

A note is written when one of your messages shows one of these triggers:

- `correction`: you corrected, rejected or redirected what Claude did, or told it how you want things done.
- `clarification_question`: you asked a follow-up question about Claude's response or work, which shows information Claude could have given without being asked.
- `unclear_response`: you did not understand Claude's response.
- `avoidable_request`: you asked Claude to do something it could have done without asking.

**What a note looks like**

Each note is one line of JSON; it is shown formatted here. It records the trigger, the taste note (`note`), what Claude should do next time (`next_time`), a short summary of the situation, what Claude did and your words. `category` is one of `communication`, `code-style`, `architecture`, `testing`, `workflow`, `tooling`, `git`, `documentation` or `other`; `scope` is `global` or `project`; `basis` is `stated` when you said the preference in words, `inferred` when it was deduced from a question or reaction; `supersedes` is the `id` of an older note that this one replaces, or `null`.

```json
{
  "id": "pref_3f9a1c2b7d4e",
  "trigger": "avoidable_request",
  "note": "After a bug fix, the user wants Claude to run the existing tests before it reports, not ask whether to run them.",
  "next_time": "Run the project's test command after a fix and report the result.",
  "category": "testing",
  "scope": "global",
  "basis": "stated",
  "context": {
    "situation": "Claude fixed a date-parsing bug and asked whether to run the tests.",
    "claude_action": "Ended its turn with \"Shall I run the tests?\"",
    "user_quote": "yes, run them"
  },
  "supersedes": null,
  "source": {
    "project": "my-app",
    "session_id": "0b6c2f4e-8a1d-4c3b-9e57-2d8f1a6b3c90",
    "prompt_uuid": "5e2d9a7c-1f3b-4a8e-b6c4-7d0e2f9a1b35",
    "timestamp": "2026-10-14T09:12:45.318Z"
  }
}
```

**Privacy:** before a note is written, a pattern check (`plugins/preference-tracker/scripts/redact.mjs`) removes tokens, keys, passwords, email addresses and URLs from its text.

**Errors:** if a background run fails, the error is shown after the next Claude turn.

Example: after installing, work in Claude Code as usual. When you correct Claude, the next turn's background run appends a note to `preferences/preferences.jsonl` in the configured repository.

## ChatGPT

### `full-code-audit`

ChatGPT/custom-GPT version of the full-code-audit command. Files under `chatgpt/` are plain prompt text, not an installable format. Use one of:

- **Custom GPT:** paste the file's content into the GPT's *Instructions* field.
- **One-off chat:** paste the prompt, replace `{{TARGET}}` with what you're auditing (or drop that line and paste/upload the code right after the prompt).

## MCP

MCP server configs live in [`mcps/`](mcps/). See that folder's README for setup.

### BlenderMCP

Related project: [BlenderMCP](https://github.com/ahujasid/blender-mcp) connects MCP-compatible AI clients to Blender through an MCP server and Blender add-on. Install and example usage are in its README; setup notes for this repository are in [`mcps/`](mcps/).

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

## Repository layout

```
.claude-plugin/  # Plugin marketplace manifest
commands/        # Slash commands (markdown files, one per command)
mcps/            # MCP server configurations and docs
plugins/         # Claude Code plugins (one folder per plugin)
skills/          # Reusable skills, Codex unless noted (one self-contained folder per skill)
chatgpt/         # ChatGPT/custom-GPT prompt versions of select tools
```

## Contributing

PRs welcome. Keep each tool self-contained and documented at the top of its file.
