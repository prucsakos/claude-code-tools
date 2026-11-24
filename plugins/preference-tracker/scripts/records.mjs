// Turns the extractor output into database records. Separate from worker.mjs, which runs on import, so tests can load it.
import { randomBytes } from "node:crypto";
import { redact } from "./redact.mjs";

// Limits on what a note publishes, so a summary or a long message is not copied into it whole.
const MAX_SITUATION_CHARS = 1000;
const MAX_QUOTE_CHARS = 300;

const NOTE_PROPERTIES = {
  prompt_uuid: { type: "string" },
  trigger: {
    type: "string",
    enum: ["unclear_response", "clarification_question", "avoidable_request", "correction"],
  },
  note: { type: "string" },
  next_time: { type: "string" },
  category: {
    type: "string",
    enum: [
      "communication",
      "code-style",
      "architecture",
      "testing",
      "workflow",
      "tooling",
      "git",
      "documentation",
      "other",
    ],
  },
  scope: { type: "string", enum: ["global", "project"] },
  basis: { type: "string", enum: ["stated", "inferred"] },
  situation: { type: "string" },
  claude_action: { type: "string" },
  user_quote: { type: "string" },
  supersedes: { type: ["string", "null"] },
};

const REPEAT_PROPERTIES = {
  prompt_uuid: { type: "string" },
  note_id: { type: "string" },
};

export const OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    notes: {
      type: "array",
      items: {
        type: "object",
        properties: NOTE_PROPERTIES,
        required: Object.keys(NOTE_PROPERTIES),
        additionalProperties: false,
      },
    },
    repeats: {
      type: "array",
      items: {
        type: "object",
        properties: REPEAT_PROPERTIES,
        required: Object.keys(REPEAT_PROPERTIES),
        additionalProperties: false,
      },
    },
  },
  required: ["notes", "repeats"],
  additionalProperties: false,
};

// Records written since 0.5.0 carry this number. Records without it are older and may lack `basis` or `context.situation`.
const SCHEMA_VERSION = 2;

// The notes the extractor compares new messages against: `next_time` only, without notes that
// were replaced and without notes scoped to a project that no excerpt comes from. The full
// list with the long `note` text was most of the input of every run.
export function toExistingNotes(existing, excerptProjects) {
  const supersededIds = new Set(existing.map((record) => record.supersedes).filter(Boolean));
  return existing
    .filter(isNote)
    .filter((record) => !supersededIds.has(record.id))
    .filter((record) => record.scope === "global" || excerptProjects.includes(record.source.project))
    .map((record) => ({
      id: record.id,
      next_time: record.next_time,
      project: record.scope === "project" ? record.source.project : null,
    }));
}

export function toRecords({ notes, repeats }, prompts, existing, sessionId) {
  const promptsByUuid = new Map(prompts.map((prompt) => [prompt.uuid, prompt]));
  const noteIds = new Set(existing.filter(isNote).map((record) => record.id));
  const records = [];
  const problems = [];
  const sourceOf = (prompt) => ({
    project: prompt.project,
    session_id: sessionId,
    prompt_uuid: prompt.uuid,
    timestamp: prompt.timestamp,
  });
  for (const item of notes) {
    const prompt = promptsByUuid.get(item.prompt_uuid);
    if (!prompt) {
      problems.push(`Dropped "${item.note}": unknown prompt_uuid ${item.prompt_uuid}`);
      continue;
    }
    let supersedes = item.supersedes;
    if (supersedes !== null && !noteIds.has(supersedes)) {
      problems.push(`Recorded "${item.note}" without supersedes: unknown id ${supersedes}`);
      supersedes = null;
    }
    records.push({
      schema: SCHEMA_VERSION,
      id: `pref_${randomBytes(6).toString("hex")}`,
      trigger: item.trigger,
      note: redact(item.note),
      next_time: redact(item.next_time),
      category: item.category,
      scope: item.scope,
      basis: item.basis,
      context: {
        situation: truncate(redact(item.situation), MAX_SITUATION_CHARS),
        claude_action: redact(item.claude_action),
        user_quote: truncate(redact(item.user_quote), MAX_QUOTE_CHARS),
      },
      supersedes,
      source: sourceOf(prompt),
    });
  }
  for (const item of repeats) {
    const prompt = promptsByUuid.get(item.prompt_uuid);
    if (!prompt) {
      problems.push(`Dropped repeat of ${item.note_id}: unknown prompt_uuid ${item.prompt_uuid}`);
      continue;
    }
    if (!noteIds.has(item.note_id)) {
      problems.push(`Dropped repeat for prompt ${item.prompt_uuid}: unknown note id ${item.note_id}`);
      continue;
    }
    // `source` has the same shape as in a note, because every worker version reads
    // `source.prompt_uuid` of every line to find the prompts that are already processed.
    records.push({
      schema: SCHEMA_VERSION,
      id: `rep_${randomBytes(6).toString("hex")}`,
      repeats: item.note_id,
      source: sourceOf(prompt),
    });
  }
  return { records, problems };
}

// A repeat record has no note text of its own.
export function isNote(record) {
  return typeof record.note === "string";
}

export function truncate(text, maxChars) {
  return text.length <= maxChars ? text : `${text.slice(0, maxChars)}\n[truncated]`;
}
