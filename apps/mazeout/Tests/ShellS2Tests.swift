import XCTest
import SwiftUI
import UIKit
import PathCore
@testable import ArrowOut

/// SHELL S2 (SPEC-architecture §12.2 S2). Hosted checks of the HUD, the level popups, the win / unlock / claim presentation:
/// - the HUD intro curves hit SPEC-motion-audio §3.6's beats (drop from −118.4 at K + 1.015 with the ≈ 36 pt overshoot at +0.16,
///   the boosters at K + 1.092, the empty pill until K + 1.339 then the 3.5× pop, the hearts at 1.406 / 1.505 / 1.622), the heart
///   break law (§3.4.5), the Add Time pop, the tutorial hand loop (§6.4) and the unlock beats (§6.3, ui.json values);
/// - the fail chain's layouts follow `ContinueOffer.warning` (CONSISTENCY ID-11: `.none` + hearts = Out of Lives!);
/// - the Streak Race strip: hidden below L30, the multiplier outcome drives its chips, a loss slides back to x1;
/// - the unlock card breaks lines like the phone (040, 134) and highlights the CAPS words without their punctuation;
/// - the celebration logo's part files re-assemble the one-piece logo at rest, in the app's paint order (LOGO-SPEC §5.3);
/// - the HUD write meter counts HUDModel writes; the S2 panels are registered with the popup host;
/// - every S2 frame / text key the code reads is in ui.json.
@MainActor final class ShellS2Tests: XCTestCase {

    private let motion = HUDMotion(Tuning.load(bundle: .main).ui)

    // MARK: HUD intro (SPEC-motion-audio §3.6)

    func testHUDDropBeats() {
        XCTAssertEqual(motion.dropOffset(0), -118.4, accuracy: 1e-9, "hidden above before K + 1.015")
        XCTAssertEqual(motion.dropOffset(1.015), -118.4, accuracy: 1e-6)
        // easeOutBack(3.42): the peak ≈ 36 pt past rest at ≈ +0.16 s (VERIFIED 106 − 68.5 ≈ 37 pt, pause top −49.9 → 106 → 68.5)
        let peakT = (0..<400).map { 1.015 + Double($0) / 400 * 0.334 }.max { motion.dropOffset($0) < motion.dropOffset($1) }!
        XCTAssertEqual(peakT - 1.015, 0.162, accuracy: 0.005)
        XCTAssertEqual(motion.dropOffset(peakT), 35.9, accuracy: 1.5)
        XCTAssertEqual(motion.dropOffset(1.015 + 0.334), 0, accuracy: 1e-9)
        XCTAssertEqual(motion.dropOffset(5), 0)
    }

    func testBoosterSlideAndPops() {
        XCTAssertEqual(motion.boosterOffset(1.092), 88.8, accuracy: 1e-6)
        XCTAssertEqual(motion.boosterOffset(1.092 + 0.209), 0, accuracy: 1e-9)
        XCTAssertNil(motion.timerScale(1.2), "the pill is empty until K + 1.339")
        XCTAssertEqual(motion.timerScale(1.339) ?? 0, 3.5, accuracy: 1e-9)
        XCTAssertEqual(motion.timerScale(1.339 + 0.133) ?? 0, 0.95, accuracy: 1e-6)
        XCTAssertEqual(motion.timerScale(2.0), 1)
        for (i, at) in [1.406, 1.505, 1.622].enumerated() {
            XCTAssertNil(motion.heartScale(i, at - 0.01), "heart \(i + 1) shows the recess before its beat")
            XCTAssertEqual(motion.heartScale(i, at) ?? 0, 1.58, accuracy: 1e-9)
            XCTAssertEqual(motion.heartScale(i, at + 0.133) ?? 0, 0.89, accuracy: 1e-6)
            XCTAssertEqual(motion.heartScale(i, at + 1), 1)
        }
        XCTAssertEqual(motion.introEnd, 1.622 + 0.30, accuracy: 1e-9)
        XCTAssertEqual(motion.addTimeScale(0), 1.3, accuracy: 1e-9)
        XCTAssertEqual(motion.addTimeScale(0.25), 1.0, accuracy: 1e-9)
    }

