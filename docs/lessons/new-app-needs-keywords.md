---
name: new-app-needs-keywords
description: A NEW app cannot be submitted without a keywords value — the never-upload-keywords rule only protects existing ones
metadata:
  type: project
---

App Store Connect **refuses to review a first version with an empty `keywords` field**:

```
POST /v1/reviewSubmissionItems -> 409 STATE_ERROR.ENTITY_STATE_INVALID
  associatedErrors: /v1/appStoreVersionLocalizations/{id}
    ENTITY_ERROR.ATTRIBUTE.REQUIRED
    "You must provide a value for the attribute 'keywords'"
```

`asc_submit.py` reports this only as `!! appStoreVersion item eklenemedi` — it swallows the
body, so POST the item manually and print the response to see the real cause.

**Why this does not contradict [[keywords-are-user-owned]]:** that rule exists so `deliver`
never OVERWRITES keywords the user has tuned. On a brand-new app there is no value to
protect and the app is simply unsubmittable without one.

**How to apply:** on a first submission, set keywords with a direct
`PATCH /v1/appStoreVersionLocalizations/{id}` — **not** by creating `fastlane/metadata/
en-US/keywords.txt`. That way the field is populated but `deliver` still has no file to push
on later runs, so the user's edits stay safe.

Related: [[keywords-are-user-owned]], [[aso-keywords-and-screenshots-rule]], [[asc-subscription-submission]]
