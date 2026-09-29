---
name: xcuitest-hittable-lies
description: isHittable returns true for an element hidden under a safeAreaInset bar; scroll until it clears the bar
metadata:
  type: project
---

`XCUIElement.isHittable` can report **true for an element sitting underneath a bottom bar**
added with `.safeAreaInset(edge: .bottom)`. The tap then lands on the bar and the button
appears to "do nothing".

Hit on `hearup` 2026-08-21: `preset.lecture` reported `hittable=true` at frame y 790–908 while
the bottom bar's button occupied y 749–802 on an 874-tall window. Three wrong theories were
tried first (hit area, `contentShape`, `-DemoPaywall`); dumping `app.debugDescription` after the
tap gave the answer immediately.

**Test helper that works:**
```swift
private func reveal(_ app: XCUIApplication, _ element: XCUIElement, _ attempts: Int = 8) -> Bool {
    func clear() -> Bool {
        guard element.exists && element.isHittable else { return false }
        let bar = app.buttons["home.listen"]           // the overlaying bar
        guard bar.exists else { return true }
        return element.frame.maxY <= bar.frame.minY
    }
    for _ in 0..<attempts { if clear() { return true }; app.swipeUp() }
    return clear()
}
```

**Two lessons:** when a UI test fails mysteriously, **print `app.debugDescription` and read the
real frames** instead of guessing; and if content hides under a bottom bar, that is also a real
UX smell worth fixing in the layout.

Related: [[interactive-bug-check]], [[appstorage-in-observableobject]]
