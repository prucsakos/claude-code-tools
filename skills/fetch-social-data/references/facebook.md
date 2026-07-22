# Facebook read-only data retrieval

Verified against Facebook desktop UI in Hungarian on 2026-07-21. Labels vary by locale and Facebook frequently changes its DOM. Use the current DOM snapshot as ground truth.

## Contents

1. Browser and locator strategy
2. Fetching a post
3. Fetching comments and nested replies
4. Fetching polls and voters
5. Fetching feeds
6. Fetching groups
7. Searching posts and filtering
8. Fetching posts under a profile or page
9. URL normalization and deduplication
10. Gotchas and completeness

## Browser and locator strategy

Use the `browser:control-in-app-browser` skill. Claim an already-open Facebook tab when possible so the user's authenticated session and current privacy permissions apply.

Before every interaction:

1. Take or reuse a fresh relevant DOM snapshot.
2. Build a locator from a visible role/name, stable `href`, or scoped container.
3. Count it and act only when it resolves to one element. Scope repeated generic controls to the target post, comment, dialog, or navigation region.
4. After interaction, observe only the state needed for the next decision.

Prefer one bounded `playwright.evaluate` call that projects a small set of already-identified elements. Never dump the entire `body`, embedded application state, cookies, local storage, or hidden GraphQL payloads.

Generated class names are unstable. Accessible headings, regions, articles, labels, and canonical-looking links are more durable.

Common Hungarian labels and concepts observed:

| Concept | Observed label |
|---|---|
| Facebook search | `Keresés a Facebookon` |
| Group search | `Keresés a csoporton belül`, then `Keresés a csoportban` |
| Comments | `Hozzászólások`, `Hozzászólás írása` |
| Load more comments | `További hozzászólások`, `További válaszok` |
| Expand replies | `N válasz megtekintése` |
| Expand text | `Továbbiak` |
| Comment order | `A legrelevánsabbak` or another current sort label |
| Post actions | `Műveletek … bejegyzésénél`, `A bejegyzéssel kapcsolatos műveletek` |
| Group sort | `csoport hírfolyamának rendezése` |

Translate by meaning in other locales; do not hard-code Hungarian text when the snapshot shows another language.

## Fetching a post

Prefer a post detail/permalink page over a feed card. Detail pages expose the author, full text, visibility, media, reaction summary, comment sort, comment articles, and canonical comment links together.

### Open the detail view

Use the first safe path available:

1. Open an existing canonical post link such as `/groups/{group}/posts/{post}` or `/{page-or-profile}/posts/{post}`.
2. Follow a stable outer post wrapper link when the profile/page UI exposes one.
3. Open a media link such as `/photo/?fbid=...`; its complementary panel contains the associated post and comments.
4. Open the timestamp only after the current snapshot proves the timestamp locator. Timestamp text may be visually obfuscated in feed DOM.

Do not use the post action menu to obtain a link unless the user explicitly authorizes clipboard interaction and the menu item is visibly read-only.

### Extract fields

From the post container or detail side panel, collect:

- author name and profile/page URL;
- group/page context separately from the author;
- timestamp display text and the accessible absolute date/time when present;
- visibility from an image/label such as Public, Public group, or Private group;
- complete text after expanding `See more`/`Továbbiak`;
- media URLs and alt text;
- outbound links, unwrapping `l.facebook.com/l.php?u=...` when possible;
- reaction types and displayed counts from the reaction toolbar;
- displayed comment and share counts;
- a canonical permalink from a direct post or comment timestamp URL.

Feed cards may render author, context, and timestamp as separate siblings rather than one semantic `article`. Identify the post boundary through a unique author/action label or by opening the detail view; do not assume every post is `[role=article]`.

## Fetching comments and nested replies

Open the post detail view. The comments section exposes top-level comments as semantic articles with labels similar to `{person} comment ({relative time})`.

