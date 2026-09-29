---
name: localization-extractor-hides-single-words
description: tools/extract.py's camelCase filter silently eats real single-word UI copy like "week" — the paywall's price suffix shipped untranslated
metadata:
  type: reference
---

`template/tools/extract.py` skips literals matching `^[a-z][A-Za-z0-9]*$` to drop identifiers
(`rawValue`, `weekly`). That also swallows **genuine single-word UI copy**. On `spinwheel` it
ate `"day" "week" "month" "year" "period"`, which `PaywallView.unitName()` looks up via
`String(localized:)` — so the billed-amount suffix (`€4,99/week`) would have shipped in
English in all 49 languages, on the one screen where a mistranslation costs money.

Nothing catches this: the build is clean, `strings.audit()` only counts lines, and a
screenshot of the DEMO paywall looks fine because the demo passes a raw Swift `String`.

**How to apply:** `tools/keys.py` now has a `FORCE_APPEND` list. After running `keys.py` on a
new app, grep the sources for `String(localized:)` with a bare lowercase word and confirm each
one is in `design/strings_en.json`. Append forced keys AFTER the existing ones so translations
already written stay index-aligned with `tools/strings.py`'s positional writer.

Also: `Text("… \(x, specifier: "%.1f") …")` is invisible to the extractor entirely — the
nested quotes cut the literal in half. Format the value before it reaches the string.

Related: [[localize-all-50-locales]], [[localizedstringkey-not-string]]
