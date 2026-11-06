# Fork provenance

**This directory is the ChatGPT fork, not the original Claude Code skill.** It is maintained separately from the source in the same repository.

- Original author: prucsakos (Ákos Prucs).
- Repository: [prucsakos/claude-code-tools](https://github.com/prucsakos/claude-code-tools).
- Original directory: [`skills/my-iterative-optimization/`](https://github.com/prucsakos/claude-code-tools/tree/main/skills/my-iterative-optimization).
- Source revision used for this port: [`52b89bd27e0864fdf725dbbf44c0743a9510275e`](https://github.com/prucsakos/claude-code-tools/tree/52b89bd27e0864fdf725dbbf44c0743a9510275e/skills/my-iterative-optimization).
- Port date: 2026-11-06.
- Variant: ChatGPT / OpenAI skill, with capability-based execution and optional Codex use.

The original pillar/target taxonomy, optimize/build distinction, profiles, research/experiment/integration roles, baseline comparisons, anti-gaming rules and regression checks are retained. The original files are unchanged by this port.

Changes in this fork:

- Replace Claude-only tool names, Opus selection, background timers and notification assumptions with the host's actual execution, delegation, waiting and cancellation capabilities.
- Keep the original requested profiles (5/10/15 experimenters), while bounding real concurrency by host limits. Support sequential execution when worker delegation is absent. A chat without executable repository access receives a plan/patch with unverified checks identified.
- Replace the Bash/GNU measurement helper with a standard-library Python runner for Windows and POSIX, with bounded lock acquisition, OS advisory locks, finite-number checks, visible diagnostics and command-tree termination on timeout.
- Use a compact setup form, reuse existing explicit authorization, and make publishing opt-in unless the request already authorizes it. Keep the review mode's batch gate.
- Store detailed workflow and role templates under `references/`; include OpenAI UI metadata. Keep fork identification in this file, the skill entrypoint and the repository README.
- Make stop/host/budget boundaries explicit, scope cleanup to recorded run-owned artifacts, and verify the recovered baseline after a revert. Do not promise unattended continuation without host support.

## Using this fork

Keep this entire directory together: `SKILL.md` depends on its references and Python script. In a ChatGPT surface that supports skills, create/import the skill with the skill editor or `@skill-creator`, providing this directory's files. Consult the current [OpenAI skill instructions](https://learn.chatgpt.com/docs/build-skills) for the installation options available to your account. Invoke the installed skill with `@my-iterative-optimization` in ChatGPT; Codex uses `$my-iterative-optimization`.

For a chat without native skill installation, attach the entrypoint and support files and ask it to follow the workflow. This supplies instructions only; execution and delegation still depend on the chat's tools. Pasting the entrypoint alone into a custom GPT does not supply its referenced files or command tools.

Examples after installation:

```text
@my-iterative-optimization "Make scripts/build_report.py faster without changing its output"
@my-iterative-optimization low review "Improve code hygiene"
@my-iterative-optimization "Make it faster and add CSV export of reports"
```

No license grant is added by this fork; consult the upstream repository's applicable terms.
