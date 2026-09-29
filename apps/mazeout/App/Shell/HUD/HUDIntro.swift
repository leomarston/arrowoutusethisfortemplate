import SwiftUI
import PathCore

// SHELL S2 (SPEC-architecture §6.5 "HUD intro"; SPEC-motion-audio §3.6 rows 6-10, §4, §3.4.5; ui.json `hudIntro.*`, `hud.*`).
// Pure functions of time (seconds from the level-start cut K) for the HUD's motion, so a TimelineView on the MotionClock can
// draw any instant (slow motion, `-pc.freezeAt hudIntro@t` captures) and a unit test can check every beat:
//   K + 1.015   the top row (coin group, back, panel + "Level N" tab + timer pill + hearts, pause) drops from −118.4 pt,
//               easeOutBack(3.42) over 0.334 s (peak ≈ 37 pt past rest at +0.16)
//   K + 1.092   the booster corners slide in from ∓88.8 pt, easeOutBack(2.57) over 0.209 s
//   K + 1.015 … 1.339  the timer pill shows an EMPTY bar, the heart slots the empty recess
//   K + 1.339   the timer text pops (kf 3.5 → 1.42 → … → 1.0 over 0.25 s)
//   K + 1.406 / 1.505 / 1.622  heart 1, 2, 3 pop (kf 1.58 → 0.89 → 1.04 → 1.0 over 0.30 s)
// `HUDIntroPhase.playing(start:)` carries K in MotionClock game seconds (GAME's HUDWriter writes it at the cut).

struct HUDMotion: Equatable {
    var startAfterCut = 1.015
    var dropPt = 118.4
    var dropDur = 0.334
    var dropBack = 3.42
    var boosterDelay = 0.077
    var boosterPt = 88.8
    var boosterDur = 0.209
    var boosterBack = 2.57
    var bigTimerAt = 1.339
    var bigTimerKf: [Double] = [0, 3.5, 0.067, 1.42, 0.083, 1.31, 0.10, 1.17, 0.133, 0.95, 0.167, 0.88, 0.20, 0.96, 0.25, 1.0]
    var heartsAt: [Double] = [1.406, 1.505, 1.622]
    var heartKf: [Double] = [0, 1.58, 0.05, 1.36, 0.10, 0.93, 0.133, 0.89, 0.167, 0.96, 0.20, 1.04, 0.25, 1.02, 0.30, 1.0]
    /// Add Time (+30 sec): the timer text pops `addTimePop[0]` → 1.0 over `addTimePop[1]` s, easeOutBack(1.70).
    var addTimePop: [Double] = [1.3, 0.25]
    /// Add Lives (+3): the hearts re-pop left → right with `heartKf`, `refillStagger` apart.
    var refillStagger = 0.10
    var heartBreak = HeartBreak()

    struct HeartBreak: Equatable {
        var v0 = -115.0          // pt/s, up
        var g = 960.0            // pt/s²
        var vx = 37.5            // pt/s, each half outwards
        var rot1 = 25.0          // degrees reached at τ 0.12
        var rot2 = 40.0          // degrees at τ 0.40
        var rotKnee = 0.12
        var fadeFrom = 0.30
        var fadeTo = 0.40
    }

    init() {}

    init(_ ui: UITuning) {
        let f = ui.file
        startAfterCut = f.double("hudIntro.startAfterCut", startAfterCut)
        dropPt = f.double("hudIntro.dropPt", dropPt)
        dropDur = f.double("hudIntro.dropDur", dropDur)
        dropBack = f.double("hudIntro.dropBack", dropBack)
        boosterDelay = f.double("hudIntro.boosterDelay", boosterDelay)
        boosterPt = f.double("hudIntro.boosterPt", boosterPt)
        boosterDur = f.double("hudIntro.boosterDur", boosterDur)
        boosterBack = f.double("hudIntro.boosterBack", boosterBack)
        bigTimerAt = f.double("hudIntro.bigTimerAt", bigTimerAt)
        bigTimerKf = Self.pairs(f.doubles("hudIntro.bigTimerKf", bigTimerKf), bigTimerKf)
        let hearts = f.doubles("hudIntro.heartsAt", heartsAt)
        heartsAt = hearts.count >= 3 ? hearts : heartsAt
        heartKf = Self.pairs(f.doubles("hudIntro.heartKf", heartKf), heartKf)
        let pop = f.doubles("hud.addTimePop", addTimePop)
        addTimePop = pop.count == 2 ? pop : addTimePop
        refillStagger = f.double("hud.refillStagger", refillStagger)
        heartBreak.v0 = f.double("hud.heartBreak.v0", heartBreak.v0)
        heartBreak.g = f.double("hud.heartBreak.g", heartBreak.g)
        heartBreak.vx = f.double("hud.heartBreak.vx", heartBreak.vx)
        heartBreak.rot1 = f.double("hud.heartBreak.rot1", heartBreak.rot1)
        heartBreak.rot2 = f.double("hud.heartBreak.rot2", heartBreak.rot2)
        heartBreak.fadeFrom = f.double("hud.heartBreak.fadeFrom", heartBreak.fadeFrom)
        heartBreak.fadeTo = f.double("hud.heartBreak.fadeTo", heartBreak.fadeTo)
    }

