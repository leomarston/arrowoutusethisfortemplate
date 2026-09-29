---
name: never-touch-keywords-or-description
description: HARD RULE — never change the App Store keywords OR the description of a live app; the ASO is strong and tuned
metadata:
  type: feedback
---

Stated 2026-09-10, emphatically: "NEVER CHANGE THE KEYWORDS OR DESCRIPTION, NEVER
NEVER NEVER, THAT IS OUR BIG NONO, AS OUR ASO IS STRONG RIGHT NOW."

This EXTENDS [[keywords-are-user-owned]] from the keywords field to the
description body. Both are tuned, ranking assets. Not a style preference — a
revenue rule.

**Why:** a live listing's ranking is earned. Rewriting prose for internal
tidiness (an honesty tweak, a URL swap, trimming to fit a length limit) throws
away ranking for nothing the owner asked for. On camdetect I changed all 50
descriptions twice — `privacy.html`→`privacy-ads.html`, then stripping `https://`
to fit the 4000-char cap — and shipped them to ASC before being told. Restored
byte-for-byte from the last approved commit.

**How to apply:**
- Treat description.txt and keywords.txt as READ-ONLY. If a change seems
  necessary, ASK FIRST and say exactly which words and why.
- Never use `deliver`/`upload_text` to fix one field — it uploads keywords and
  the whole description too. PATCH the single attribute:
  `PATCH /v1/appStoreVersionLocalizations/{id}` with only that key.
- Keep NO `fastlane/metadata/*/keywords.txt` in any app (deliver uploads it).
  Mirror the live values to `design/keywords.json` for reference and .gitignore
  the txt files. Done for camdetect 2026-09-10.
- To restore: `git checkout <last-approved-commit> -- .../metadata/*/description.txt`,
  then diff against ASC to confirm byte parity.
- Legitimately per-version and NOT covered by this rule: release_notes.txt,
  privacy_url.txt, review_information/notes.txt, app_privacy_details.json.
