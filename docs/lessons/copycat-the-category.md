---
name: copycat-the-category
description: HARD RULE (2026-09-06) — in a crowded App Store category, copy the leaders' UI/UX/colour/icon conventions; a distinctive identity there is a bug, not a feature
metadata:
  type: feedback
---

The owner rejected `storagecleaner`'s first UI outright — warm archival paper, copper accent, a
"contact sheet" metaphor, the keeper circled instead of the condemned ticked. Their words:
"LOOK AT THE COMPETITRS AND MAKE A COPYCAT, JUST A FUCKING SIMPLE COPYCAT THAT WORKS. COPY ALL THE
SYSTEM, COLOR AND UI. MAKING COPYCAT IS LEGAL SO NO PROBLEM, WE DONT GIVE IT THE SAME NAME. THIS IS
LITERALLY HOW THIS FUCKING CATEGORY WORKS."

**Why:** a user arriving from a search result decides in about a second whether this is the kind of
app they meant to find. In a category where the top eleven apps all look like one another, looking
different is not differentiation — it reads as an app that does not belong there. [[distinctive-ui-not-slop]]
still holds against *default grey SwiftUI*; it does NOT license a bespoke identity in a category
with strong conventions. The two rules resolve as: never look like unstyled SwiftUI, always look
like the category you are competing in.

**How to apply — measure the category, do not eyeball it:**
1. Search the store for every head term; filter to the real competitors; rank by rating count.
2. `curl` every competitor's App Store screenshots AND their 1024px icons.
3. **Sample the pixels.** A small CoreGraphics script over the JPEGs gives exact accent, ground and
   destructive hexes plus how often each is used. Ours came out as the 710k-rating leader's own
   #017FFA on #F0F4FF, not an impression of "blue".
4. Fan out one agent per competitor to READ its screenshots and return a structured teardown
   (palette, type scale, home layout, the review interaction, components, icon language, the store
   screenshot formula), then one synthesis agent to find the convention: where 8 of 11 agree, that
   is the convention and you copy it; where they differ, follow the highest-rated.
5. Recreate icons and illustrations in the same *style* — never ship a competitor's actual artwork.
   Lifting literal assets is the one thing that triggers Guideline 4.1/5.2.

Full worked example, including the eleven-app teardown and every measured value:
`docs/CLEANER-DESIGN.md` §13. See [[storagecleaner-build-state]].