    func testHeartBreakLaw() {
        // y = −115τ + 480τ² (apex ≈ −6.9 pt at 0.12, +30.8 pt at 0.40), x = ±37.5τ, tilt 25° by 0.12 then 40° by 0.40, fade 0.30 → 0.40
        let a = motion.heartHalf(0.12, side: -1), b = motion.heartHalf(0.40, side: 1)
        XCTAssertEqual(a.dy, -115 * 0.12 + 480 * 0.0144, accuracy: 1e-9)
        XCTAssertEqual(a.dy, -6.9, accuracy: 0.05)
        XCTAssertEqual(b.dy, 30.8, accuracy: 0.05)
        XCTAssertEqual(a.dx, -4.5, accuracy: 1e-9)
        XCTAssertEqual(b.dx, 15.0, accuracy: 1e-9)
        XCTAssertEqual(a.degrees, -25, accuracy: 1e-9)
        XCTAssertEqual(b.degrees, 40, accuracy: 1e-9)
        XCTAssertEqual(motion.heartHalf(0.30, side: 1).opacity, 1)
        XCTAssertEqual(motion.heartHalf(0.35, side: 1).opacity, 0.5, accuracy: 1e-9)
        XCTAssertEqual(motion.heartHalf(0.40, side: 1).opacity, 0)
    }

    // MARK: tutorial + unlock (SPEC-motion-audio §6.3, §6.4)

    func testTutorialHandLoop() {
        let m = TutorialMotion(Tuning.load(bundle: .main).ui)
        XCTAssertEqual(m.captionScale(0), 0.7, accuracy: 1e-9)
        XCTAssertEqual(m.captionScale(0.08), 1.10, accuracy: 1e-9)
        XCTAssertEqual(m.captionScale(0.3), 1.0)
        XCTAssertEqual(m.handScale(0), 0.24, accuracy: 1e-9)
        XCTAssertEqual(m.handScale(0.28), 1.0, accuracy: 1e-9)
        XCTAssertEqual(m.handScale(0.56), 1.0, accuracy: 1e-9, "the first press starts 0.56 s after the hand appears")
        XCTAssertEqual(m.handScale(0.56 + 0.48), 0.53, accuracy: 1e-6)
        XCTAssertEqual(m.handScale(0.56 + 0.48 + 0.36), 1.0, accuracy: 1e-6)
        XCTAssertEqual(m.handScale(0.56 + 2.10 + 0.48), 0.53, accuracy: 1e-6, "period 2.10 s")
    }

    func testUnlockBeatsFollowUIJSON() {
        let t = UnlockTiming(Tuning.load(bundle: .main).ui)
        // CONSISTENCY T-25: SPEC-motion-audio §6.3 wins (ui.json unlock.*)
        XCTAssertEqual(t.b.icon, 0.26); XCTAssertEqual(t.b.iconSettle, 0.54); XCTAssertEqual(t.b.title, 0.50)
        XCTAssertEqual(t.b.unlocked, 0.62); XCTAssertEqual(t.b.card, 0.78); XCTAssertEqual(t.b.sparkles, 1.14)
        // SPEC.md §5 item 42 (contract amend 4; motion-catalog §6.7, measured on v552): the dismiss cuts the content in one frame
        // and fades the dim linearly over 0.233 s (was a 0.16 s fade of everything) — the same exact-value strength
        XCTAssertEqual(t.dismissFade, 0.233); XCTAssertEqual(t.b.dismissMode, .contentCut); XCTAssertEqual(t.acceptFrom, 0.94)
        XCTAssertNil(t.icon(0.25))
        XCTAssertEqual(t.icon(0.26 + 0.16) ?? 0, 1.3, accuracy: 1e-9)
        XCTAssertEqual(t.icon(0.54) ?? 0, 1.0, accuracy: 1e-9)
        XCTAssertNil(t.title(0.49))
        XCTAssertEqual(t.title(0.50) ?? 0, 0.2, accuracy: 1e-9)
        XCTAssertEqual(t.title(0.62) ?? 0, 1.15, accuracy: 1e-9)
        XCTAssertEqual(t.unlocked(0.70) ?? 0, 1.0, accuracy: 1e-9)
        XCTAssertEqual(t.card(0.90) ?? 0, 1.12, accuracy: 1e-9)
        XCTAssertEqual(t.card(0.94) ?? 0, 1.0, accuracy: 1e-9)
    }

