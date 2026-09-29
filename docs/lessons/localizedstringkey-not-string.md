---
name: localizedstringkey-not-string
description: "SwiftUI helpers typed `String` silently skip the strings table — labels must be LocalizedStringKey"
metadata: 
  node_type: memory
  type: project
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-22T23:05:42.669Z
---

Every view helper in the template takes `String` for its label (`row(_ title: String,…)`,
`toolRow`, `block`, `point`, `benefitRow`, `step`, `PrimaryButton.title`,
`EmptyStateView.title`, `QuestionStep.title/subtitle/ctaTitle`). `Text(aStringVariable)`
renders **verbatim** — it never looks the value up in `Localizable.strings`. Only
`Text("literal")` becomes a `LocalizedStringKey`.

Result on strobelight (2026-08-23): the app looked localized in German while `RATE`,
`FLASH WIDTH`, `Start strobe` and `120 flashes / min` stayed English, because those go
through helpers. Same trap for `Text(String(format:…))` and `String(localized:)` results
fed back into a `LocalizedStringKey` parameter.

**Why:** the type, not the call site, decides whether a lookup happens.

**How to apply:** when localizing any app in this repo, change label parameters to
`LocalizedStringKey` (call sites with literals need no edit); keep *value* params
(`String(format: "%.1f Hz", …)`, store prices) as `String`. For a runtime string that must
still be looked up, use `Text(LocalizedStringKey(someString))` — that is what
`Option.label` does so the accessibility identifier can stay the English text. Then grep
for `Text(` / `String(localized:` / `title:` literals and diff against
`design/strings_en.json`; the first extraction pass will have missed everything behind a
helper. See [[simctl-launch-args-gotcha]] for verifying the result on screen.

**The harder variant: the key is translated and still never looked up (FreeUp, 2026-09-12).**
`check_strings.py` goes green and the `.strings` file holds a correct translation, so nothing
flags it — only the pixels do. Two shapes, both found in shipped code:

- **One branch of a `String`-returning property localizes and its sibling doesn't.**
  `findingsSummary: String` returned `String(localized: "\(n) found")` on one path and a bare
  `"\(n) found  ·  \(Format.bytes(bytes))"` on the other. The bare branch was the one that
  actually rendered, so `3 found` shipped inside 10 storefronts' screenshots.
- **A `String` param feeding `Text(text)`,** where the *other* call sites happen to pass
  `String(localized:)` results and therefore work. `subordinate(_ text: String)` had three
  working callers and one raw literal.

Audit recipe that finds both — resolve the *declared type*, never eyeball the call:
1. regex every string literal containing `\(` and skip those already inside
   `String(localized:` / `Text(`; then read the enclosing declaration's return type. Interpolation
   into a `LocalizedStringKey` is fine, into a `String` is a bug.
2. regex `Text(<lowercase identifier>)` and resolve that identifier's declared type. `String` /
   `String?` are suspects; then check the *value source* — a `localizedPriceString`, a
   `Format.bytes` number, or an `error.localizedDescription` is correctly unlocalized, and a
   `#if DEBUG` demo renderer is deliberately English.

On FreeUp this reduced 10 + 11 raw hits to exactly 2 real bugs. Fix by wrapping the literal in
`String(localized:)` to match the working siblings — changing the helper's param to
`LocalizedStringKey` would make the already-localized callers look their translated text up as a
key. And re-shoot **every** locale's store frames, not just the new ones: a string that was
English everywhere is baked into every screenshot already live.

