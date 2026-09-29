---
name: localize-all-50-locales
description: "HARD RULE from 2026-08-08: every new app ships metadata AND in-app UI localized to all 50 App Store locales, keywords researched in Appfigures"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: af304055-c323-4932-95ec-dca1c6b99b7b
  modified: 2026-08-08T16:34:20.483Z
---

**From 2026-08-08 every app must be localized to ALL 50 App Store locales — metadata AND
in-app UI — correctly, no mistakes.** Not a subset, not "top markets".

**The 50 locales Apple accepts** (verified against the installed fastlane: deliver
`ALL_LANGUAGES`, produce's app-creation list, spaceship's languageMapping):

```
ar-SA bn-BD ca cs da de-DE el en-AU en-CA en-GB en-US es-ES es-MX fi fr-CA fr-FR
gu-IN he hi hr hu id it ja kn-IN ko ml-IN mr-IN ms nl-NL no or-IN pa-IN pl pt-BR
pt-PT ro ru sk sl-SI sv ta-IN te-IN th tr uk ur-PK vi zh-Hans zh-Hant
```
29 Latin · 1 Greek · 2 Cyrillic · 4 CJK · 2 Arabic-script (ar, ur) · 1 Hebrew · 1 Thai ·
10 Indic. Four are English variants (en-US/GB/AU/CA) — spelling-level differences only.

**Keywords are the exception to [[keywords-are-user-owned]] for NEW apps.** The user's
instruction: *"You write local search terms, by using claude in chrome with appfigures on
web. I have appfigures subscription… make the localization searches WITHOUT BEING LAZY."*
So: research each locale's keyword field as REAL local-language App Store search terms in
Appfigures — never a literal translation of the English keywords. Still never push
keywords for an ALREADY-SHIPPED app without being asked.

**In-app UI too:** `Localizable.strings` for all 50, not just the store listing. Every new
UI string has to be translated 50 ways.

**Pipeline facts established while scoping this (don't re-derive):**
- `scripts/make_screenshots.py` rendered only 37/50 correctly. SF-Pro-Display covers Latin
  **plus Greek and Cyrillic**; CJK + Arabic had fonts wired. The other 13 (he, th, hi,
  mr, bn, gu, kn, ml, or, pa, ta, te, ur) drew **solid tofu boxes** — proven by rendering a
  sheet and LOOKING at it, not by counting pixels (an ink-count proxy said "renders" for
  every script because tofu boxes have ink).
- Every missing script already has a font on this Mac: SFHebrew, ThonburiUI (th),
  Devanagari Sangam MN (hi/mr), KohinoorBangla, KohinoorGujarati, NotoSansKannada,
  ZitherMalayalam, NotoSansOriya, Gurmukhi MN (pa), ZitherTamil, KohinoorTelugu.
  Urdu needs Nastaliq to look right (GeezaPro renders it in Naskh — legible, not idiomatic).
- Arabic needs `arabic_reshaper` + `bidi` (installed) — `shape()` silently falls back to
  unshaped LTR text if they're missing, which looks wrong rather than obviously broken.
- **Per-locale character limits are the #1 mechanical failure**: name ≤30, subtitle ≤30,
  keywords ≤100, promo ≤170, description ≤4000. German/Finnish/Hungarian blow the 30-char
  name and subtitle constantly. Validate every locale before upload.

Related: [[one-app-per-task]] (this applies to the app being built, not a retrofit of
shipped apps), [[aso-keywords-and-screenshots-rule]].