1. Record the active comment sort. The default is often Most relevant and is not complete or chronological.
2. If the request needs exhaustive or chronological comments, open the sort control and choose the closest read-only option such as All comments or Newest. Report the chosen order.
3. Repeatedly activate `More comments`/`További hozzászólások` only until the requested limit or until the control disappears.
4. Expand truncated comment text with its scoped `See more` control.
5. Expand `N replies`/`N válasz megtekintése` buttons. These can be siblings immediately after the parent comment rather than descendants of its article.
6. After expansion, rebuild the comment list from a fresh snapshot or one bounded DOM projection.

Useful structure:

- Top-level article label: `{author} hozzászólása (...)`.
- Reply article label: `{reply author} válasza {parent author} hozzászólására (...)`.
- Author link may include `comment_id` but still identifies the author profile.
- Timestamp link may contain the canonical post path plus `comment_id`.
- Reply timestamp link may add `reply_comment_id`.

Build the tree by matching the reply article's named parent and, when available, its `comment_id`/`reply_comment_id`. Names are not globally unique, so prefer IDs when present.

Never focus or fill the comment textbox. The disabled submit button may become active after accidental input.

## Fetching polls and voters

Poll controls are particularly risky because clicking an option may immediately cast or change a vote.

### Detect and extract a poll

On a post detail page, identify the poll from visible option/category rows and vote counts. Extract without clicking:

- question, author, time, and visibility from the normal post fields;
- each option/category label;
- displayed per-option vote count and total votes;
- selected/checked state only when exposed in DOM attributes or visible labels;
- visible settings such as multiple selection or allowing user-added options.

Never infer poll options from unrelated buttons in the post action bar. Never click an option, checkbox, radio, or selectable row.

### Fetch voter identities

Only open a voter list when the current snapshot exposes a separate, clearly read-only vote-count link or button, such as `{N} votes`. Confirm that the locator is the count, not the option row. Then:

1. Open the count dialog.
2. Extract visible voter name/profile URL pairs.
3. Load more only through a clearly read-only list pagination control.
4. Close the dialog without altering selection.

On current desktop poll cards the safe percentage/count control can be a nested `[role=button]` inside the selectable option row. The outer row contains the checkbox and must never be clicked. Confirm the nested control from the current DOM, read its bounding box, and use a trusted screen click when a normal locator click is swallowed by Facebook's rerender. The resulting dialog header exposes both values in the form `{percentage}% · {absolute count} szavazat`.

For long voter lists, use `scripts/facebook_harvest.mjs` and persist after every scroll step. Facebook may remove earlier voter nodes, and reaching the current scrollbar bottom can merely trigger the next lazy-loaded batch. Continue small downward overscrolls until voter count and scroll height remain unchanged for several passes. Canonicalize profile URLs and merge by URL. After a verified down-up-down sweep, using a smaller scroll delta for the reverse and final passes, distinguish:

- `complete`: collected identities equal the absolute vote count;
- `complete_visible_identity_gap`: the list is exhausted but Facebook rendered fewer identities than votes, for example because an account is unavailable;
- `partial_virtualized`: extraction stopped before a stable end was proven.

If the option itself is the only interactive target, the voter count is not clickable, the poll is anonymous, or permissions hide identities, return `voter_visibility: unavailable` and explain why. Do not attempt to reveal hidden voters through application state or private APIs.

Observed limitation during validation: keyword searches for "poll"/"vote" do not reliably return native Facebook polls. Locate a known poll by permalink or browse the target group's feed; search text is relevance-based and may return ordinary posts merely mentioning voting.

## Fetching feeds

### Home feed

Use `https://www.facebook.com/` and locate the main heading/region for feed posts. The home feed mixes followed content, suggested posts, ads, stories, and composer controls.

1. Ignore the create-post region and stories unless requested.
2. Extract only visible post cards.
3. Mark sponsored/suggested items from their visible labels.
4. Scroll incrementally, take a fresh observation, and append only new canonical posts.
5. Stop at the requested item count. Home feed order is personalized and unstable; record `order: personalized`.

### Group feed

