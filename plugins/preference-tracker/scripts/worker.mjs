// Background worker started by on-stop.mjs. It finds the human prompts of one session
// that were not processed yet, has a headless Claude write taste notes for the prompts
// that a better-informed Claude would have made unnecessary, appends the notes to the
// JSONL database in a plugin-owned clone of the repository, and pushes. Failures go to
// last-error.txt, which the next Stop hook shows.
import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import {
  appendFileSync,
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { redact } from "./redact.mjs";

const DEFAULT_REPO_URL = "https://github.com/prucsakos/claude-preferences.git";
const DEFAULT_MODEL = "sonnet";
// Must match the path that .gitattributes marks merge=union, so appends from two machines merge cleanly.
const DATABASE_PATH = "preferences/preferences.jsonl";
const PROMPT_FILE = fileURLToPath(new URL("./extractor-prompt.md", import.meta.url));

const MAX_PROMPTS_PER_RUN = 20;
const MAX_USER_MESSAGE_CHARS = 4000;
const MAX_CLAUDE_TEXT_CHARS = 4000;
const MAX_TOOL_CALLS = 10;
const MAX_TOOL_CALL_CHARS = 200;
// Context from before the first excerpt, so a message that depends on the earlier task can be read correctly.
const MAX_EARLIER_MESSAGES = 10;
const MAX_EARLIER_MESSAGE_CHARS = 500;
const MAX_SUMMARY_CHARS = 6000;
// Limits on what a note publishes, so a summary or a long message is not copied into it whole.
const MAX_SITUATION_CHARS = 1000;
const MAX_QUOTE_CHARS = 300;

const GIT_TIMEOUT_MS = 2 * 60 * 1000;
const EXTRACTOR_TIMEOUT_MS = 5 * 60 * 1000;
// Longer than the worst-case run, so only a killed worker leaves a lock this old.
const LOCK_STALE_MS = 15 * 60 * 1000;

const OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    notes: {
      type: "array",
      items: {
        type: "object",
        properties: {
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
          situation: { type: "string" },
          claude_action: { type: "string" },
          user_quote: { type: "string" },
          supersedes: { type: ["string", "null"] },
        },
        required: [
          "prompt_uuid",
          "trigger",
          "note",
          "next_time",
          "category",
          "scope",
          "situation",
          "claude_action",
          "user_quote",
          "supersedes",
        ],
        additionalProperties: false,
      },
    },
  },
  required: ["notes"],
  additionalProperties: false,
};

const dataDir = process.env.CLAUDE_PLUGIN_DATA;
const [sessionId, transcriptPath] = process.argv.slice(2);

try {
  mkdirSync(dataDir, { recursive: true });
  const lockFile = join(dataDir, "worker.lock");
  // When another worker holds the lock, exit: the next Stop picks up the prompts this run skipped.
  if (acquireLock(lockFile)) {
    try {
      run();
    } finally {
      rmSync(lockFile, { force: true });
    }
  }
} catch (error) {
  appendFileSync(join(dataDir, "last-error.txt"), `${new Date().toISOString()} ${error.message}\n`);
  process.exitCode = 1;
}

function run() {
  const config = {
    repoUrl: process.env.CLAUDE_PLUGIN_OPTION_REPO_URL || DEFAULT_REPO_URL,
    model: process.env.CLAUDE_PLUGIN_OPTION_MODEL || DEFAULT_MODEL,
  };
  const ledgerFile = join(dataDir, "processed", `${sessionId}.json`);
  const ledger = readLedger(ledgerFile);
  const allPrompts = readHumanPrompts(transcriptPath);
  if (!allPrompts.some((prompt) => !ledger.includes(prompt.uuid))) return;

  const repoDir = join(dataDir, "repo");
  syncRepo(repoDir, config.repoUrl);
  const databaseFile = join(repoDir, DATABASE_PATH);
  const existing = readJsonl(databaseFile);
  // The database also counts as processed, in case a run pushed but died before writing the ledger.
  const processed = new Set([...ledger, ...existing.map((record) => record.source.prompt_uuid)]);
  const prompts = allPrompts.filter((prompt) => !processed.has(prompt.uuid)).slice(0, MAX_PROMPTS_PER_RUN);
  if (prompts.length === 0) return;

  const firstIndex = allPrompts.indexOf(prompts[0]);
  const conversationBefore = {
    compact_summary: prompts[0].summaryBefore,
    earlier_user_messages: allPrompts
      .slice(Math.max(0, firstIndex - MAX_EARLIER_MESSAGES), firstIndex)
      .map((prompt) => truncate(prompt.userMessage, MAX_EARLIER_MESSAGE_CHARS)),
  };
  const extracted = extractPreferences(prompts, conversationBefore, existing, config.model);
  const { records, problems } = toRecords(extracted, prompts, existing);
  if (records.length > 0) {
    appendRecords(databaseFile, records);
    commitAndPush(repoDir, records);
  }
  writeLedger(ledgerFile, [...ledger, ...prompts.map((prompt) => prompt.uuid)]);
  appendFileSync(
    join(dataDir, "worker.log"),
    `${new Date().toISOString()} session=${sessionId} prompts=${prompts.length} recorded=${records.length}\n`,
  );
  if (problems.length > 0) throw new Error(`Extractor output problems:\n${problems.join("\n")}`);
}

