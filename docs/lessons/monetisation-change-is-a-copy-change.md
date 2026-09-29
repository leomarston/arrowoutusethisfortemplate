---
name: monetisation-change-is-a-copy-change
description: Changing the free tier falsifies store + in-app copy in every locale; budget chars first, most locales have <40 free
metadata:
  type: project
---

Adding a 5-a-day delete cap to storagecleaner (2026-09-14) falsified a whole section of the LIVE
listing — "deleting them is free and unlimited, no daily cap" — in **all 14 locales**, plus the Pro
paragraph, the subscription terms, the in-app honesty screen and the reviewer notes. Shipping the
cap against that text is a straight Guideline 2.3.1.

**Why:** A paywall change is never just code. Every claim made about the old free tier becomes a
false claim the moment the gate moves, and the store description is the one place Apple checks it.

**How to apply:** Before writing replacements, **measure the character budget per locale**. The
description limit is 4,000 and most locales had only **3-40 characters of headroom** (de-DE 6,
sl-SI 3, fr-FR 7) — the first attempt blew seven locales at once. Replacement paragraphs must come
in at or under the originals; compute `4000 - total + len(lines being replaced)` and write to it.
Reviewer notes have their own undocumented 4,000 cap. Then re-run `scripts/meta_sdk.py --check`,
whose copy audit catches surviving claims across store, in-app and reviewer text.

Related: [[free-tier-copies-the-leader]], [[locale-urls-before-the-length-check]],
[[never-touch-keywords-or-description]].
