---
name: reordered-args-need-positional
description: A translation that reorders format arguments MUST use positional specifiers (%1$@) or Swift prints the wrong value
metadata:
  type: project
---

When a localized string has two or more format arguments and the translation puts them in a
different order from English, the specifiers must become **positional** — `%1$@`, `%2$lld` — or
Swift substitutes in source order and prints the count where the size belongs.

**Why:** on `storagecleaner`, `"%@ measured across %lld items"` was translated as
`"%lld öğede %@ ölçüldü"` (tr) and equivalently in ja/ko/zh — count first. All four would have
printed a byte size where the item count belongs, in the delete confirmation, right before someone
destroys photos. A specifier check that compares only the *set* of specifiers (e.g. via `sorted()`)
passes this happily; the check has to compare the **ordered list**.

**How to apply:** `tools/check_strings.py` (in `template/tools/`) enforces it — plutil parse, key
parity, ordered specifier match, positional-index completeness, empty and still-English detection.
Run it before every submit. Related: [[localizedstringkey-not-string]], [[strings-escape-decode]],
[[localization-extractor-hides-single-words]].
