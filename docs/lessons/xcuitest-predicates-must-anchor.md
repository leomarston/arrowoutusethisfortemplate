---
name: xcuitest-predicates-must-anchor
description: A loose CONTAINS predicate matches the app's own marketing copy, so the test passes while asserting nothing
metadata:
  type: feedback
---

camdetect's network tests matched host rows with
`label CONTAINS 'ports '`. That also matched the locked card's sentence "shows
the ports it answered on" and a paywall benefit line — so the PRO test
(`listed.count > 0`) would have gone green with zero hosts found, and the FREE
test (`rows.count == 0`) failed on marketing copy rather than on leaked data.

A host row is `ports 80, 443` or `192.168.1.5 · ports 80, 443`, so the predicate
must be `label BEGINSWITH 'ports ' OR label CONTAINS '· ports '`.

**Why:** a green test that cannot fail is worse than no test — it is the same
class of defect as [[verify-real-not-mock]] and [[screenshots-verify-content-not-count]].
Prose in the app will collide with any word the feature is about.

**How to apply:** when writing a UI-test predicate, grep the app for the phrase
first. If any static copy matches, anchor with BEGINSWITH or a separator that
only the real data has. Then prove it can fail.
