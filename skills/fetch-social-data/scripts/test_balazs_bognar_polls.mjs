import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  BALAZS_BOGNAR,
  auditBalazsDataset,
  buildExtractionQueue,
  exportBalazsPolls,
  verifyBalazsDatasetComplete,
} from "./balazs_bognar_polls.mjs";

const directory = fs.mkdtempSync(path.join(os.tmpdir(), "balazs-polls-test-"));
const sourcePath = path.join(directory, "source.json");
const outputPath = path.join(directory, "export.json");

const fixture = {
  posts: [{
    record_id: "poll-option-1",
    facebook_post_id: "99",
    permalink: "https://www.facebook.com/groups/257529845152517/posts/99",
    title: "Test poll",
    publication_year: 2025,
    author: { id: "100001332278141", name: "Balázs Bognár" },
    text_visible: "Test poll",
    poll: {
      selection_type: "multiple_choice",
      options: [{
        option_id: "1",
        label: "AAA",
        percentage: 100,
        vote_count: 2,
        available_voter_count: 2,
        voter_list_status: "complete",
        voters: [
          { name: "One", profile_url: "https://www.facebook.com/one?__tn__=x" },
          { name: "Two", profile_url: "https://www.facebook.com/profile.php?id=2&__cft__=x" },
        ],
      }],
    },
    engagement: { comment_count: 2 },
    comments: {
      status: "complete_displayed_count_match",
      loaded_count: 2,
      top_level_count: 1,
      items: [{
        id: "c1",
        parent_comment_id: null,
        author: { name: "One", url: "https://www.facebook.com/one" },
        text: "Top",
        replies: [{
          id: "r1",
          parent_comment_id: "c1",
          author: { name: "Two", url: "https://www.facebook.com/profile.php?id=2" },
          text: "Reply",
          replies: [],
        }],
      }],
    },
  }],
  completeness: {},
};

fs.writeFileSync(sourcePath, JSON.stringify(fixture), "utf8");

const audit = auditBalazsDataset(sourcePath);
assert.equal(audit.ok, true);
assert.equal(audit.complete, true);
assert.equal(audit.posts, 1);
assert.equal(audit.posts_with_voter_data, 1);
assert.equal(audit.posts_with_complete_voter_lists, 1);
assert.equal(audit.complete_options, 1);
assert.equal(audit.pending_options, 0);
assert.equal(audit.vote_records, 2);
assert.equal(audit.comments, 2);
assert.equal(verifyBalazsDatasetComplete(sourcePath).complete, true);

const queue = buildExtractionQueue(sourcePath);
assert.equal(queue.remaining_posts, 0);

const exported = exportBalazsPolls({ targetPath: sourcePath, outputPath });
assert.equal(exported.posts, 1);
const output = JSON.parse(fs.readFileSync(outputPath, "utf8"));
assert.equal(output.posts[0].poll.vote_records.length, 2);
assert.equal(output.posts[0].poll.vote_records[0].option_label, "AAA");
assert.equal(output.posts[0].comments.items[0].replies[0].id, "r1");

fixture.posts[0].author.name = "Not Balázs";
fs.writeFileSync(sourcePath, JSON.stringify(fixture), "utf8");
const rejected = auditBalazsDataset(sourcePath);
assert.equal(rejected.ok, false);
assert.match(rejected.errors[0], /author is not Balázs Bognár/);

fixture.posts[0].author.name = BALAZS_BOGNAR.name;
delete fixture.posts[0].poll.options[0].voter_list_status;
fs.writeFileSync(sourcePath, JSON.stringify(fixture), "utf8");
const incomplete = auditBalazsDataset(sourcePath);
assert.equal(incomplete.ok, true);
assert.equal(incomplete.complete, false);
assert.equal(incomplete.posts_with_complete_voter_lists, 0);
assert.equal(incomplete.pending_options, 1);
assert.equal(incomplete.pending_voter_lists[0].option_id, "1");
assert.throws(() => verifyBalazsDatasetComplete(sourcePath), /structurally valid but incomplete/);

fixture.posts[0].poll.options[0].voter_list_status = "complete";
const nonInvestment = structuredClone(fixture.posts[0]);
nonInvestment.record_id = "poll-option-2";
nonInvestment.facebook_post_id = "100";
nonInvestment.title = "Biztosítás szavazás 1/2";
nonInvestment.poll.options[0].option_id = "2";
delete nonInvestment.poll.options[0].voter_list_status;
fixture.posts.push(nonInvestment);
fs.writeFileSync(sourcePath, JSON.stringify(fixture), "utf8");

const allPolls = auditBalazsDataset(sourcePath);
assert.equal(allPolls.scope, "all_polls");
assert.equal(allPolls.complete, false);
assert.equal(allPolls.posts, 2);
const investments = auditBalazsDataset(sourcePath, { investmentOnly: true });
assert.equal(investments.scope, "investment_polls");
assert.equal(investments.complete, true);
assert.equal(investments.posts, 1);
assert.equal(verifyBalazsDatasetComplete(sourcePath, { investmentOnly: true }).complete, true);
assert.equal(buildExtractionQueue(sourcePath, { investmentOnly: true }).remaining_posts, 0);

console.log("balazs_bognar_polls tests passed");