- Personal group feed: `https://www.facebook.com/groups/feed/`.
- Groups landing page: `https://www.facebook.com/groups/` also shows recent activity and a joined-groups navigation list.
- Specific group: navigate to its visible group link, normally `/groups/{id-or-slug}/`.

A group page exposes a feed sort button such as `csoport hírfolyamának rendezése`. Open it only to select a read-only ordering requested by the user. Record the exact visible order, for example Recent activity or New posts.

Feed extraction is never provably exhaustive. Return the number of unique posts extracted and the stop reason: requested limit, no new items after another scroll, access boundary, or loading failure.

## Fetching groups

Use these visible routes:

- `/groups/` for navigation plus recent activity;
- `/groups/joins/?nav_source=tab` for all joined groups;
- `/groups/discover/` for discovery, only when requested.

The joined-groups list exposes group name, URL, and often last-active text. The group header exposes privacy and displayed member count. Determine `joined` from visible membership state such as `Member`/`Tagja vagy`; never click it because it may open leave/notification actions.

Do not click Join, Invite, Create group, membership, or group-settings controls.

## Searching posts and filtering

### Search inside a group

Preferred route:

1. Open the target group.
2. Activate the visible `Search within group` control.
3. Fill the dialog combobox and press Enter.

Equivalent stable result route observed:

```text
https://www.facebook.com/groups/{group-id-or-slug}/search/?q={url-encoded-query}
```

The group result navigation can expose:

- Recent posts switch;
- Seen posts switch;
- Publication date filter;
- Post source filter;
- Tagged location filter.

The publication date menu was observed to offer Any date plus individual years, not arbitrary start/end dates. For a narrower period:

1. Select the relevant year(s), one query at a time when needed.
2. Read the absolute timestamp from each result or its detail page.
3. Apply the requested start/end boundary client-side.
4. Report that Facebook did not enforce the exact range.

The Post source field is a searchable combobox. Its initial suggestions can be categories such as Anyone, You, Your friends, Your groups and pages, or Public posts. To filter a certain person, type the person's name and choose the uniquely matching profile suggestion from the fresh snapshot. Do not assume the first suggestion is correct.

### Search across Facebook posts

Observed route:

```text
https://www.facebook.com/search/posts/?q={url-encoded-query}
```

The global posts result page is relevance-ranked and may expose only coarse content-type navigation, with fewer author/date filters than group search. Prefer group search when group context is known. Verify every result's author and context because private joined-group results, public pages, and sponsored content can mix together.

Do not claim a search is exhaustive. Facebook may return results outside the literal query intent and omit older matches.

## Fetching posts under a profile or page

Navigate to the canonical visible profile/page URL, for example `https://www.facebook.com/{username}` or a `profile.php?id=...` link already exposed by Facebook.

1. Verify the page/profile heading and URL.
2. Locate the `Posts`/`Bejegyzések` section. Pages may use an `All` tab instead of a separate Posts tab.
3. Ignore Highlights/Pinned content unless requested, or label it separately.
4. Use the visible post Filter control when it is available and the requested filter is read-only.
5. Extract and deduplicate posts as for a feed.

Profile/page posts often expose an outer canonical post link, especially in highlighted sections. Prefer it over timestamp query/hash links. A profile page can also show nested comments under the first loaded post; keep comments attached to that post rather than treating them as separate profile items.

Respect privacy boundaries. A signed-in user may see only public posts, friends-only posts, or group-context posts depending on permissions. Report visible results only.

## URL normalization and deduplication

Normalize for identity while preserving meaningful IDs:

- resolve relative Facebook URLs against `https://www.facebook.com`;
- remove tracking parameters such as `__cft__`, `__tn__`, `fbclid`, `ref`, and opaque search-session IDs;
- unwrap `https://l.facebook.com/l.php?u={encoded-url}` for outbound links;
- preserve `comment_id` and `reply_comment_id` when the requested entity is a comment;
- prefer `/groups/{group}/posts/{post}` and `/{profile}/posts/{post}` over photo or feed-query URLs;
- when only a comment permalink is available, strip comment query parameters to obtain the parent post permalink and retain the full comment permalink separately;
- deduplicate primarily by canonical permalink, then by stable post ID, then cautiously by author + timestamp + normalized text hash.

