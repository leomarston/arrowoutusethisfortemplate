---
name: localize-top-10-locales
description: HARD RULE (2026-09-05, supersedes the 50-locale rule) — localize to the TOP 10 App Store locales only, and do those properly
metadata:
  type: feedback
---

Localize every new app to the **top 10 App Store locales only**, not 50. The user: *"dont localize
to 50 langs, only top 10 you should localize to, but properly."*

This **supersedes [[localize-all-50-locales]]**, which is no longer the standard.

The ten: `en-US` `zh-Hans` `ja` `de-DE` `fr-FR` `es-ES` `ko` `pt-BR` `it` `tr`. Russian is
deliberately excluded despite market size — Apple suspended App Store purchases there, so a
subscription app earns nothing from it.

**Why:** 50 locales was enormous work per app, and the tail locales carry almost no revenue for a
subscription utility. Breadth was being bought at the cost of quality.

**How to apply:** "properly" is the operative word — idiomatic copy a native speaker would write,
not a pass through a translator. Keywords are still RESEARCHED per storefront, never translated.
Per-locale App Store limits still bind (name/subtitle 30, promo 170, description 4000), and
`tools/loc.py` must write privacy_url/support_url BEFORE the length check or a locale that trips a
limit silently loses both URLs ([[locale-urls-before-the-length-check]]). In-app UI is localized
too, not just the store listing — and a helper typed `String` silently skips the strings table
([[localizedstringkey-not-string]]).

**SUPERSEDED 2026-09-12 by [[localize-top-13-locales]]** — Polish, Slovak and Slovenian added.
