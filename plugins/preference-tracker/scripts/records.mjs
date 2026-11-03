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
  },
  required: ["notes"],
  additionalProperties: false,
};

export function toRecords(extracted, prompts, existing, sessionId) {
  const promptsByUuid = new Map(prompts.map((prompt) => [prompt.uuid, prompt]));
  const existingIds = new Set(existing.map((record) => record.id));
  const records = [];
  const problems = [];
  for (const item of extracted) {
    const prompt = promptsByUuid.get(item.prompt_uuid);
    if (!prompt) {
      problems.push(`Dropped "${item.note}": unknown prompt_uuid ${item.prompt_uuid}`);
      continue;
    }
    let supersedes = item.supersedes;
    if (supersedes !== null && !existingIds.has(supersedes)) {
      problems.push(`Recorded "${item.note}" without supersedes: unknown id ${supersedes}`);
      supersedes = null;
    }
    records.push({
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
      source: {
        project: prompt.project,
        session_id: sessionId,
        prompt_uuid: prompt.uuid,
        timestamp: prompt.timestamp,
      },
    });
  }
  return { records, problems };
}

export function truncate(text, maxChars) {
  return text.length <= maxChars ? text : `${text.slice(0, maxChars)}\n[truncated]`;
}
