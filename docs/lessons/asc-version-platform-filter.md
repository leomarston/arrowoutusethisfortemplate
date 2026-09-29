---
name: asc-version-platform-filter
description: "An app with a stray macOS version record breaks submit; always filter appStoreVersions by platform, and read `platform` before renaming anything"
metadata:
  type: reference
---

`GET /v1/apps/<id>/appStoreVersions` returns versions for **every platform**. If an app ever had
a macOS/Catalyst version record, an unfiltered `limit=1` can hand back that MAC_OS row instead of
the iOS one — and then attaching the new iOS build fails.

**The symptom lies.** `asc_submit.py` reported *"build version'a BAGLANAMADI (version hala kilitli
olabilir)"* — build could not be attached, version may still be locked. The real error only shows
in the raw response:

    409 ENTITY_ERROR.RELATIONSHIP.INVALID
    "The specified build has a different platform than the version."

**Fixed in `scripts/asc_submit.py`:** the version query now carries `filter[platform]=IOS`.

**Two things that make this worse than it sounds:**
- **The stray record can never be removed.** `DELETE` returns 409 *"A version cannot be deleted if
  any build has been uploaded for the platform"* — so once an app has any build, every version row
  it owns is permanent.
- **Version strings are namespaced per platform**, so a macOS 1.0.0 and an iOS 1.0.0 coexist
  legitimately. Seeing "two 1.0.0 versions" is NOT evidence of a duplicate.

**How to apply:** before renaming or deleting any appStoreVersion, print its `platform` field.
On partylights (2026-09-01) I renamed both records on the assumption they were both iOS and
briefly had two versions claiming 1.0.1; the fix was to read `platform`, restore both strings, and
filter the query. Diagnose first — a version record is not a scratch file.