function acquireLock(lockFile) {
  try {
    closeSync(openSync(lockFile, "wx"));
    return true;
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  if (Date.now() - statSync(lockFile).mtimeMs < LOCK_STALE_MS) return false;
  rmSync(lockFile, { force: true });
  return acquireLock(lockFile);
}

// Returns the prompts the user typed, each with what Claude said and did since the previous
// prompt, and the latest summary Claude Code wrote when it compacted the conversation before it.
function readHumanPrompts(file) {
  const prompts = [];
  let claudeTexts = [];
  let toolCalls = [];
  let summary = null;
  for (const entry of readTranscript(file)) {
    if (entry.isSidechain) continue;
    if (entry.type === "user" && entry.isCompactSummary) {
      summary = truncate(stripInjectedText(entry.message.content), MAX_SUMMARY_CHARS);
    } else if (entry.type === "assistant") {
      for (const block of entry.message.content) {
        if (block.type === "text") claudeTexts.push(block.text);
        if (block.type === "tool_use") {
          toolCalls.push(`${block.name} ${JSON.stringify(block.input)}`.slice(0, MAX_TOOL_CALL_CHARS));
        }
      }
    } else if (isHumanPrompt(entry) || isHumanMidTurnMessage(entry)) {
      const userMessage = stripInjectedText(entry.type === "user" ? entry.message.content : entry.attachment.prompt);
      if (userMessage) {
        prompts.push({
          uuid: entry.uuid,
          timestamp: entry.timestamp,
          project: basename(entry.cwd),
          userMessage: truncate(userMessage, MAX_USER_MESSAGE_CHARS),
          claudeBefore: {
            text: claudeTexts.join("\n\n").slice(-MAX_CLAUDE_TEXT_CHARS),
            toolCalls: toolCalls.slice(-MAX_TOOL_CALLS),
          },
          summaryBefore: summary,
        });
      }
      claudeTexts = [];
      toolCalls = [];
    }
  }
  return prompts;
}

// turnOrigin "human" marks prompts that start a turn: typed, queued and desktop-app prompts.
// Tool results, task notifications, peer messages and `claude -p` prompts carry other values or none.
function isHumanPrompt(entry) {
  return entry.type === "user" && entry.turnOrigin === "human" && !entry.isMeta && !entry.isCompactSummary;
}

// A message the user sends while Claude is working is stored only as a queued_command
// attachment. These are often corrections. Task notifications and peer messages use the
// same attachment type with another origin kind.
function isHumanMidTurnMessage(entry) {
  return (
    entry.type === "attachment" &&
    entry.attachment.type === "queued_command" &&
    entry.attachment.origin?.kind === "human"
  );
}

// Removes text that Claude Code injects into user messages, so it is not taken for the user's words.
function stripInjectedText(content) {
  const text =
    typeof content === "string"
      ? content
      : content
          .filter((block) => block.type === "text")
          .map((block) => block.text)
          .join("\n");
  return text
    .replace(/<system-reminder>[\s\S]*?<\/system-reminder>/g, "")
    .replace(/<local-command-(\w+)>[\s\S]*?<\/local-command-\1>/g, "")
    .trim();
}

function readTranscript(file) {
  const lines = readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean);
  return lines.flatMap((line, index) => {
    try {
      return [JSON.parse(line)];
    } catch (error) {
      // Claude Code may still be writing the last line.
      if (index === lines.length - 1) return [];
      throw new Error(`${file}:${index + 1} is not valid JSON: ${error.message}`);
    }
  });
}