    /// FIX-2 lane B (F-16): the EN unlock cards break where the phone's do, at the width each card uses (UnlockCardLines.width):
    /// Corner "Arrows turn when they hit / the CORNER!" (S2-L070 ref, line 1 ink 274.3 pt), Pipe (040), Box (134), Elevator (712)
    /// as measured; Linked and Door (no phone card shot) keep the breaks they had at 272 pt.
    func testUnlockCardBreaksMatchThePhone() {
        let style = GameTextStyle.s2(22.3, -0.66, [0x002E32])
        let cards: [(String, String, [[String]])] = [
            ("corner", "Arrows turn when they hit the CORNER!", [["Arrows", "turn", "when", "they", "hit"], ["the", "CORNER!"]]),
            ("pipe", "Pass arrows through the PIPE to break it!", [["Pass", "arrows", "through", "the"], ["PIPE", "to", "break", "it!"]]),
            ("box", "Clear required amount of arrows to break the BOX!", [["Clear", "required", "amount", "of"], ["arrows", "to", "break", "the", "BOX!"]]),
            ("elevator", "Clear all arrows on the ELEVATOR to activate it!", [["Clear", "all", "arrows", "on", "the"], ["ELEVATOR", "to", "activate", "it!"]]),
            ("linked", "LINKED ARROWS move together!", UnlockCardLines.lines("LINKED ARROWS move together!", style: style, width: 272)),
            ("door", "Collect the KEY to open the DOOR!", UnlockCardLines.lines("Collect the KEY to open the DOOR!", style: style, width: 272)),
        ]
        for (feature, text, want) in cards {
            let w = UnlockCardLines.width(feature: feature, base: 272)
            XCTAssertEqual(UnlockCardLines.lines(text, style: style, width: w), want, feature)
            XCTAssertEqual(UnlockCardLines.fit(text, style: style, width: w).scale, 1, "\(feature) at full size")
        }
        XCTAssertEqual(UnlockCardLines.width(feature: "corner", base: 272), 285)
        XCTAssertLessThanOrEqual(UnlockCardLines.width(feature: "corner", base: 272), 286, "inside the 286 pt cream")
        // negative control: at the old 272 pt the Corner card broke one word earlier than the phone
        XCTAssertEqual(UnlockCardLines.lines("Arrows turn when they hit the CORNER!", style: style, width: 272).first?.last, "they")
    }

    func testUnlockCardLinesAndCaps() {
        let style = GameTextStyle.s2(22.3, -0.66, [0x231C67])   // the shipped card style (UnlockCard)
        XCTAssertEqual(UnlockCardLines.lines("Pass arrows through the PIPE to break it!", style: style, width: 272),
                       [["Pass", "arrows", "through", "the"], ["PIPE", "to", "break", "it!"]], "VERIFIED 040")
        XCTAssertEqual(UnlockCardLines.lines("Clear required amount of arrows to break the BOX!", style: style, width: 272),
                       [["Clear", "required", "amount", "of"], ["arrows", "to", "break", "the", "BOX!"]], "VERIFIED 134")
        XCTAssertTrue(MultiRunText.isCaps("BOX!")); XCTAssertTrue(MultiRunText.isCaps("KAPIYI")); XCTAssertTrue(MultiRunText.isCaps("ASANSÖRÜ"))
        XCTAssertFalse(MultiRunText.isCaps("to")); XCTAssertFalse(MultiRunText.isCaps("A")); XCTAssertFalse(MultiRunText.isCaps("!"))
        XCTAssertEqual(RunsText.split("You will lose 100 token", "100").map(\.0), ["You will lose ", "100", " token"])
        XCTAssertEqual(RunsText.split("100 jetonu ve", "100").map(\.1), [false, true, false])
    }

