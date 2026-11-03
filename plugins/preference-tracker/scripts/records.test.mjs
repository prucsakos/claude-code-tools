import assert from "node:assert/strict";
import { test } from "node:test";
import { OUTPUT_SCHEMA, toRecords } from "./records.mjs";

const prompt = { uuid: "p-1", project: "demo-app", timestamp: "2026-01-01T00:00:00.000Z" };
const item = {
  prompt_uuid: "p-1",
  trigger: "correction",
  note: "The user wants tests run before a commit.",
  next_time: "Run the tests before committing.",
  category: "testing",
  scope: "global",
  basis: "stated",
  situation: "The user was fixing a parser bug.",
  claude_action: "Claude committed without running the tests.",
  user_quote: "always run tests first",
  supersedes: null,
};

test("toRecords copies basis and keeps every 0.2.0 field", () => {
  const { records, problems } = toRecords([item], [prompt], [], "s-1");
  assert.deepEqual(problems, []);
  const [record] = records;
  assert.equal(record.basis, "stated");
  assert.match(record.id, /^pref_[0-9a-f]{12}$/);
  for (const field of ["trigger", "note", "next_time", "category", "scope"]) assert.equal(record[field], item[field]);
  assert.deepEqual(record.context, {
    situation: item.situation,
    claude_action: item.claude_action,
    user_quote: item.user_quote,
  });
  assert.equal(record.supersedes, null);
  assert.deepEqual(record.source, {
    project: "demo-app",
    session_id: "s-1",
    prompt_uuid: "p-1",
    timestamp: prompt.timestamp,
  });
});

test("OUTPUT_SCHEMA requires basis as stated or inferred", () => {
  const noteSchema = OUTPUT_SCHEMA.properties.notes.items;
  assert.ok(noteSchema.required.includes("basis"));
  assert.deepEqual(noteSchema.properties.basis.enum, ["stated", "inferred"]);
});

test("toRecords drops an item with an unknown prompt_uuid and reports it", () => {
  const { records, problems } = toRecords([{ ...item, prompt_uuid: "missing" }], [prompt], [], "s-1");
  assert.deepEqual(records, []);
  assert.equal(problems.length, 1);
  assert.match(problems[0], /unknown prompt_uuid missing/);
});
