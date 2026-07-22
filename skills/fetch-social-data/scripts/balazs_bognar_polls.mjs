import fs from "node:fs";
import { pathToFileURL } from "node:url";

import {
  markVisibleVoterSweepComplete,
  mergeVisibleComments,
  mergeVisibleVoterDialog,
  refreshCompleteness,
  scrollAndMergeVoterDialog,
} from "./facebook_harvest.mjs";

export const BALAZS_BOGNAR = Object.freeze({
  id: "100001332278141",
  name: "Balázs Bognár",
});

const NON_INVESTMENT_TITLE_PREFIXES = Object.freeze([
  "infláció hatása",
  "csoport tagok, csatlakozás",
  "biztosítás szavazás",
]);

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function isBalazs(post) {
  return String(post?.author?.id ?? "") === BALAZS_BOGNAR.id
    && String(post?.author?.name ?? "") === BALAZS_BOGNAR.name;
}

function normalizeTitle(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase("hu-HU").trim().replace(/\s+/g, " ");
}

export function isBalazsInvestmentPoll(post) {
  const title = normalizeTitle(post?.title);
  return isBalazs(post) && !NON_INVESTMENT_TITLE_PREFIXES.some((prefix) => title.startsWith(prefix));
}

function scopedPosts(doc, { investmentOnly = false } = {}) {
  return (doc.posts ?? []).filter((post) => !investmentOnly || isBalazsInvestmentPoll(post));
}

function findBalazsOption(doc, optionId) {
  for (const post of doc.posts ?? []) {
    const option = post.poll?.options?.find((item) => String(item.option_id) === String(optionId));
    if (!option) continue;
    if (!isBalazs(post)) {
      throw new Error(`Option ${optionId} belongs to a non-Balázs post`);
    }
    return { post, option };
  }
  throw new Error(`Unknown Balázs Bognár poll option ${optionId}`);
}

function canonicalProfileUrl(raw) {
  if (!raw) return null;
  try {
    const url = new URL(raw, "https://www.facebook.com");
    const id = url.searchParams.get("id");
    url.search = "";
    if (id) url.searchParams.set("id", id);
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return String(raw).split("?")[0].replace(/\/$/, "");
  }
}

function flattenComments(items, output = []) {
  for (const item of items ?? []) {
    output.push(item);
    flattenComments(item.replies, output);
  }
  return output;
}

