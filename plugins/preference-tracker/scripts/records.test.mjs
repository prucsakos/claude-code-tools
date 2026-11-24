import assert from "node:assert/strict";
import { test } from "node:test";
import { OUTPUT_SCHEMA, toExistingNotes, toRecords } from "./records.mjs";

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
  const { records, problems } = toRecords({ notes: [item], repeats: [] }, [prompt], [], "s-1");
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
  const { records, problems } = toRecords({ notes: [{ ...item, prompt_uuid: "missing" }], repeats: [] }, [prompt], [], "s-1");
  assert.deepEqual(records, []);
  assert.equal(problems.length, 1);
  assert.match(problems[0], /unknown prompt_uuid missing/);
});

const existingNote = {
  id: "pref_aaaaaaaaaaaa",
  note: "The user wants terms defined.",
  next_time: "Define each term at first use.",
  scope: "global",
  supersedes: null,
  source: { project: "demo-app", prompt_uuid: "p-0" },
};

test("toRecords writes a repeat as a short record that points at the existing note", () => {
  const repeats = [
    { prompt_uuid: "p-1", note_id: existingNote.id },
    { prompt_uuid: "p-1", note_id: "pref_unknown" },
  ];
  const { records, problems } = toRecords({ notes: [], repeats }, [prompt], [existingNote], "s-1");
  assert.equal(records.length, 1);
  assert.match(records[0].id, /^rep_[0-9a-f]{12}$/);
  assert.equal(records[0].repeats, existingNote.id);
  assert.equal(records[0].source.prompt_uuid, "p-1");
  assert.equal(records[0].note, undefined);
  assert.match(problems[0], /unknown note id pref_unknown/);
});

test("toExistingNotes leaves out repeats, replaced notes and notes of other projects", () => {
  const existing = [
    existingNote,
    { ...existingNote, id: "pref_bbbbbbbbbbbb", supersedes: "pref_cccccccccccc" },
    { ...existingNote, id: "pref_cccccccccccc" },
    { ...existingNote, id: "pref_dddddddddddd", scope: "project" },
    { ...existingNote, id: "pref_eeeeeeeeeeee", scope: "project", source: { project: "other-app" } },
    { id: "rep_ffffffffffff", repeats: existingNote.id, source: { project: "demo-app", prompt_uuid: "p-9" } },
  ];
  assert.deepEqual(toExistingNotes(existing, ["demo-app"]), [
    { id: "pref_aaaaaaaaaaaa", next_time: existingNote.next_time, project: null },
    { id: "pref_bbbbbbbbbbbb", next_time: existingNote.next_time, project: null },
    { id: "pref_dddddddddddd", next_time: existingNote.next_time, project: "demo-app" },
  ]);
});