Do not merge two posts merely because they contain the same reshared text.

## Gotchas and completeness

- Facebook obfuscates some timestamp text into shuffled character nodes. The DOM snapshot may still expose a human-readable accessible name; otherwise open a proven safe detail link.
- Top-level feed posts are not consistently semantic `article` elements. Comments usually are.
- Facebook virtualizes and lazy-loads feeds. Old DOM nodes can disappear after scrolling; extract and store each batch before the next scroll.
- Voter dialogs can also virtualize or discard earlier rows. Never wait until the end to extract the whole list; union and save after each step.
- The current scrollbar bottom is not proof of the end of a voter list. Downward overscroll can append another batch and increase `scrollHeight`.
- Never mark a voter sweep complete from stable name/height counts alone. Require the scroll container to remain at its actual bottom while those counts stay unchanged across the configured stable passes.
- A first stable bottom with fewer rendered identities than votes is not proof of a visible identity gap. Reverse-sweep to the top with a smaller delta, then sweep down again; this can reveal lazy batches skipped by the first pass. `scrollAndMergeVoterDialog` therefore leaves such a result `partial_virtualized`; call `markVisibleVoterSweepComplete` only after the bidirectional verification.
- Fast 160-180 ms scroll loops can report false stability before Facebook appends the next lazy batch. The helper defaults to a 650 ms settle delay and five stable passes; before finalizing any identity gap, add a deliberate bottom overscroll (about 520 px was effective in this UI) with the same slow settle timing, then repeat the smaller-delta bidirectional sweep.
- A voter dialog may be nested beside duplicate post-detail dialogs. Select the dialog whose visible text matches `{N}% · {M} votes`, not the first `[role=dialog]`.
- Search-card timestamp and wrapper links may be obfuscated hash URLs. Opening the visible comment-count control can reveal a safe post-detail dialog even when its accessible label says `Write a comment`; never type in or focus the composer afterward.
- Post-detail UI can contain nested duplicate dialog roles. For comments, choose the innermost dialog that contains comment articles; for voters, choose the vote-header dialog.
- Switching comment order to All comments temporarily removes articles and shows a loading state. Wait for comment articles to reappear before extracting or expanding replies.
- Reply labels include both `X replied to Y's comment` and `X replied to Y's reply`. Multiple safe reply-expansion buttons can share the same label; count them, then expand each scoped occurrence and re-snapshot after every click.
- Comment permalinks can reveal the canonical `/groups/{group}/posts/{post}` ID even when the search card does not expose a usable post permalink. Preserve `comment_id` and `reply_comment_id` while stripping tracking parameters.
- Long monolithic browser runs risk losing in-memory progress on timeout. Use bounded batches and write the JSON after every voter scroll or comment-expansion batch.
- `blockquote: Facebook` placeholders are noise, not posts.
- The default comment order is often Most relevant. Loading visible comments without changing it is not exhaustive.
- Reply-expansion buttons may be siblings of the parent comment article.
- Counts can change during extraction. Record them as displayed observations, not immutable totals.
- A displayed comment count can include a deleted, unavailable, or otherwise non-renderable item. After selecting All comments, exhausting every read-only reply/load control, and proving stable bottom scrolls, keep the record `partial_visible` when unique rendered articles remain below the displayed count; save the exact boundary evidence and never invent the missing comment.
- Private group data is visible only through the user's current membership. Never copy unrelated private content into diagnostics or examples.
- Search filters and labels vary by locale, group type, permissions, and rollout. Re-snapshot after any locator failure; do not retry the same guessed selector.
- A navigation timeout can still leave the destination loaded. Check the current URL and take a fresh snapshot before retrying.
- If Facebook presents a checkpoint, CAPTCHA, login, or permission prompt, stop and hand control to the user. Do not bypass it.