    /// A flat [t0, v0, t1, v1, …] list with strictly increasing times, else the default.
    private static func pairs(_ v: [Double], _ d: [Double]) -> [Double] {
        guard v.count >= 4, v.count % 2 == 0 else { return d }
        var last = -Double.infinity
        for i in stride(from: 0, to: v.count, by: 2) {
            guard v[i] > last else { return d }
            last = v[i]
        }
        return v
    }

    static func track(_ flat: [Double]) -> KeyTrack {
        KeyTrack(stride(from: 0, to: flat.count - 1, by: 2).map { (flat[$0], flat[$0 + 1]) })
    }

    // MARK: the intro (t = seconds since K)

    /// The top row's y offset in pt (negative = above its rest).
    func dropOffset(_ t: Double) -> Double {
        let u = (t - startAfterCut) / dropDur
        if u <= 0 { return -dropPt }
        if u >= 1 { return 0 }
        return -dropPt * (1 - Easing.outBack(u, s: dropBack))
    }

    /// The booster corners' horizontal offset magnitude in pt (left moves by −value, right by +value).
    func boosterOffset(_ t: Double) -> Double {
        let u = (t - startAfterCut - boosterDelay) / boosterDur
        if u <= 0 { return boosterPt }
        if u >= 1 { return 0 }
        return boosterPt * (1 - Easing.outBack(u, s: boosterBack))
    }

    /// The timer text's scale, or nil while the pill is still empty.
    func timerScale(_ t: Double) -> Double? {
        let tr = Self.track(bigTimerKf)
        let u = t - bigTimerAt
        if u < 0 { return nil }
        return u >= tr.end ? 1 : tr(u)
    }

    /// Heart slot `i`'s pop scale, or nil while the slot is still the empty recess.
    func heartScale(_ i: Int, _ t: Double) -> Double? {
        guard i >= 0 else { return 1 }
        let at = i < heartsAt.count ? heartsAt[i] : (heartsAt.last ?? 1.6) + Double(i - heartsAt.count + 1) * 0.11
        let tr = Self.track(heartKf)
        let u = t - at
        if u < 0 { return nil }
        return u >= tr.end ? 1 : tr(u)
    }

    /// The instant after which every intro value is at rest.
    var introEnd: Double {
        let timer = bigTimerAt + (Self.track(bigTimerKf).end)
        let hearts = (heartsAt.last ?? 0) + Self.track(heartKf).end
        return max(startAfterCut + dropDur, startAfterCut + boosterDelay + boosterDur, timer, hearts)
    }

    // MARK: one-shots (t = seconds since the event)

    /// The Add Time pop of the timer text.
    func addTimeScale(_ t: Double) -> Double {
        let from = addTimePop[0], dur = max(0.001, addTimePop[1])
        if t <= 0 { return from }
        if t >= dur { return 1 }
        return from + (1 - from) * Easing.outBack(t / dur, s: 1.70158)
    }

    /// Heart `i`'s re-pop after Add Lives (+3), or nil before its start.
    func refillScale(_ i: Int, _ t: Double) -> Double? {
        let u = t - Double(i) * refillStagger
        if u < 0 { return nil }
        let tr = Self.track(heartKf)
        return u >= tr.end ? 1 : tr(u)
    }

    var refillEnd: Double { 2 * refillStagger + Self.track(heartKf).end }

    /// One half of a breaking heart τ s after the bump contact (left: side −1, right: +1).
    func heartHalf(_ tau: Double, side: Double) -> (dx: Double, dy: Double, degrees: Double, opacity: Double) {
        let b = heartBreak
        let t = max(0, tau)
        let dy = b.v0 * t + 0.5 * b.g * t * t
        let dx = side * b.vx * t
        let rot: Double
        if t <= b.rotKnee {
            rot = b.rot1 * t / b.rotKnee
        } else {
            rot = b.rot1 + (b.rot2 - b.rot1) * min(1, (t - b.rotKnee) / max(0.001, b.fadeTo - b.rotKnee))
        }
        let opacity: Double = t <= b.fadeFrom ? 1 : max(0, 1 - (t - b.fadeFrom) / max(0.001, b.fadeTo - b.fadeFrom))
        return (dx, dy, side * rot, opacity)
    }

    var heartBreakEnd: Double { heartBreak.fadeTo }
}

extension UITuning {
    var hudMotion: HUDMotion { HUDMotion(self) }
}