export function auditBalazsDataset(targetPath, { investmentOnly = false } = {}) {
  const doc = readJson(targetPath);
  const posts = scopedPosts(doc, { investmentOnly });
  const errors = [];
  const optionIds = new Set();
  let optionCount = 0;
  let completeOptionCount = 0;
  let pendingOptionCount = 0;
  let postsWithVoterData = 0;
  let postsWithCompleteVoterLists = 0;
  let voterCount = 0;
  let voteRecordCount = 0;
  let commentCount = 0;
  const pendingVoterLists = [];

  for (const [postIndex, post] of posts.entries()) {
    if (!isBalazs(post)) {
      errors.push(`posts[${postIndex}] author is not ${BALAZS_BOGNAR.name} (${BALAZS_BOGNAR.id})`);
    }
    if (!Array.isArray(post.poll?.options) || post.poll.options.length === 0) {
      errors.push(`posts[${postIndex}] is not a poll or has no options`);
      continue;
    }
    let postHasVoterData = false;
    let postVoterListsComplete = true;
    for (const option of post.poll.options) {
      optionCount++;
      const optionId = String(option.option_id ?? "");
      if (!optionId) errors.push(`posts[${postIndex}] has an option without option_id`);
      if (optionIds.has(optionId)) errors.push(`duplicate option_id ${optionId}`);
      optionIds.add(optionId);

      const voterUrls = new Set();
      for (const voter of option.voters ?? []) {
        postHasVoterData = true;
        voterCount++;
        voteRecordCount++;
        const url = canonicalProfileUrl(voter.profile_url ?? voter.url);
        if (!url) errors.push(`option ${optionId} has a voter without profile URL`);
        if (voterUrls.has(url)) errors.push(`option ${optionId} contains duplicate voter ${url}`);
        voterUrls.add(url);
      }
      if (option.available_voter_count != null && option.available_voter_count !== voterUrls.size) {
        errors.push(`option ${optionId} available_voter_count=${option.available_voter_count}, actual=${voterUrls.size}`);
      }

      const status = String(option.voter_list_status ?? "unprocessed");
      if (status.startsWith("complete")) {
        completeOptionCount++;
      } else {
        pendingOptionCount++;
        postVoterListsComplete = false;
        pendingVoterLists.push({
          record_id: post.record_id ?? null,
          facebook_post_id: post.facebook_post_id ?? null,
          permalink: post.permalink ?? null,
          title: post.title ?? null,
          option_id: optionId,
          option_label: option.label ?? null,
          status,
        });
      }
    }
    if (postHasVoterData) postsWithVoterData++;
    if (postVoterListsComplete) postsWithCompleteVoterLists++;

    const flatComments = flattenComments(post.comments?.items);
    commentCount += flatComments.length;
    const commentIds = new Set();
    for (const comment of flatComments) {
      const id = String(comment.id ?? "");
      if (!id) errors.push(`posts[${postIndex}] contains a comment without id`);
      if (commentIds.has(id)) errors.push(`posts[${postIndex}] contains duplicate comment ${id}`);
      commentIds.add(id);
    }
    if (post.comments?.loaded_count != null && post.comments.loaded_count !== flatComments.length) {
      errors.push(`posts[${postIndex}] comments.loaded_count=${post.comments.loaded_count}, actual=${flatComments.length}`);
    }
  }

  return {
    ok: errors.length === 0,
    complete: errors.length === 0 && pendingOptionCount === 0,
    scope: investmentOnly ? "investment_polls" : "all_polls",
    author: BALAZS_BOGNAR,
    posts: posts.length,
    posts_with_voter_data: postsWithVoterData,
    posts_with_complete_voter_lists: postsWithCompleteVoterLists,
    options: optionCount,
    complete_options: completeOptionCount,
    pending_options: pendingOptionCount,
    voters: voterCount,
    vote_records: voteRecordCount,
    comments: commentCount,
    pending_voter_lists: pendingVoterLists,
    errors,
  };
}

export function verifyBalazsDatasetComplete(targetPath, options = {}) {
  const audit = auditBalazsDataset(targetPath, options);
  if (!audit.ok) throw new Error(`Dataset audit failed:\n${audit.errors.join("\n")}`);
  if (!audit.complete) {
    throw new Error(
      `Dataset is structurally valid but incomplete: ${audit.pending_options}/${audit.options} voter lists remain pending across `
      + `${audit.posts - audit.posts_with_complete_voter_lists}/${audit.posts} posts`,
    );
  }
  return audit;
}

export function buildExtractionQueue(targetPath, { investmentOnly = false } = {}) {
  const doc = readJson(targetPath);
  const audit = auditBalazsDataset(targetPath, { investmentOnly });
  if (!audit.ok) throw new Error(`Dataset audit failed:\n${audit.errors.join("\n")}`);

  const posts = [];
  for (const post of scopedPosts(doc, { investmentOnly })) {
    const pendingOptions = (post.poll?.options ?? [])
      .filter((option) => !String(option.voter_list_status ?? "").startsWith("complete"))
      .map((option) => ({
        option_id: String(option.option_id),
        label: option.label,
        percentage: option.percentage ?? null,
        status: option.voter_list_status ?? "unprocessed",
      }));
    const commentsPending = !String(post.comments?.status ?? "").startsWith("complete");
    if (pendingOptions.length === 0 && !commentsPending) continue;
    posts.push({
      record_id: post.record_id,
      facebook_post_id: post.facebook_post_id ?? null,
      permalink: post.permalink ?? null,
      title: post.title,
      publication_year: post.publication_year ?? null,
      pending_options: pendingOptions,
      comments: {
        pending: commentsPending,
        displayed_count: post.engagement?.comment_count ?? null,
        loaded_count: post.comments?.loaded_count ?? 0,
        status: post.comments?.status ?? "unprocessed",
        anchor_option_id: String(post.poll.options[0].option_id),
      },
      // Percentages are display metadata, not work estimates. A malformed
      // joined label such as `100% · 45 votes` can otherwise become 10045.
      estimated_cost: pendingOptions.reduce((sum, option) => {
        const source = post.poll.options.find((item) => String(item.option_id) === option.option_id);
        return sum + (+source?.vote_count || +source?.available_voter_count || 1);
      }, 0)
        + (commentsPending ? (+post.engagement?.comment_count || 0) : 0),
    });
  }
  posts.sort((a, b) => a.estimated_cost - b.estimated_cost || String(a.title).localeCompare(String(b.title)));
  return {
    scope: investmentOnly ? "investment_polls" : "all_polls",
    author: BALAZS_BOGNAR,
    remaining_posts: posts.length,
    posts,
  };
}

