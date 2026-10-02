---
description: Explain a concept in ASD-STE100 Simplified Technical English, linked to my Concept Vocabulary (no fixed section structure)
argument-hint: "<topic> [--diagram mermaid|image] [--web static|interactive] [--video storyboard|full]"
---

EXPLAIN-SIMPLE COMMAND

/explain-simple <topic>
  [--diagram mermaid|image]
  [--web static|interactive]
  [--video storyboard|full]

Purpose:
Explain <topic> using ASD-STE100 Simplified Technical English.

Use only the following ASD-STE100 rules.

WRITING LIMITS

1. Procedural sentence:
   - Maximum 20 words.

2. Descriptive sentence:
   - Maximum 25 words.

3. Descriptive paragraph:
   - Maximum 6 sentences.
   - Write one topic in each paragraph.

4. Noun cluster:
   - Maximum 3 words.

5. Instructions in each sentence:
   - Maximum 1 instruction.
   - Simultaneous actions are an exception.

GENERAL WRITING RULES

6. Use the same word for the same thing every time.

7. Do not leave out words such as:
   - "the"
   - "a"
   - "an"
   - "this"

8. Use the active voice in procedures.

9. Use vertical lists for complex text.

VERB FORMS

Approved:
- Command / imperative
  Example: "Close the valve."

- Simple present
  Example: "The valve closes."

- Simple past
  Example: "The valve closed."

- Simple future
  Example: "The valve will close."

- Infinitive
  Example: "Turn the knob to close it."

- Past participle used as an adjective
  Example: "The closed valve."

Not approved:
- Progressive (-ing)
  Example: "The valve is closing."

- Perfect
  Example: "The valve has closed."

- Passive voice in procedures
  Example: "The valve must be closed."

Additional verb rules:
- Use the -ing form only inside a technical name, for example "landing gear".
- Descriptive text can use the passive voice when it is necessary.

SAFETY INSTRUCTIONS

10. Use:
    - WARNING for risk of injury.
    - CAUTION for risk of damage.

11. In a safety instruction:
    - First give a clear, simple command.
    - Then give the risk.

Example:
"WARNING: Do not touch the brake unit until it is cool. Hot parts can cause injury."

DICTIONARY / WORD USAGE

12. An approved word keeps only its listed meaning and part of speech.

13. Use these approved alternatives:

- CLOSE (verb)
  Meaning: to move together; to stop flow.
  Example: "CLOSE the valve."

- close (adjective) → NEAR
  Approved: "Put the tool NEAR the panel."
  Not approved: "Put the tool close to the panel."

- commence → START
  Approved: "START the pump."
  Not approved: "Commence pumping."

- ensure → MAKE SURE
  Approved: "MAKE SURE that the switch is off."
  Not approved: "Ensure the switch is off."

- prior to → BEFORE
  Approved: "BEFORE you start the engine."
  Not approved: "Prior to starting the engine."

- replenish → FILL
  Approved: "FILL the reservoir."
  Not approved: "Replenish the reservoir."

- utilize → USE
  Approved: "USE a torque wrench."
  Not approved: "Utilize a torque wrench."

- approximately → ABOUT
  Approved: "Wait for ABOUT 10 minutes."
  Not approved: "Wait approximately 10 minutes."

- TEST
  Meaning: to find if it operates correctly.
  Example: "TEST the circuit."

- in order to → TO
  Approved: "Remove the panel TO get access."
  Not approved: "Remove the panel in order to get access."

OUTPUT OPTIONS

--diagram mermaid
Create a Mermaid diagram as part of the explanation.

--diagram image
Create an explanatory image or diagram.

--web static
Create a static HTML explanation.

--web interactive
Create an interactive HTML explanation.

--video storyboard
Create a video storyboard.

--video full
Create the complete explainer video when the available tools permit it.

# Vocabulary Vault

**Before you explain:** scan `concept-vocab/INDEX.md` and surface related concepts already in it, so the new concept links to them.

**At the end of the answer:** give a table `Concept | Topic | Subtopic | Date Added` — Topic required, Subtopic optional, date as `YYYY-MM-DD`. One row per concept; a one-sentence gloss is fine in chat but is not stored. Then ask whether to save it to my Concept Vocabulary.

**Concept Vocabulary** — my git repo, the source of truth for saved concepts:

* Repo: https://github.com/prucsakos/concept-vocabulary (private)
* UTF-8 `README.md` documents the schema and the topic/subtopic map; read it for the full data model.
* Source of truth: the `concept-vocab/` file tree, one YAML file per concept.
* `concept-vocab/INDEX.md` is generated from the tree; never edit it by hand.
* Lookups: `grep -i "Finance & Investing" concept-vocab/INDEX.md` (one topic), `grep -i "Autoencoder" concept-vocab/INDEX.md` (one concept).

**When I say "save to my vocabulary":** create one YAML file per concept at `concept-vocab/<Topic>/<Subtopic>/<Concept>.yaml`, containing `concept: "<Exact Concept Name>"` and `date: YYYY-MM-DD` (today).

* Assign the closest **existing** Topic. Add a Subtopic folder only if a matching subtopic already exists; otherwise omit it.
* Reuse Topic/Subtopic names **verbatim** — never invent near-duplicates.
* Keep the exact concept name in `concept:`; sanitize only the filename if needed.

**If you cannot reach the repo this session** (no local clone and no GitHub access): say so, and output paste-ready YAML file specs instead.

# Input

$ARGUMENTS

Everything that is not a flag is the topic. Without a flag, do not create that output.
