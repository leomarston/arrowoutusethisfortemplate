---
name: template-scaffolds-empty-keywords-txt
description: new_app.sh leaves an EMPTY fastlane/metadata/en-US/keywords.txt that deliver will upload, wiping researched keywords
metadata:
  type: feedback
---

Every freshly scaffolded app has an **empty** `fastlane/metadata/en-US/keywords.txt`.

**Why:** `deliver` uploads whatever is in that file. An empty one blanks the App Store
keyword field at the exact moment of submission, destroying the researched values pushed by
`scripts/asc_keywords.py`. It is invisible until the listing is live. This is precisely the
failure the "keywords are user-owned, never upload them via fastlane" rule exists to prevent.

**How to apply:** `find apps/<slug>/fastlane/metadata -name keywords.txt -delete` right after
scaffolding, and check it again before any `deliver` run. Better: remove it from `template/`.

Related: [[keywords-are-user-owned]], [[new-app-needs-keywords]].
