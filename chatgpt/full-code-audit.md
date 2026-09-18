# Full-Code Audit (ChatGPT)

ChatGPT-compatible version of the `/full-code-audit` Claude Code command (see `commands/full-code-audit.md`). Use it as the **Instructions** field of a custom GPT, or paste it into a chat right before (or after uploading) the code you want audited.

Replace `{{TARGET}}` with a description of the folder/repo/module being audited, or delete that line if you're pasting the code directly below the prompt.

---

Audit all production code in: `{{TARGET}}`

## Instructions

1. Work only from the source code provided in this conversation (pasted text or uploaded files). Do not guess about code you have not been shown.
2. Exclude:
   - tests/specs
   - comments
   - generated/vendor/build files
   - documentation
3. Preserve file paths and code structure.
4. Do not modify the code.

Analyze the codebase globally, comparing implementations across files.

Find:
- duplicated or redundant implementations
- inconsistent patterns or conventions
- unnecessary complexity
- poor abstractions
- architectural inconsistencies
- dependency/layering problems
- obsolete or competing approaches
- opportunities to consolidate or simplify

Infer the project's dominant conventions from the code itself rather than imposing arbitrary style preferences.

For every finding provide:
- files/locations
- what is inconsistent or suboptimal
- evidence/comparison
- recommended canonical approach
- confidence

Prioritize high-impact findings and avoid cosmetic issues.

If the code does not fit in one message, ask for it module by module. After each module, build a compact architectural index (file → responsibility → key conventions) instead of holding the whole codebase in context, then do a final cross-module pass using that index once everything has been provided.
