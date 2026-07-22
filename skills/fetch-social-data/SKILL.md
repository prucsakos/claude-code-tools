---
name: fetch-social-data
description: Efficiently retrieve structured, read-only social data from supported websites through an authenticated browser session. Use for Facebook posts, polls and voter lists, nested comments, home or group feeds, joined groups, group search with author/date filters, and posts under a profile or page. Preserve privacy boundaries and never react, vote, post, join, follow, share, message, report, or perform any other side effect.
---

# Fetch Social Data

Retrieve visible social data through the user's authenticated browser session and return structured, source-linked results without changing account or site state.

## Select the site guide

- For Facebook, read [references/facebook.md](references/facebook.md) completely before browsing.
- For any unsupported site, stop and explain that the site guide has not been implemented yet. Do not improvise a hidden API or reuse Facebook selectors.

## Core workflow

1. Use the in-app Browser capability and reuse a matching signed-in tab when available.
2. Confirm the requested scope: target URL/profile/group, fields, comment depth, result limit, and time range. Infer harmless omissions when possible.
3. Navigate only through visible Facebook UI or stable URLs documented in the site guide.
4. Take a fresh DOM snapshot before constructing locators. Prefer accessibility roles, names, stable `href`s, and bounded read-only DOM evaluation. Never depend on generated CSS classes.
5. Expand only read-only controls required to reveal data, such as `See more`, more comments, nested replies, sort menus, and search filters.
6. Extract into the schemas below. Normalize URLs and deduplicate before scrolling for more items.
7. Stop at the requested limit or explain the completeness boundary. Facebook feeds and comments are lazy-loaded and may not expose a stable total.

For large Facebook polls or comment trees, use [scripts/facebook_harvest.mjs](scripts/facebook_harvest.mjs) from the browser runtime. Its voter and comment helpers merge each rendered batch directly into the JSON output so virtualization or a later browser timeout does not discard earlier data. Read the Facebook guide before using the script; it does not choose or click poll controls by itself.

For the FIRE-group collection restricted to Balázs Bognár, use [scripts/balazs_bognar_polls.mjs](scripts/balazs_bognar_polls.mjs). It hard-locks the author to Facebook ID `100001332278141`, audits every post before processing, performs the slow bidirectional voter-list verification, expands and union-merges nested replies on both post dialogs and inline permalink pages, builds a cheapest-first pending-work queue, and exports explicit voter-to-option records. It still requires the agent to open the proven nested percentage/count control rather than the selectable poll row.

Run Facebook work sequentially with the script defaults: one open voter/comment surface, a 650 ms settle delay, durable merge after every rendered batch, and several unchanged passes before completion. Do not claim that this prevents rate limits. Stop on checkpoint, CAPTCHA, login, permission, or unusual loading failures and resume from the persisted JSON instead of increasing concurrency or retry speed.

Useful CLI commands:

```text
node scripts/balazs_bognar_polls.mjs audit input.json
node scripts/balazs_bognar_polls.mjs verify input.json
node scripts/balazs_bognar_polls.mjs verify input.json --investment-only
node scripts/balazs_bognar_polls.mjs queue input.json
node scripts/balazs_bognar_polls.mjs export input.json output.json
```

`audit` distinguishes structural validity (`ok`) from voter-list completeness
(`complete`) and lists every pending option. Before treating an extraction as
finished or running a downstream analytics pipeline, run `verify`; it exits
non-zero while any voter list remains pending.

Use `--investment-only` with `audit`, `verify`, or `queue` when the requested
scope is the recurring FIRE investment polls. The full export also contains
unrelated inflation, group-membership, and insurance polls; their pending voter
lists must not make a completed investment-only pipeline look incomplete.

### Collection gotchas

- Persist after every visible voter batch. Facebook virtualizes long dialogs,
  so identities scrolled out of view cannot be reconstructed after a timeout or
  reload unless each batch was already union-merged into the working JSON.
- Prove exhaustion bidirectionally. Sweep down, up, and down again with several
  unchanged passes before marking a list complete. Newer polls may display a
  much larger vote count while rendering only about ten identities; record
  `complete_visible_identity_gap` after stable exhaustion and never invent the
  hidden names.
- Click only the nested percentage or vote-count control that is proven to open
  the voter dialog. The surrounding option row is the voting control and is a
  prohibited side effect.
- Treat Facebook group search as a discovery aid, not a complete chronological
  index. Date filters and query text can remain stale or omit results. Validate
  the visible author, title, and year on every result, search by distinctive
  title fragments, and deduplicate by stable option/post identifiers.
- Parse percentage and vote-count text independently. Joined accessible text
  such as `100% · 45 votes` can otherwise become the impossible number `10045`.
  Queue estimates must prefer the explicit vote count, then visible voter count,
  and use percentages only as display metadata.
- Preserve `record_id` and `published_month` in exports. Some older posts expose
  neither a Facebook post ID, permalink, nor exact timestamp; stable record IDs
  support date overrides and the month field provides an auditable fallback.
- Separate structural validity from requested-scope completeness. `audit.ok`
  means the data is internally consistent; `audit.complete` means every voter
  list in the selected scope reached a terminal status.

## Side-effect boundary

Treat the following as allowed read-only actions: navigation, search, changing result filters or sort order, opening post details, opening reaction or voter lists, expanding text, loading more comments, and expanding nested replies.

Never click or submit controls that can create or modify data, including:

- reaction, Like, Follow, Join, Leave, Invite, Interested, Save, Hide, Report, Share, Send, or Message controls;
- poll options, even when they look like ordinary rows or buttons;
- comment or post composers, enabled submit buttons, identity selectors, uploads, or file pickers;
- account, notification, privacy, membership, or moderation settings.

If a requested fact is available only through a control whose side effect cannot be ruled out, report it as unavailable without interaction.

## Output schemas

Use compact JSON-compatible objects unless the user requests another format.

### Post

```text
{
  permalink, author: {name, url}, context, timestamp_text, timestamp_iso,
  visibility, text, media: [{type, url, alt}], external_links: [{label, url}],
  reaction_summary: [{type, count}], comment_count, share_count,
  is_poll, poll, comments, extraction_notes
}
```

### Poll

Treat "categories" as poll options unless the user defines another meaning.

```text
{
  question, author: {name, url}, timestamp_text, timestamp_iso,
  options: [{label, vote_count, voters: [{name, url}], selected}],
  total_votes, allows_multiple, allows_user_options, voter_visibility,
  extraction_notes
}
```

### Comment tree

```text
{
  author: {name, url}, timestamp_text, timestamp_iso, permalink,
  text, reaction_count, replies: [comment], extraction_notes
}
```

### Group and feed

```text
group = {name, url, privacy, member_count, last_active, joined}
feed = {source, source_url, order, extracted_at, items: [post], completeness}
```

## Quality rules

- Preserve the visible distinction between a profile/page author and a group or page context.
- Return absolute timestamps when exposed through accessible labels; keep relative display text separately.
- Strip tracking parameters from canonical entity URLs, but preserve identifiers such as `comment_id` and `reply_comment_id` when they identify a requested comment.
- Mark counts as displayed, approximate, or unavailable. Do not infer hidden voters, deleted comments, private profiles, or unrendered results.
- Distinguish `complete_displayed_count_match` from `complete_visible_comment_gap`. The latter means All comments and every visible reply/load boundary were exhausted, but Facebook rendered fewer identities than its displayed count.
- State the sort order used for comments and feeds.
- Treat search results as relevance-ranked unless the UI explicitly proves another order.
- Do not expose unrelated private feed content in examples, logs, or the final answer.
