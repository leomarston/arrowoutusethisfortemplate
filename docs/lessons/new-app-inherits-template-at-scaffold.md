---
name: new-app-inherits-template-at-scaffold
description: Apps copy template/ at scaffold time — fixing template later does NOT fix apps already scaffolded
metadata:
  type: feedback
---

`new_app.sh` COPIES `template/` into `apps/<slug>/`. An app scaffolded before a template fix
keeps the old code forever.

Burned on 2026-08-21: the Guideline 3.1.2 paywall fix went into `template/` **after**
`hearingtest`, `trackdetect` and `hearup` were scaffolded, so all three were submitted with the
exact paywall Apple had just rejected four other apps for. Caught only because the user said
"make sure you don't skip anything, look at what we did with our previous apps."

**How to apply:** after ANY fix to `template/`, immediately check every app that is not yet
approved:
```
grep -L "<marker-from-the-fix>" apps/*/App/<Path>/<File>.swift
```
and backport. Remember the fix must also reach anything DERIVED from the old code —
marketing screenshots and the **subscription review screenshot** both show the paywall, and a
review screenshot cannot be replaced while the subscription is in review (409
`MEDIA_ASSET_DELETE_NOT_ALLOWED`): cancel the submission first, replace, then resubmit.

Related: [[paywall-billed-amount-dominant]], [[appstorage-in-observableobject]]