export async function harvestOpenVoterDialogVerified({
  tab,
  targetPath,
  optionId,
  coarseDelta = 520,
  verificationDelta = 180,
  delayMs = 650,
  stablePasses = 5,
  maxSteps = 400,
}) {
  const doc = readJson(targetPath);
  findBalazsOption(doc, optionId);

  const coarse = await scrollAndMergeVoterDialog({
    tab,
    targetPath,
    optionId,
    direction: "down",
    steps: maxSteps,
    delta: coarseDelta,
    delayMs,
    stablePasses,
  });
  if (coarse.status === "dialog_missing") throw new Error("Voter dialog is not open");
  if (coarse.status === "complete") {
    return { result: coarse, verification: "count_match", completeness: refreshCompleteness(targetPath) };
  }
  if (!coarse.stable_bottom_reached) {
    return { result: coarse, verification: "incomplete_bottom_not_proven" };
  }

  const reverse = await scrollAndMergeVoterDialog({
    tab,
    targetPath,
    optionId,
    direction: "up",
    steps: maxSteps,
    delta: verificationDelta,
    delayMs,
    stablePasses,
  });
  const finalDown = await scrollAndMergeVoterDialog({
    tab,
    targetPath,
    optionId,
    direction: "down",
    steps: maxSteps,
    delta: verificationDelta,
    delayMs,
    stablePasses,
  });

  if (finalDown.scroll) {
    await tab.cua.scroll({
      x: finalDown.scroll.x,
      y: finalDown.scroll.y,
      scrollX: 0,
      scrollY: Math.abs(coarseDelta),
    });
    await tab.playwright.waitForTimeout(delayMs);
  }
  const bottomNudge = await scrollAndMergeVoterDialog({
    tab,
    targetPath,
    optionId,
    direction: "down",
    steps: stablePasses + 3,
    delta: verificationDelta,
    delayMs,
    stablePasses,
  });

  let result = bottomNudge;
  let verification = "incomplete_bottom_not_proven";
  if (result.status === "complete") {
    verification = "count_match_after_bidirectional_sweep";
  } else if (result.stable_bottom_reached && result.bidirectional_verification_required) {
    result = { ...result, ...markVisibleVoterSweepComplete(targetPath, optionId) };
    verification = "visible_identity_gap_after_bidirectional_sweep";
  }
  return {
    result,
    verification,
    evidence: { coarse, reverse, final_down: finalDown, bottom_nudge: bottomNudge },
    completeness: refreshCompleteness(targetPath),
  };
}

function replyControlFromVisibleDom(visibleDom) {
  for (const line of String(visibleDom).split("\n")) {
    const node = line.match(/node_id="?([^"\s>]+)"?/);
    if (!node) continue;
    const hungarian = line.match(/>(\d+)\s+válasz megtekintése</i);
    const english = line.match(/>View\s+(\d+)\s+repl(?:y|ies)</i);
    const count = hungarian?.[1] ?? english?.[1];
    if (count) return { node_id: node[1], displayed_remaining: +count, line };
  }
  return null;
}

