---
name: localize-top-13-locales
description: HARD RULE (2026-09-12) — the locale set is 13: the former top 10 PLUS Polish, Slovak and Slovenian
metadata:
  type: feedback
---

Owner's call 2026-09-12: **add Polish, Slovak and Slovenian to the localization set.**
This SUPERSEDES [[localize-top-10-locales]].

**The 13 store locales** (`fastlane/metadata/<loc>/`):
`en-US de-DE fr-FR es-ES it pt-BR tr ja ko zh-Hans pl sk sl-SI`

**The 13 in-app catalogues** (`App/Resources/<lang>.lproj/`):
`en de fr es it pt-BR tr ja ko zh-Hans pl sk sl`

⚠️ The store locale is **sl-SI** but the `.lproj` folder is **sl**. Polish and Slovak are
`pl`/`sk` in both. Getting this wrong writes a folder Apple ignores.

**Why Polish earns its place — measured, not assumed:** PL was 5 subscription starts, **4
payers (80%)**, $30.58 proceeds = **36% of all revenue ever** from 7% of starts. Best geo
in the portfolio by a wide margin. And StopDog's Polish subscriber paid $12.29 on the
ANNUAL plan from an app that was **entirely in English** — no Polish UI, listing or
keywords. That is the strongest localization signal in the data.

**Translation standard (owner, verbatim): "dont just chicken translate."** Natural native
register, platform-native vocabulary, short UI strings. Slavic inflection means any string
interpolating a number needs phrasing that survives all cases.

**Keywords:** translate only as real search behaviour, never literally — often an English
loanword or a different phrase entirely. Additive only.

**Critical interaction with [[never-touch-keywords-or-description]]:** adding a NEW locale
is additive and safe. Editing an EXISTING locale's name/subtitle/description/keywords is
still forbidden. Never touch en-US.

Pipeline per app: `tools/keys.py` → `design/strings_en.json`; `tools/tr.py` (stdin
`{"pl":[...ordered values...]}`); `tools/meta.py` (stdin `{"pl":{name,subtitle,promo,desc,
notes}}`, enforces 30/30/170/4000 and **silently skips an overlong field**, so a missing
name.txt means the limit was blown); `tools/check_strings.py` validates plutil + key parity
+ format-specifier COUNT AND ORDER. Then `xcodegen generate` — `.lproj` folders become
knownRegions, and skipping it ships English-only with translations unused on disk
([[reordered-args-need-positional]], [[localizedstringkey-not-string]]).
