---
description: Teach a concept via reusable mental models, linked to my Concept Vocabulary
argument-hint: "concept or topic to learn"
---

# Teaching me
When teaching me, optimize for reusable mental models, not just facts.

Explain in this order, tying each step back to the problem:
**Problem → Hungarian, English version → Mechanism → Worked example → Compact mode → Connections → Failure casesl → Transfer test → Vocabulary Vault**

**Problem** — max 3 sentences: what breaks, or what question is unanswerable, without this concept.
**Hungarian, English version** — one line, with IPA phonetic transcription for the English term (skip it when pronunciation is obvious from spelling). Include word composition (abstract meaning of the word's atomic components) only when the components genuinely carry the meaning; skip it for opaque names and acronyms.
**Mechanism** — the core section, and the only one allowed multiple paragraphs. Introduce each moving part inline, at the moment the explanation needs it — no separate parts list. Walk cause → effect.
**Worked example** — Three examples with differing contexts.
**Compact model** — Two methafors in differing settings.
**Connections** — Three topological connection: "This connects to [concept] because…" Prefer concepts already in my Concept Vocabulary.
**Failure cases** — max 2, one line each: where the concept breaks, misleads, or stops applying.
**Transfer test** — two challenging tests verifying my mental model. Task: Definition mapping and differentiating. — from my Concept Vocabulary if any are present. In your thinking phase work extensively to make it challenging and true.
**Vocabulary Vault** — a table mirroring my Concept Vocabulary: `Concept | Topic | Subtopic | Date Added`, one line each (a one-sentence gloss is fine in chat but isn't stored). Then ask whether to save it to my Concept Vocabulary (below).
* Define every necessary term on first use. No unexplained jargon.
* Respect every length budget above. When in doubt, compress — depth belongs in Mechanism and Transfer test, not in more prose elsewhere.

# Concept Vocabulary — my git repo source of truth for learned concepts

The Vocabulary Vault is the in-chat draft; **this repository is where saved concepts live.**

* Repo: https://github.com/prucsakos/concept-vocabulary (private)
* UTF-8 `README.md` documents the schema and the topic/subtopic map.
* Source of truth: `concept-vocab/` file tree — one YAML file per concept.
* Read index: `concept-vocab/INDEX.md`; it is generated from the tree and must not be hand-edited.
* Chat schema: **Concept** · **Topic** (required) · **Subtopic** (optional) · **Date Added** (`YYYY-MM-DD`)
* Saved file schema: `concept: "<Exact Concept Name>"` and `date: YYYY-MM-DD`.

**When I'm learning something new (read first):** scan `concept-vocab/INDEX.md`, then surface related concepts already in it so we link the new one to them.

* All concepts in a topic: `grep -i "Finance & Investing" concept-vocab/INDEX.md`
* Look up one concept: `grep -i "Autoencoder" concept-vocab/INDEX.md`
* For the full schema and data model, read `README.md`.

**When I say "save to my vocabulary":** create one YAML file per concept under `concept-vocab/<Topic>/<Subtopic>/<Concept>.yaml`.

* Omit the Subtopic folder if the concept has no matching existing subtopic.
* Assign the closest **existing** Topic. Add a Subtopic only if a matching one already exists.
* Reuse Topic/Subtopic names **verbatim** — never invent near-duplicates.
* Preserve the exact concept name in the YAML `concept:` field; sanitize only the filename if needed.
* Date Added = today.

**If you cannot reach the repo this session** (no local clone and no GitHub access): say so, and output paste-ready YAML file specs instead.

## Concept to teach

$ARGUMENTS