    /// FIX-V2 F-02: every shipped card fits the 272 pt box in EN and TR — the phone's greedy breaks at full size where they fit
    /// (040 / 134 stay unscaled), else the balanced break with one shrink ≥ 0.70 (the TR Elevator line ran past both edges).
    func testUnlockCardsFitTheBoxInBothLanguages() {
        let style = GameTextStyle.s2(22.3, -0.66, [0x231C67])
        let cards = ["LINKED ARROWS move together!", "BAĞLI OKLAR birlikte hareket eder!",
                     "Clear required amount of arrows to break the BOX!", "KUTUYU kırmak için gereken sayıda oku temizle!",
                     "Pass arrows through the PIPE to break it!", "BORUYU kırmak için okları içinden geçir!",
                     "Clear all arrows on the ELEVATOR to activate it!", "ASANSÖRÜ çalıştırmak için üstündeki tüm okları temizle!",
                     "Collect the KEY to open the DOOR!", "KAPIYI açmak için ANAHTARI topla!",
                     "Arrows turn when they hit the CORNER!", "Oklar KÖŞEYE çarpınca döner!"]
        for text in cards {
            let fit = UnlockCardLines.fit(text, style: style, width: 272)
            XCTAssertLessThanOrEqual(fit.lines.count, 2, text)
            XCTAssertGreaterThanOrEqual(fit.scale, 0.70, text)
            XCTAssertLessThanOrEqual(fit.scale, 1.0, text)
            XCTAssertEqual(fit.lines.flatMap { $0 }.joined(separator: " "), text, "no word lost or reordered")
            let st = style.sized(style.size * fit.scale)
            for line in fit.lines {
                let w = GameTextLayout.make(line.joined(separator: " "), postScriptName: st.postScriptName, size: st.size,
                                            tracking: st.tracking).advance
                XCTAssertLessThanOrEqual(w, 272.5, "\(text): '\(line.joined(separator: " "))' is \(w) pt")
            }
        }
        XCTAssertEqual(UnlockCardLines.fit("Pass arrows through the PIPE to break it!", style: style, width: 272).scale, 1, "VERIFIED 040")
        XCTAssertEqual(UnlockCardLines.fit("Clear required amount of arrows to break the BOX!", style: style, width: 272).scale, 1,
                       "VERIFIED 134")
        let tr = UnlockCardLines.fit("ASANSÖRÜ çalıştırmak için üstündeki tüm okları temizle!", style: style, width: 272)
        XCTAssertLessThan(tr.scale, 1, "the TR Elevator card needs the shrink")
    }

    // MARK: the fail chain and the strip

