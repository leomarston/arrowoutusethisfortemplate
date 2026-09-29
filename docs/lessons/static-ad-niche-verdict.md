---
name: static-ad-niche-verdict
description: 2026-09-05 niche hunt — 4 picks rejected, TV remote is the standing recommendation, and the owner relaxed two hard constraints
metadata:
  type: project
---

Long niche hunt (13 rounds, `docs/AD-NICHE-RESEARCH.md`, 995 lines; summary in
`MARKETING-HANDOFF.md` §7). **Nothing was built and nothing was spent.**

**Owner rejected**, in order: receipt/document scanner ("does not have that paying instinct" —
he was right, it sells convenience), notes/planner, habit tracker, DMV permit prep. Also
measured out: quit-porn recovery (failed the shippable-shape test — every earner sells an AI
companion; the plain offline streak counter **Reboot has 13 ratings**), solitaire (100% static
but MobilityWare/Playstudios/King, ad-monetised), storage cleaner (96% video), hidden camera
(0 static app ads).

**Standing recommendation: Universal TV Remote.** Six in the top-40 grossing US Utilities;
14 apps >2,000 ratings; new entrants keep winning (2024-08→31,549 · 2025-12→5,199 at 4.84★);
a solo dev at 42,758. **$6.99/wk · $39.99/yr.** Fully offline — LAN control (Roku ECP HTTP
:8060, Samsung/LG WebSocket, Sony REST, Vizio) — and we already own the discovery half in
`apps/rfdetector/App/Core/NetScanner.swift` (Bonjour/mDNS). **Hazards:** iPhone has NO IR
blaster so non-smart TVs cannot work — never claim "universal"/"all TVs" (2.3.1); and TV
control cannot be tested in the Simulator (same trap as [[never-ship-stand-in-content]]).

**TWO CONSTRAINTS THE OWNER RELAXED — do not re-litigate:**
1. **4.3 collisions with the existing 28 no longer disqualify a niche.** His explicit call,
   made knowing the account carries 8 rejections and 4.3 risk is account-level.
2. **The no-server rule is relaxed** — he chose this over relaxing the static bar. If a backend
   is actually built, CLAUDE.md's "SUNUCU/BACKEND YOK" and
   [[no-servers-not-no-libraries]] MUST be updated or the next session will refuse.

**Round 14 (frontier sweep, solo — workflow died on the monthly spend limit):** family locator
reopened then killed on honesty (Famio: 45% static, 100% install CTAs, but every ad sells
"find location by phone number", undeliverable); coin identifier 6% static despite CoinSnap's
300k ratings; chair yoga 11%/0 installs; resume dead. **NEW FINALISTS: (1) couples app
(Paired class) — Paired 206,796 ratings at $14.99/mo, page-verified 32% static with a 51-day
honest static ad, Cozy Couples 44k launched 2023-10, PairStreak buying carousels NOW; the
question card IS a one-frame static ad; build = bundled deck + pairing (CKShare may make it
serverless). (2) prayer/daily verse — 42% static, 10/29 install CTAs, real small advertisers.
(3) invoice maker — 45% static but B2B web flows.** Full: AD-NICHE-RESEARCH.md round 14.

**Open question he asked last:** how to run profitable Apple Search Ads — outlined in
`MARKETING-HANDOFF.md` §10 (brand/exact/discovery/competitor split, harvest loop, Custom
Product Pages, AdServices attribution). See [[utility-apps-win-on-aso]] for why ASA and not
Meta. Method: [[ad-library-media-filter]].
