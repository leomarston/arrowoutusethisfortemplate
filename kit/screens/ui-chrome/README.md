# UI chrome kit (`ui-chrome`)

Shared drawn-in-code chrome: popup panels, ribbons, cards, toggles, page headers, band popups, glossy buttons.

The building blocks every popup and page is drawn with, at the measured frames and from skin tokens: PopupPanelFrame, PopupRibbon/PopupTitle, PopupCard, PopupCloseButton, PopupToggle, ChromeButtonFace (PopupChrome.swift); ShellPageHeader, ShellPageBackground, BlueCard, FramedButton, ShellSquareToggle, PillLinkButton, BandPopupFrame (PageChrome.swift); ArtInk, TokenText, RingedText, TierSquareButton, OfferCoinGroup, PriceButton (S2Chrome.swift); and UI-ART's GlossyChrome recipes (art/ui/code).

## How the app uses it

```swift
ZStack(alignment: .topLeading) {
    PopupPanelFrame(n: t.superellipseN("pause.panel", 6.31), t: t).placed(panel)
    PopupCard(radius: t.radius("pause.card", 24.44), t: t).placed(card)
    PopupTitle(title: "Paused", frame: t.frame("pause.ribbon", ribbon), t: t)
    PopupCloseButton(id: "popup.pause.close", t: t) { answer(PopupResult.close) }.placed(close)
}
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab components
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show ui-chrome          # files, what it uses, deps, who depends on it
python3 tools/kit.py export ui-chrome --out /tmp/ui-chrome-kit
python3 tools/kit.py add ui-chrome --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