    func testContinueVariantsFollowTheWarning() {
        let time = ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30))
        let hearts = ContinueOffer(kind: .outOfHearts, step: 0, price: 900, grant: .refillHearts(3))
        let token = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .token)
        let life = ContinueOffer(kind: .outOfHearts, step: 2, price: 900, grant: .refillHearts(3), warning: .life, isLast: true)
        XCTAssertEqual(ContinuePopup.variant(time, clawRunning: true), .time)
        XCTAssertEqual(ContinuePopup.variant(hearts, clawRunning: false), .hearts, "CONSISTENCY ID-11: hearts-out = Out of Lives!")
        XCTAssertEqual(ContinuePopup.variant(token, clawRunning: true), .token)
        XCTAssertEqual(ContinuePopup.variant(token, clawRunning: false), .streak, "SPEC-ui §2.6.3: no Claw → the streak layout")
        XCTAssertEqual(ContinuePopup.variant(life, clawRunning: true), .life)
    }

    func testStreakStripData() {
        let steps = [1, 5, 10, 25, 100]
        XCTAssertNil(StreakStripSource.data(steps: steps, step: 2, level: 29, unlock: 30, outcomes: [], lost: false, timeLeft: "1h"),
                     "no strip before the Streak Race unlock (L30)")
        let win = StreakStripSource.data(steps: steps, step: 2, level: 34, unlock: 30, outcomes: [.multiplier(from: 5, to: 10)],
                                          lost: false, timeLeft: "8h 39m")
        XCTAssertEqual(win?.from, 1); XCTAssertEqual(win?.to, 2)
        let loss = StreakStripSource.data(steps: steps, step: 3, level: 62, unlock: 30, outcomes: [], lost: true, timeLeft: "9h 16m")
        XCTAssertEqual(loss?.from, 3); XCTAssertEqual(loss?.to, 0, "Level Failed slides the lit chip back to x1")
        // FIX-2 B (L28): the strip's countdown is the ONE event formatter now (EventCountdown was a second copy of it)
        XCTAssertEqual(Countdown.text(9 * 3600 + 16 * 60 + 30), "9h 16m")
        XCTAssertEqual(Countdown.text(3 * 86_400 + 5 * 3600), "3d 5h")
        XCTAssertEqual(ClaimItem.duration(1800), "30m")
        XCTAssertEqual(ClaimItem.duration(3600), "1h")
        XCTAssertEqual(ClaimItem.items(Grant(coins: 200, unlimitedLives: 1800)).count, 2)
    }

    func testS2PanelsAreRegistered() {
        let pay: PayAction = { false }
        let offer = ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30))
        let requests: [PopupRequest] = [.outOfTime(offer, pay: pay), .continueOffer(offer, pay: pay), .levelFailed(levels: [32], reason: .timeUp),
                                        .winPanel(WinSummary(levels: [32], reward: 20, tag: .normal)), .unlockOverlay(.pipe), .claimReward(.coins(200))]
        for r in requests {
            XCTAssertTrue(PopupContent.hasPanel(r), "\(r.id.rawValue) has its S2 panel")
            XCTAssertFalse(PopupContent.isPage(r), "\(r.id.rawValue) is a popup on the reference canvas")
        }
        XCTAssertEqual(PopupContent.containerID(.continueOffer(offer, pay: pay)), "popup.continue")
        XCTAssertEqual(PopupContent.containerID(.winPanel(WinSummary(levels: [1], reward: 1, tag: .normal))), "popup.win")
    }

    // MARK: the celebration logo parts and the HUD meter

    /// LOGO-IMPL (SPEC.md ruling 35: replaces testLogoSplitRecomposesTheLogo — the colour-key split no longer exists): every
    /// part file decodes; the letters sit left → right inside the blue sign, the glyphs inside the arrow sign; and the stack AS
    /// THE APP COMPOSES IT AT REST (LogoParts' tree, its paint order, flats and echo hidden) re-assembles logoArrowOut —
    /// CoreGraphics at logoArrowOut's own 918 × 708 px (8-bit sRGB, premultipliedLast, `.medium`), each file drawn into its
    /// logo_rect. Bound (LOGO-SPEC §5.3, from the measured shipped stack, build/logo/art4/reassembly_cg*.json: max 61, 64 px > 41,
    /// p99.9 26): max ≤ 90/255, px > 41/255 ≤ 160, p99.9 ≤ 32/255 — every layer is filtered on its own, so the joins conflate
    /// (≈ 25/255 p99.9, rounds 2-3 alike) and the one-piece was Lanczos-filtered; a wrong stack is far outside it (OUT! Ext over
    /// the Faces max 120 / 852 px > 41; a pair 1 px off max 197-229; a letter missing 248; per-letter containers 449 px > 41).
    func testLogoPartsRecomposeTheLogo() throws {
        let file = Tuning.load(bundle: .main).ui.file
        let spec = try XCTUnwrap(LogoSpec(file))
        let parts = try XCTUnwrap(LogoParts.make(file))
        XCTAssertEqual(parts.mode, .pairs)
        for id in spec.layers.values.flatMap(\.contents) {
            XCTAssertNotNil(ArtStore.image(try XCTUnwrap(UIArt(rawValue: id), id))?.cgImage, "\(id) decodes")
        }
        // letters left → right inside the blue sign, glyphs inside the arrow sign (logo_rect, a 0.01 margin)
        let blue = try XCTUnwrap(spec.layers["logoSignBlue"]).logoRect, purple = try XCTUnwrap(spec.layers["logoSignPurple"]).logoRect
        let letters = LogoSpec.arrowOrder.map { spec.layers[$0 + "Face"]!.logoRect }
        XCTAssertEqual(letters.map(\.midX), letters.map(\.midX).sorted(), "A R R O W")
        for r in letters { XCTAssertTrue(blue.insetBy(dx: -0.01, dy: -0.01).contains(r), "\(r)") }
        for id in LogoSpec.outOrder { XCTAssertTrue(purple.insetBy(dx: -0.01, dy: -0.01).contains(spec.layers[id + "Face"]!.logoRect), id) }
        // the app's paint order at rest, read from the BUILT layer tree (siblings by zPosition, table L's per-layer z; orchestrator
        // note 19:56), without the layers hidden at rest (the flats, the echo)
        var registry: [(node: LogoParts.Node, layer: CALayer)] = []
        let tree = parts.build(t0: 1000, into: &registry)
        let nodeOf = Dictionary(uniqueKeysWithValues: registry.map { (ObjectIdentifier($0.layer), $0.node) })
        var order: [String] = []
        func walk(_ l: CALayer) {
            guard let n = nodeOf[ObjectIdentifier(l)], n.name != "outEcho" else { return }
            if n.image != nil && n.slot != "flat" { order.append(n.name) }
            let kids = (l.sublayers ?? []).enumerated().sorted { ($0.element.zPosition, $0.offset) < ($1.element.zPosition, $1.offset) }
            for k in kids { walk(k.element) }
        }
        walk(tree)
        for id in LogoSpec.arrowOrder + LogoSpec.outOrder {
            let z = registry.filter { $0.node.part == id && ($0.node.slot == "ext" || $0.node.slot == "face") }.map { $0.layer.zPosition }
            XCTAssertEqual(Set(z).count, 2, "\(id): its Ext and Face never share one z")
        }
        let l = ["A", "R1", "R2", "O", "W"], o = ["O", "U", "T", "Bang"]
        XCTAssertEqual(order, ["logoSignPurple", "logoPegs", "logoSignBlue"] + l.map { "logoLetter\($0)Ext" } + l.map { "logoLetter\($0)Face" }
                       + o.map { "logoOut\($0)Ext" } + o.map { "logoOut\($0)Face" })
        let whole = try XCTUnwrap(ArtStore.image(.logoArrowOut)?.cgImage)
        let W = whole.width, H = whole.height
        XCTAssertEqual([W, H], [918, 708])
        func context() throws -> CGContext {
            let c = try XCTUnwrap(CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: W * 4,
                                            space: try XCTUnwrap(CGColorSpace(name: CGColorSpace.sRGB)),
                                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
            c.interpolationQuality = .medium
            return c
        }
        let stack = try context(), ref = try context()
        for id in order {
            let r = try XCTUnwrap(spec.layers[id]).logoRect
            let img = try XCTUnwrap(parts.images[id])
            stack.draw(img, in: CGRect(x: r.minX * Double(W), y: Double(H) - r.maxY * Double(H), width: r.width * Double(W), height: r.height * Double(H)))
        }
        ref.draw(whole, in: CGRect(x: 0, y: 0, width: W, height: H))
        let a = try XCTUnwrap(stack.data).bindMemory(to: UInt8.self, capacity: W * H * 4)
        let b = try XCTUnwrap(ref.data).bindMemory(to: UInt8.self, capacity: W * H * 4)
        var hist = [Int](repeating: 0, count: 256)
        for i in 0..<(W * H) {
            var d = 0
            for ch in 0..<4 { d = max(d, abs(Int(a[i * 4 + ch]) - Int(b[i * 4 + ch]))) }
            hist[d] += 1
        }
        let maxD = hist.lastIndex { $0 > 0 } ?? 0
        let over41 = hist[42...].reduce(0, +)
        var acc = 0, p999 = 0
        for (v, n) in hist.enumerated() { acc += n; if Double(acc) >= 0.999 * Double(W * H) { p999 = v; break } }
        print("[logo] re-assembly at rest: max \(maxD), px > 41: \(over41), p99.9 \(p999)")
        XCTAssertLessThanOrEqual(maxD, 90, "max |stack − logoArrowOut| /255")
        XCTAssertLessThanOrEqual(over41, 160, "pixels > 41/255")
        XCTAssertLessThanOrEqual(p999, 32, "p99.9 /255")
    }

    func testHUDWriteMeterCountsWrites() async {
        let hud = HUDModel()
        let meter = HUDWriteMeter(hud)
        meter.start()
        hud.timerText = "2:59"
        for _ in 0..<5 { await Task.yield() }
        hud.timerText = "2:58"
        hud.coins = 20
        for _ in 0..<5 { await Task.yield() }
        meter.stop()
        XCTAssertEqual(meter.byField["timerText"], 2)
        XCTAssertEqual(meter.byField["coins"], 1)
        XCTAssertEqual(meter.writes, 3)
    }

    // MARK: the data

    func testUIJSONCarriesTheS2Keys() {
        let t = Tuning.load(bundle: .main).ui.tokens
        for id in ["hud.coinPill", "hud.coinIcon", "hud.backButton", "hud.panel", "hud.levelTab", "hud.timerPill", "hud.stopwatch", "hud.heart1",
                   "hud.heart2", "hud.heart3", "hud.pauseButton", "booster.trayLeft", "booster.trayRight", "booster.buttonLeft",
                   "booster.buttonRight", "booster.iconLeft", "booster.iconRight", "booster.badgeLeft", "booster.badgeRight",
                   "outOfTime.stopwatch", "outOfTime.addTimeFace", "outOfTime.addTime", "outOfTime.coinGroup", "outOfTime.closeDisc",
                   "outOfLives.heart", "outOfLives.addLives", "outOfLives.addFrame", "continue.band", "continueStreak.ribbon",
                   "continueStreak.chips", "continueStreak.playOn", "continueToken.token", "continueToken.chips", "continueLife.brokenHeart",
                   "failed.panel", "failed.card", "failed.brokenHeart", "failed.tryAgain", "win.panel", "winHard.panel", "win.continue",
                   "win.ribbon", "winHard.tagRibbon", "streakRace.band", "streakRace.chips", "streakRace.timerChip", "streakRace.logo",
                   "raceBar.band", "raceBar.plate", "raceBar.timer", "unlock.card", "claim.heart", "claimCoins.coins", "claimBulb.icon"] {
            XCTAssertNotEqual(t.frame(id, .zero), .zero, "frames.\(id)")
        }
        XCTAssertEqual(t.frame("hud.panel", .zero), CGRect(78.4, 60.4, 236.5, 59.4), "uim hud.panel (VERIFIED 003)")
        XCTAssertEqual(t.anchor("hud.panel", .centre), .top)
        XCTAssertEqual(t.anchor("booster.trayLeft", .centre), .bottom)
        for id in ["win.perfect.title", "win.rewardsLabel.label", "unlock.title.title", "unlock.subtitle.sub", "claim.title.title",
                   "claim.tap.tap", "failed.caption.caption", "continueStreak.message.msg", "continueLife.message.msg", "hud.timerPill.timer",
                   "hud.coinPill.digits", "tutorial.caption"] {
            XCTAssertNotEqual(t.text(id, GameTextStyle(size: -1)).size, -1, "text.\(id)")
        }
        let f = Tuning.load(bundle: .main).ui.file
        // SPEC.md ruling 35 (approved pin change, same exact-equality strength): CONSISTENCY W-2 re-anchored on the wave start —
        // v552's panel at W + 4.034 (LOGO-SPEC §1; W = the clear wave's first frame, 0.125 s before motion.md's W)
        XCTAssertEqual(f.double("win.panelAt", 0), 4.034, "CONSISTENCY W-2 re-anchored on the wave start: v552's panel at W + 4.034 (LOGO-SPEC §1)")
        XCTAssertEqual(f.doubles("win.rockets", []).count, 6, "CONSISTENCY W-4: six rockets")
        XCTAssertFalse(f.has("hud.outOfTimeHold"), "CONSISTENCY T-4: the 0:00 hold is game.json's")
    }
}
