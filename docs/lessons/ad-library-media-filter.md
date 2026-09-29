---
name: ad-library-media-filter
description: The competitive-research toolkit — Meta static share, CTA histogram, iTunes earnings, Google's ad library, and the shippable-shape test
metadata:
  type: reference
---

Instruments for judging whether a niche is worth building for. All verified 2026-09-05.

**Meta static share.** The Ad Library API has **no media-type field**; only the web UI does, via
`&media_type=` on a `q=` or `view_all_page_id=` URL. **`image_and_meme` is the COMPLETE static
set** — NOT the union of `image` and `meme`. Proof: `video 230 + image_and_meme 31 ≈ 260` total,
while `image`=3, `meme`=2. Using `image` alone undercounts static ~10x.

**CTA histogram — the key discriminator.** Count exact innerText lines: `İndir`/`Install Now`/
`Download`/`Oyna` = app install; `Daha fazla bilgi al` = web funnel; `Şimdi alışveriş yap` =
ecommerce. (UI renders in the browser locale — Turkish here.) **Never count `APPS.APPLE.COM`
occurrences** — store ads often show a headline instead of a domain, giving false zeros.
This is what separates a real app niche from a course/merch/hardware niche.

**Cheap extraction.** `javascript_tool` on `document.body.innerText` matching `~N sonuç`. Never
pull full page text — enormous context for no extra signal. Keep browser_batch ≤6 actions.

**Earnings.** `curl "https://itunes.apple.com/lookup?id=<id>&country=us"` and
`/search?term=&country=us&entity=software&limit=N` → `userRatingCount`, `releaseDate`,
`sellerName`, `description`. **Use curl — python urllib fails on SSL certs here.**
Top-grossing chart: `itunes.apple.com/us/rss/topgrossingapplications/limit=40/genre=6002/json`
(6002=Utilities) — finds where money is instead of guessing niches.

**THE SHIPPABLE-SHAPE TEST.** Grep each earner's `description` for AI/community/cloud/sync/login:
*do the apps that EARN do so from the shape we're allowed to build?* This killed two
recommendations. iCloud/CloudKit does NOT count as a server (Apple's, free, unmaintained by us).

**Google has a public ad library too** — `adstransparency.google.com`, searchable by advertiser,
identity-verified, with a **format filter (Image/Text/Video)**. Check it alongside Meta always.
**Apple Search Ads has NO public library** — "no Meta ads" never means "no advertising".

**Longevity is a floor.** Results are newest-first; query `ad_active_status: INACTIVE`/`ALL` for
lifetime counts. Never report "longest run across active creatives" as tenure — that measures
creative churn and mislabels 74-day advertisers as burners.

See [[static-ad-niche-verdict]] and [[utility-apps-win-on-aso]].
