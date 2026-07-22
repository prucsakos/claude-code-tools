import fs from "node:fs";

function readJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function writeJson(path, value) {
  fs.writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function findOption(doc, optionId) {
  for (const post of doc.posts ?? []) {
    const option = post.poll?.options?.find((item) => String(item.option_id) === String(optionId));
    if (option) return { post, option };
  }
  return null;
}

function canonicalProfileUrl(url) {
  try {
    const parsed = new URL(url, "https://www.facebook.com");
    for (const key of [...parsed.searchParams.keys()]) {
      if (key !== "id") parsed.searchParams.delete(key);
    }
    parsed.hash = "";
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return String(url).split("?")[0];
  }
}

async function readVoterDialog(tab) {
  return tab.playwright.evaluate(() => {
    const dialog = [...document.querySelectorAll('[role="dialog"]')]
      .find((item) => /\d+%\s*·\s*\d+\s+szavazat/.test(item.innerText || ""));
    if (!dialog) return null;
    const text = dialog.innerText || "";
    const header = text.match(/(\d+)%\s*·\s*(\d+)\s+szavazat/);
    const scrollable = [...dialog.querySelectorAll("*")]
      .filter((element) => element.scrollHeight > element.clientHeight + 40 && element.clientHeight > 200)
      .sort((a, b) => b.clientHeight - a.clientHeight)[0];
    const rect = scrollable?.getBoundingClientRect();
    const voters = [...dialog.querySelectorAll("a[href]")]
      .map((link) => ({
        name: (link.innerText || "").trim(),
        profile_url: link.href,
      }))
      .filter((item) => item.name && !item.name.endsWith("profilképe"));
    return {
      label: text.split("\n")[0] || null,
      percentage: header ? +header[1] : null,
      vote_count: header ? +header[2] : null,
      voters,
      scroll: rect ? {
        x: rect.x + rect.width / 2,
        y: rect.y + rect.height / 2,
        top: scrollable.scrollTop,
        height: scrollable.scrollHeight,
        client: scrollable.clientHeight,
      } : null,
    };
  });
}

export async function mergeVisibleVoterDialog({ tab, targetPath, optionId }) {
  const observed = await readVoterDialog(tab);
  if (!observed) return { status: "dialog_missing", option_id: String(optionId) };
  const doc = readJson(targetPath);
  const match = findOption(doc, optionId);
  if (!match) throw new Error(`Unknown poll option ${optionId}`);
  const byUrl = new Map();
  for (const voter of match.option.voters ?? []) {
    byUrl.set(canonicalProfileUrl(voter.profile_url ?? voter.url), {
      name: voter.name,
      profile_url: canonicalProfileUrl(voter.profile_url ?? voter.url),
    });
  }
  for (const voter of observed.voters) {
    const profileUrl = canonicalProfileUrl(voter.profile_url);
    byUrl.set(profileUrl, { name: voter.name, profile_url: profileUrl });
  }
  match.option.vote_count = observed.vote_count;
  match.option.voters = [...byUrl.values()];
  match.option.available_voter_count = byUrl.size;
  match.option.voter_list_status = byUrl.size >= observed.vote_count
    ? "complete"
    : "partial_virtualized";
  writeJson(targetPath, doc);
  return {
    status: match.option.voter_list_status,
    option_id: String(optionId),
    label: observed.label,
    vote_count: observed.vote_count,
    available_voter_count: byUrl.size,
    scroll: observed.scroll,
  };
}

export async function scrollAndMergeVoterDialog({
  tab,
  targetPath,
  optionId,
  direction = "down",
  steps = 6,
  delta = 420,
  delayMs = 180,
  stablePasses = 3,
}) {
  let result = await mergeVisibleVoterDialog({ tab, targetPath, optionId });
  let unchanged = 0;
  let previousSignature = null;
  let stableEnd = false;
  for (let step = 0; step < steps; step++) {
    if (!result.scroll) break;
    const atTop = result.scroll.top <= 3;
    const atBottom = result.scroll.top + result.scroll.client >= result.scroll.height - 8;
    if (direction === "up" && atTop) break;
    const signature = `${result.available_voter_count}:${result.scroll.height}`;
    unchanged = atBottom && signature === previousSignature ? unchanged + 1 : 0;
    previousSignature = signature;
    if (direction === "down" && atBottom && unchanged >= stablePasses) {
      stableEnd = true;
      break;
    }
    await tab.cua.scroll({
      x: result.scroll.x,
      y: result.scroll.y,
      scrollX: 0,
      scrollY: direction === "up" ? -Math.abs(delta) : Math.abs(delta),
    });
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    result = await mergeVisibleVoterDialog({ tab, targetPath, optionId });
  }
  result.stable_bottom_reached = stableEnd;
  result.bidirectional_verification_required = Boolean(
    stableEnd && result.vote_count !== null && result.available_voter_count < result.vote_count
  );
  return result;
}

export function markZeroVoteOptions(targetPath) {
  const doc = readJson(targetPath);
  let updated = 0;
  for (const post of doc.posts ?? []) {
    for (const option of post.poll?.options ?? []) {
      if (+option.percentage === 0) {
        option.vote_count = 0;
        option.voters = [];
        option.available_voter_count = 0;
        option.voter_list_status = "complete_zero_votes";
        updated++;
      }
    }
  }
  writeJson(targetPath, doc);
  return { updated };
}

export function resetOptionVoters(targetPath, optionId) {
  const doc = readJson(targetPath);
  const match = findOption(doc, optionId);
  if (!match) throw new Error(`Unknown poll option ${optionId}`);
  match.option.vote_count = null;
  match.option.voters = null;
  delete match.option.available_voter_count;
  delete match.option.voter_list_status;
  writeJson(targetPath, doc);
  return { option_id: String(optionId), reset: true };
}

export function markVisibleVoterSweepComplete(targetPath, optionId) {
  const doc = readJson(targetPath);
  const match = findOption(doc, optionId);
  if (!match) throw new Error(`Unknown poll option ${optionId}`);
  const available = match.option.voters?.length ?? 0;
  const votes = match.option.vote_count;
  match.option.available_voter_count = available;
  match.option.voter_list_status = votes !== null && available >= votes
    ? "complete"
    : "complete_visible_identity_gap";
  writeJson(targetPath, doc);
  return {
    option_id: String(optionId),
    vote_count: votes,
    available_voter_count: available,
    status: match.option.voter_list_status,
  };
}

export function refreshCompleteness(targetPath) {
  const doc = readJson(targetPath);
  const options = (doc.posts ?? []).flatMap((post) => post.poll?.options ?? []);
  const comments = (doc.posts ?? []).map((post) => post.comments);
  const voterStatuses = {};
  for (const option of options) {
    const status = option.voter_list_status ?? "unprocessed";
    voterStatuses[status] = (voterStatuses[status] ?? 0) + 1;
  }
  const commentStatuses = {};
  for (const item of comments) {
    const status = item?.status ?? "unprocessed";
    commentStatuses[status] = (commentStatuses[status] ?? 0) + 1;
  }
  doc.completeness.voter_lists = {
    total_options: options.length,
    by_status: voterStatuses,
  };
  doc.completeness.comments = {
    total_posts: comments.length,
    by_status: commentStatuses,
  };
  doc.completeness.voter_lists_updated_options = options.filter((option) => option.vote_count !== null).length;
  writeJson(targetPath, doc);
  return { voter_lists: doc.completeness.voter_lists, comments: doc.completeness.comments };
}

function canonicalFacebookUrl(raw, preserve = []) {
  try {
    const url = new URL(raw, "https://www.facebook.com");
    const keep = new Map();
    for (const key of preserve) {
      if (url.searchParams.has(key)) keep.set(key, url.searchParams.get(key));
    }
    url.search = "";
    for (const [key, value] of keep) url.searchParams.set(key, value);
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return raw;
  }
}

function commentTextFromLines(rawText, author, timestampText) {
  const lines = String(rawText).split("\n").map((line) => line.replace(/\u00a0/g, " ").trim());
  let skippedAuthor = false;
  const ignored = new Set(["", "·", "Válasz", "Tetszik", timestampText]);
  return lines.filter((line) => {
    if (!skippedAuthor && line === author) {
      skippedAuthor = true;
      return false;
    }
    if (ignored.has(line)) return false;
    if (/^\d+ reakció/.test(line)) return false;
    return true;
  }).join("\n").trim();
}

async function readVisibleCommentArticles(tab) {
  return tab.playwright.evaluate(() => {
    const dialogs = [...document.querySelectorAll('[role="dialog"]')];
    const dialog = dialogs.find((item) => !item.querySelector('[role="dialog"]')) ?? dialogs.at(-1);
    if (!dialog) return null;
    const articles = [...dialog.querySelectorAll('[role="article"]')].map((article) => ({
      aria: article.getAttribute("aria-label") || "",
      text: article.innerText || "",
      links: [...article.querySelectorAll("a[href]")].map((link) => ({
        text: (link.innerText || "").trim(),
        href: link.href,
      })),
      buttons: [...article.querySelectorAll('[role="button"]')].map((button) => ({
        aria: button.getAttribute("aria-label") || "",
        text: (button.innerText || "").trim(),
      })),
    }));
    const sortButton = [...dialog.querySelectorAll('[role="button"]')]
      .map((button) => (button.innerText || "").trim())
      .find((text) => text === "Az összes hozzászólás" || text === "A legújabbak" || text === "A legrelevánsabbak") ?? null;
    return { articles, sort: sortButton };
  });
}

export async function mergeVisibleComments({ tab, targetPath, optionId }) {
  const observed = await readVisibleCommentArticles(tab);
  if (!observed) return { status: "dialog_missing" };
  const flat = [];
  for (const article of observed.articles) {
    const replyMatch = article.aria.match(/^(.+?) válasza (.+?) (?:hozzászólására|válaszára) \((.+)\)$/);
    const topMatch = article.aria.match(/^(.+?) hozzászólása \((.+)\)$/);
    if (!replyMatch && !topMatch) continue;
    const authorName = replyMatch ? replyMatch[1] : topMatch[1];
    const parentAuthorName = replyMatch ? replyMatch[2] : null;
    const timestampFromAria = replyMatch ? replyMatch[3] : topMatch[2];
    const permalinkLink = article.links.find((link) => link.href.includes("comment_id="));
    const authorLink = article.links.find((link) => link.text === authorName);
    if (!permalinkLink) continue;
    const parsed = new URL(permalinkLink.href);
    const commentId = parsed.searchParams.get("comment_id");
    const replyCommentId = parsed.searchParams.get("reply_comment_id");
    const timestampText = permalinkLink.text || timestampFromAria;
    const reactionButton = article.buttons.find((button) => /reakció/.test(button.aria));
    const reactionMatch = reactionButton?.aria.match(/(\d+) reakció/);
    flat.push({
      id: replyCommentId || commentId,
      parent_comment_id: replyCommentId ? commentId : null,
      author: {
        name: authorName,
        url: authorLink ? canonicalFacebookUrl(authorLink.href) : null,
      },
      parent_author_name: parentAuthorName,
      timestamp_text: timestampText,
      timestamp_iso: null,
      permalink: canonicalFacebookUrl(permalinkLink.href, ["comment_id", "reply_comment_id"]),
      text: commentTextFromLines(article.text, authorName, timestampText),
      reaction_count: reactionMatch ? +reactionMatch[1] : null,
      replies: [],
      extraction_notes: [],
    });
  }

  const byId = new Map(flat.map((item) => [String(item.id), item]));
  const roots = [];
  for (const item of flat) {
    if (item.parent_comment_id && byId.has(String(item.parent_comment_id))) {
      byId.get(String(item.parent_comment_id)).replies.push(item);
    } else {
      roots.push(item);
    }
  }

  const firstPermalink = flat[0]?.permalink;
  const postMatch = firstPermalink?.match(/\/groups\/([^/]+)\/posts\/(\d+)/);
  const doc = readJson(targetPath);
  const match = findOption(doc, optionId);
  if (!match) throw new Error(`Unknown poll option ${optionId}`);
  if (postMatch) {
    match.post.facebook_post_id = postMatch[2];
    match.post.permalink = `https://www.facebook.com/groups/${postMatch[1]}/posts/${postMatch[2]}`;
  }
  const displayedTotal = +match.post.engagement?.comment_count || null;
  match.post.comments = {
    status: displayedTotal !== null && flat.length >= displayedTotal
      ? "complete_displayed_count_match"
      : "partial_visible",
    sort: observed.sort,
    loaded_count: flat.length,
    top_level_count: roots.length,
    items: roots,
  };
  writeJson(targetPath, doc);
  return {
    status: match.post.comments.status,
    sort: observed.sort,
    loaded_count: flat.length,
    top_level_count: roots.length,
    post_id: match.post.facebook_post_id,
  };
}