export async function selectAllCommentsInOpenPost({
  tab,
  dialogName = "Balázs bejegyzése",
  currentSortLabels = ["A legrelevánsabbak", "A legújabbak", "Most relevant", "Newest"],
  allCommentsLabel = "Az összes hozzászólás",
  allCommentsMenuItemName = "Az összes hozzászólás Az összes hozzászólás megjelenítése, a lehetséges kéretlen tartalmakkal együtt.",
  waitMs = 900,
}) {
  await tab.playwright.domSnapshot();
  const dialog = tab.playwright.getByRole("dialog", { name: dialogName, exact: true });
  const dialogCount = await dialog.count();
  if (dialogCount > 1) throw new Error(`Expected at most one ${dialogName} dialog, found ${dialogCount}`);
  const root = dialogCount === 1 ? dialog : tab.playwright;

  const alreadyAll = root.getByText(allCommentsLabel, { exact: true }).filter({ visible: true });
  if (await alreadyAll.count() === 1) return { changed: false, sort: allCommentsLabel };

  let sortControl = null;
  for (const label of currentSortLabels) {
    const candidate = root.getByText(label, { exact: true }).filter({ visible: true });
    if (await candidate.count() === 1) {
      sortControl = candidate;
      break;
    }
  }
  if (!sortControl) throw new Error("Could not uniquely locate the current comment-sort control");
  await sortControl.click();
  await tab.playwright.domSnapshot();

  const allComments = tab.playwright.getByRole("menuitem", { name: allCommentsMenuItemName, exact: true });
  const allCount = await allComments.count();
  if (allCount !== 1) throw new Error(`Expected one All comments menu item, found ${allCount}`);
  await allComments.click();
  await tab.playwright.waitForTimeout(waitMs);
  await tab.playwright.domSnapshot();
  return { changed: true, sort: allCommentsLabel };
}

export async function harvestOpenPostComments({
  tab,
  targetPath,
  optionId,
  dialogName = "Balázs bejegyzése",
  maxActions = 250,
  delayMs = 900,
  scrollDelta = 800,
  stableScrollPasses = 3,
  selectAll = true,
}) {
  const doc = readJson(targetPath);
  const { post } = findBalazsOption(doc, optionId);
  const dialog = tab.playwright.getByRole("dialog", { name: dialogName, exact: true });
  const dialogCount = await dialog.count();
  if (dialogCount > 1) throw new Error(`Expected at most one ${dialogName} dialog, found ${dialogCount}`);

  if (selectAll) await selectAllCommentsInOpenPost({ tab, dialogName, waitMs: delayMs });

  let merged = await mergeVisibleComments({ tab, targetPath, optionId });
  if (merged.sort !== "Az összes hozzászólás" && merged.sort !== "All comments") {
    throw new Error(`Comments must be switched to All comments first; current sort is ${merged.sort ?? "unknown"}`);
  }

  let actions = 0;
  let scrollsWithoutGrowth = 0;
  let previousLoaded = merged.loaded_count;
  while (actions < maxActions && scrollsWithoutGrowth < stableScrollPasses) {
    const visibleDom = await tab.dom_cua.get_visible_dom();
    const control = replyControlFromVisibleDom(visibleDom);
    if (control) {
      await tab.dom_cua.click({ node_id: control.node_id });
      await tab.playwright.waitForTimeout(delayMs);
      await tab.playwright.domSnapshot();
      merged = await mergeVisibleComments({ tab, targetPath, optionId });
      actions++;
      scrollsWithoutGrowth = 0;
      previousLoaded = merged.loaded_count;
      continue;
    }

    const rect = dialogCount === 1
      ? await dialog.evaluate((element) => {
        const box = element.getBoundingClientRect();
        return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
      })
      : await tab.playwright.evaluate(() => ({ x: innerWidth / 2, y: innerHeight / 2 }));
    await tab.cua.scroll({ x: rect.x, y: rect.y, scrollX: 0, scrollY: scrollDelta });
    await tab.playwright.waitForTimeout(delayMs);
    await tab.playwright.domSnapshot();
    merged = await mergeVisibleComments({ tab, targetPath, optionId });
    scrollsWithoutGrowth = merged.loaded_count === previousLoaded ? scrollsWithoutGrowth + 1 : 0;
    previousLoaded = merged.loaded_count;
  }

  const displayed = +post.engagement?.comment_count || null;
  let terminal = merged;
  if (
    displayed !== null
    && merged.loaded_count < displayed
    && scrollsWithoutGrowth >= stableScrollPasses
    && (merged.sort === "Az összes hozzászólás" || merged.sort === "All comments")
  ) {
    terminal = { ...merged, ...markVisibleCommentSweepComplete(targetPath, optionId) };
  }
  return {
    ...terminal,
    displayed_count: displayed,
    reply_actions: actions,
    stable_scroll_passes: scrollsWithoutGrowth,
    complete: displayed !== null && (merged.loaded_count >= displayed || terminal.status === "complete_visible_comment_gap"),
    completeness: refreshCompleteness(targetPath),
  };
}

