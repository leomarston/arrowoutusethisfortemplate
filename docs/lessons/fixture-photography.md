---
name: fixture-photography
description: store frames need CC0 photos of PEOPLE (Openverse, not Wikimedia) at real camera dimensions; and never index a contact sheet built with `ls` using Python's sorted()
metadata:
  type: reference
---

**Photos of people sell a photo app.** The category leaders' App Store frames are couples,
families and graduations, because the product is sold on nearly losing a memory and a landscape
does not carry that. A first pass that deliberately avoided people looked sterile beside theirs.

**Wikimedia Commons is the wrong well.** It is an archive: a CC0 search for "family portrait"
returns military parades, politicians shaking hands, 19th-century engravings and museum scans.
Under a fifth of a 66-photo harvest read as photographs a person would have on their phone.

**Openverse is the right one** — it aggregates Flickr, where modern candid CC0 photography lives,
and its API is keyless:

    https://api.openverse.org/v1/images/?q=<query>&license=cc0,pdm&page_size=N&mature=false

Filter on the `license` field in the response and keep only `cc0` and `pdm`; CC-BY would oblige
attribution inside a store screenshot. Flickr size suffixes: `_k` = 2048px, `_b` = 1024px — ask for
the big one and reject anything under ~60 KB, which is Flickr's missing-size error image.
`apps/storagecleaner/tools/fetch_openverse.py`.

**Upscale fixtures to real camera dimensions (4032px long edge).** A 300 KB web-sized photo makes
every total in a storage app read in kilobytes, which looks broken next to a competitor showing GB.
The app still measures whatever bytes are actually there — nothing is faked.

**And always LOOK at the harvest.** Build a labelled contact sheet and read it before using
anything. But: `ls *.jpg` and Python's `sorted(glob(...))` do **not** agree — macOS collation
ignores punctuation and case, Python sorts by codepoint. Reading indices off a sheet built with
`ls` and then indexing a `sorted()` list silently picks neighbouring photos, which is how six
"people" duplicate groups came out as handcuffs, a cat and a Merry Christmas sign. Pick by
FILENAME, or generate the sheet from the same ordering you will index.