function extractPreferences(prompts, conversationBefore, existing, model) {
  const input = {
    existing_notes: existing.map((record) => ({
      id: record.id,
      note: record.note,
      next_time: record.next_time,
      scope: record.scope,
      project: record.source.project,
    })),
    conversation_before: conversationBefore,
    excerpts: prompts.map((prompt) => ({
      prompt_uuid: prompt.uuid,
      project: prompt.project,
      claude_before: prompt.claudeBefore,
      user_message: prompt.userMessage,
    })),
  };
  const result = spawnSync(
    "claude",
    [
      "-p",
      "--safe-mode",
      "--model",
      model,
      "--tools",
      "",
      "--no-session-persistence",
      "--system-prompt-file",
      PROMPT_FILE,
      "--output-format",
      "json",
      "--json-schema",
      JSON.stringify(OUTPUT_SCHEMA),
    ],
    {
      cwd: dataDir,
      input: JSON.stringify(input),
      encoding: "utf8",
      timeout: EXTRACTOR_TIMEOUT_MS,
      maxBuffer: 16 * 1024 * 1024,
      windowsHide: true,
      env: { ...process.env, PREFERENCE_TRACKER_CHILD: "1" },
    },
  );
  checkExit(result, "claude -p");
  const response = JSON.parse(result.stdout);
  if (response.is_error || !response.structured_output) {
    throw new Error(`Extractor returned no structured output: ${result.stdout.slice(0, 500)}`);
  }
  return response.structured_output.notes;
}

function toRecords(extracted, prompts, existing) {
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

function syncRepo(repoDir, repoUrl) {
  if (!existsSync(join(repoDir, ".git"))) {
    git(dataDir, ["clone", repoUrl, repoDir]);
    return;
  }
  const originUrl = git(repoDir, ["remote", "get-url", "origin"]);
  if (originUrl !== repoUrl) {
    throw new Error(`${repoDir} is a clone of ${originUrl}, not ${repoUrl}. Delete it to clone the new repository.`);
  }
  pullRebase(repoDir);
  // A previous run may have committed but failed to push.
  if (git(repoDir, ["rev-list", "--count", "@{upstream}..HEAD"]) !== "0") git(repoDir, ["push"]);
}

function commitAndPush(repoDir, records) {
  const projects = [...new Set(records.map((record) => record.source.project))].join(", ");
  const noun = records.length === 1 ? "taste note" : "taste notes";
  git(repoDir, ["add", DATABASE_PATH]);
  git(repoDir, ["commit", "-m", `Record ${records.length} ${noun} from ${projects}`]);
  try {
    git(repoDir, ["push"]);
  } catch {
    // The remote moved since the pull at the start of the run: rebase onto it and retry once.
    pullRebase(repoDir);
    git(repoDir, ["push"]);
  }
}

function pullRebase(repoDir) {
  try {
    git(repoDir, ["pull", "--rebase"]);
  } catch (error) {
    const rebaseInProgress =
      existsSync(join(repoDir, ".git", "rebase-merge")) || existsSync(join(repoDir, ".git", "rebase-apply"));
    if (rebaseInProgress) git(repoDir, ["rebase", "--abort"]);
    throw error;
  }
}

function git(cwd, args) {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
    windowsHide: true,
    // Fail instead of waiting for a credential prompt that nobody can see.
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0", GCM_INTERACTIVE: "never" },
  });
  checkExit(result, `git ${args.join(" ")}`);
  return result.stdout.trim();
}

function checkExit(result, label) {
  if (result.error) throw new Error(`${label}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${label} exited with ${result.status}: ${result.stderr.trim()}`);
}

function readJsonl(file) {
  if (!existsSync(file)) return [];
  return readFileSync(file, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`${file}:${index + 1} is not valid JSON: ${error.message}`);
      }
    });
}

function appendRecords(file, records) {
  mkdirSync(dirname(file), { recursive: true });
  const current = existsSync(file) ? readFileSync(file, "utf8") : "";
  // Every record must sit on its own line, or a union merge can join two records.
  const separator = current === "" || current.endsWith("\n") ? "" : "\n";
  appendFileSync(file, separator + records.map((record) => `${JSON.stringify(record)}\n`).join(""));
}

function readLedger(file) {
  return existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : [];
}

function writeLedger(file, uuids) {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(uuids));
}

function truncate(text, maxChars) {
  return text.length <= maxChars ? text : `${text.slice(0, maxChars)}\n[truncated]`;
}