export function markVisibleCommentSweepComplete(targetPath, optionId) {
  const doc = readJson(targetPath);
  const { post } = findBalazsOption(doc, optionId);
  const loaded = +post.comments?.loaded_count || 0;
  const displayed = +post.engagement?.comment_count || null;
  if (post.comments?.sort !== "Az összes hozzászólás" && post.comments?.sort !== "All comments") {
    throw new Error("Visible comment-gap completion requires All comments sort");
  }
  post.comments.status = "complete_visible_comment_gap";
  post.comments.available_comment_count = loaded;
  post.comments.displayed_comment_count = displayed;
  post.comments.extraction_notes = [...new Set([
    ...(post.comments.extraction_notes ?? []),
    "All comments was exhausted after reply expansion and stable scrolling, but Facebook rendered fewer comment identities than the displayed count; deleted, unavailable, or withheld comments are not inferred.",
  ])];
  writeJson(targetPath, doc);
  return { status: post.comments.status, loaded_count: loaded, displayed_count: displayed };
}

export function exportBalazsPolls({ targetPath, outputPath }) {
  const doc = readJson(targetPath);
  const audit = auditBalazsDataset(targetPath);
  if (!audit.ok) throw new Error(`Dataset audit failed:\n${audit.errors.join("\n")}`);

  const posts = (doc.posts ?? []).filter(isBalazs).map((post) => {
    const voteRecords = [];
    for (const option of post.poll.options) {
      for (const voter of option.voters ?? []) {
        voteRecords.push({
          voter: {
            name: voter.name,
            profile_url: canonicalProfileUrl(voter.profile_url ?? voter.url),
          },
          option_id: String(option.option_id),
          option_label: option.label,
        });
      }
    }
    return {
      record_id: post.record_id ?? null,
      facebook_post_id: post.facebook_post_id ?? null,
      permalink: post.permalink ?? null,
      title: post.title,
      published_at: post.published_at ?? null,
      published_month: post.published_month ?? null,
      publication_year: post.publication_year ?? null,
      author: post.author,
      text: post.text_visible ?? null,
      poll: {
        selection_type: post.poll.selection_type ?? null,
        options: post.poll.options,
        vote_records: voteRecords,
      },
      comments: post.comments,
      completeness: {
        voter_lists_complete: post.poll.options.every((option) => String(option.voter_list_status ?? "").startsWith("complete")),
        comments_status: post.comments?.status ?? "unprocessed",
      },
    };
  });

  const output = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    scope: {
      platform: "facebook",
      group_id: "257529845152517",
      author: BALAZS_BOGNAR,
      content_type: "poll_posts_only",
    },
    posts,
    completeness: doc.completeness ?? null,
    audit,
  };
  writeJson(outputPath, output);
  return { output_path: outputPath, posts: posts.length, audit };
}

const argv = globalThis.process?.argv;
if (Array.isArray(argv) && argv[1] && import.meta.url === pathToFileURL(argv[1]).href) {
  const investmentOnly = argv.includes("--investment-only");
  const [command, targetPath, outputPath] = argv.slice(2).filter((value) => value !== "--investment-only");
  if (!command || !targetPath) {
    throw new Error("Usage: node balazs_bognar_polls.mjs <audit|verify|queue|export> <input.json> [output.json] [--investment-only]");
  }
  if (command === "audit") console.log(JSON.stringify(auditBalazsDataset(targetPath, { investmentOnly }), null, 2));
  else if (command === "verify") console.log(JSON.stringify(verifyBalazsDatasetComplete(targetPath, { investmentOnly }), null, 2));
  else if (command === "queue") console.log(JSON.stringify(buildExtractionQueue(targetPath, { investmentOnly }), null, 2));
  else if (command === "export") {
    if (!outputPath) throw new Error("export requires an output path");
    console.log(JSON.stringify(exportBalazsPolls({ targetPath, outputPath }), null, 2));
  } else throw new Error(`Unknown command ${command}`);
}
