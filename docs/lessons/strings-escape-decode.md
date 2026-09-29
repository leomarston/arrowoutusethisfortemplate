---
name: strings-escape-decode
description: "extract.py must DECODE Swift escapes or every multi-line string ships untranslated in all 48 languages"
metadata:
  type: reference
---

`tools/extract.py` captures the literal SOURCE text of each Swift string. A newline written as
`\n` in Swift therefore arrives as **two characters** (backslash, n). `keys.py`'s `esc()` then
escapes the backslash again, and the `.strings` file gets a literal `\\n` — a key the runtime can
never match.

**The symptom is invisible in English.** SwiftUI falls back to the key itself, so the English
build looks perfect; only the other 48 languages silently show English. Had the lookup ever
succeeded it would have rendered a visible `\n` instead of a line break.

Caught by the localisation audit on **boxingtimer AND ledbanner** — twice, because the fix was
applied to the output (`.strings` files) rather than the cause.

**Fixed at the cause** (2026-09-02): extract.py now decodes `\n`, `\t` and `\"` at the point of
capture, so keys.py re-encodes them correctly. `keys.py`'s REMOVE entries must then match the
DECODED literal (the support-mail body is the one that trips this).

**Verify with Apple's own parser, never by reading the file:**

    plutil -convert json -o - App/Resources/de.lproj/Localizable.strings

then check `"\n" in key` for the multi-line keys. A `.strings` file shows `\n` either way.

The toolchain now lives in `template/tools/` and `new_app.sh` token-fills `*.py`, so a fix
reaches the next app. Before that, each app copied `tools/` from whichever app was built
before it and fixes never propagated. Related: [[localizedstringkey-not-string]],
[[localize-all-50-locales]].
