import Foundation
import QuartzCore
import PathCore

// GAME G1 (SPEC-architecture §6.5, §8.1 step 4, §8.2, §10.2 "HUD"; SPEC-motion-audio §3.6, §3.7, §4; CONSISTENCY B-6, T-2).
// The ONLY writer of the ◆ HUDModel (HUD views never touch the session). Rules:
//  - ≤ `hud.publishHz` (10) writes per second for the throttled fields: the timer text is written only when the displayed
//    second changes (≈ 1 Hz), `timerFrozen` at most once per tick;
//  - hearts on their event (the contact frame: the rightmost full heart breaks, S2 animates it), coins and boosters on
//    theirs;
//  - NOTHING on a tap frame (§8.2): the first tap's `.timerStarted` only flips `timerFrozen`, and that write waits for the
//    next display-link tick, so the exit's first frame has no SwiftUI layout cost.
// Timer text "m:ss" with no leading zero on the minutes, the value `ceil(remaining)` (C2's `displayedSeconds`).
// Template phase 2: reads only the generic `.meta` events and the session's generic state (clock, hearts); a module without a
// hearts rule (`hearts` nil) shows no hearts.
// Template phase 5: the HUD shows the module's declared widgets (`widgets`, written once at the cut, only when they differ from
// the reference game's timer + hearts); the counters follow `movesChanged` / `goalProgress` on their event, except on a tap
// frame (§8.2), where they wait for the next display-link tick like `.timerStarted`.

@MainActor final class HUDWriter {
    let hud: HUDModel
    /// Seconds between two throttled writes (1 / game.json `hud.publishHz`).
    let minInterval: CFTimeInterval
    /// Every write, by field name (GameControllerTests, the lab's HUD write meter).
    var onWrite: ((String) -> Void)?
    private(set) var writes = 0

    private var lastThrottled: CFTimeInterval = 0
    private var shownSeconds = -1
    private var frozenPending: Bool?
    private var slots = 3
    /// A timer re-arm due at a game time (the stage transition's swap at W + gap, MA §3.7 row 3).
    private var rearm: (at: Double, seconds: Int)?
    /// Counter values that arrived on a tap frame (written on the next tick, §8.2).
    private var movesPending: Int?
    private var goalsPending: [GoalState]?

    init(hud: HUDModel, publishHz: Double) {
        self.hud = hud
        minInterval = 1 / max(1, publishHz)
    }

    /// The level screen's first state (the cut): label, tier, the stage's limit frozen, full hearts, coins, boosters, intro.
    func begin(label: LocalizedStringResource, tag: LevelTag, seconds: Int, hearts: Int?, maxHearts: Int, coins: Int,
               boosters: [BoosterSlotVM], intro: HUDIntroPhase, widgets: [HUDWidget] = [.timer, .hearts]) {
        slots = hearts.map { max(maxHearts, $0, 1) } ?? 0
        movesPending = nil
        goalsPending = nil
        if hud.widgets != widgets { write("widgets") { hud.widgets = widgets } }
        if hud.movesLeft != nil { write("movesLeft") { hud.movesLeft = nil } }
        if !hud.goals.isEmpty { write("goals") { hud.goals = [] } }
        write("levelLabel") { hud.levelLabel = label }
        write("tag") { hud.tag = tag }
        setTimer(seconds, force: true)
        write("timerFrozen") { hud.timerFrozen = true }
        frozenPending = nil
        if let hearts { setHearts(hearts) } else if !hud.hearts.isEmpty { write("hearts") { hud.hearts = [] } }
        write("coins") { hud.coins = coins }
        write("boosters") { hud.boosters = boosters }
        write("introPhase") { hud.introPhase = intro }
        write("isVisible") { hud.isVisible = true }
    }

    /// Step 4 of the fan-out.
    func apply(_ outputs: [SessionOutput], session: any PuzzleSession, onTapFrame: Bool) {
        for o in outputs {
            guard case .meta(let e) = o else { continue }
            switch e {
            case .timerStarted:
                frozenPending = false                                 // next tick (§8.2)
            case .timerArmed(_, let seconds):
                if rearm == nil { setTimer(seconds, force: true) }    // a stage transition re-arms at its swap instead
                frozenPending = true
            case .heartsChanged(let remaining):
                setHearts(remaining)                                  // the contact frame (MA §3.4.5)
            case .continued(let offer):
                if case .refillHearts = offer.grant, let h = session.hearts { setHearts(h) }
                frozenPending = !session.clock.isRunning
            case .timeAdded:
                setTimer(session.clock.displayedSeconds, force: true)
            case .stageLoaded:
                // a stage shows the session's hearts: a reset session's fresh count (sessions.json `hearts: reset`); in a
                // carrying one the count already on the HUD (no write: `setHearts` writes only a change)
                if let h = session.hearts { setHearts(h) }
            case .offer, .won, .lost, .stageCleared:
                frozenPending = true
            case .movesChanged(let left):
                if onTapFrame { movesPending = left } else { setMoves(left) }
            case .goalProgress(let goals):
                if onTapFrame { goalsPending = goals } else { setGoals(goals) }
            default:
                break
            }
        }
    }

    /// Every display-link frame: the timer's displayed second, the pending frozen flag, a due re-arm.
    func tick(session: any PuzzleSession, now: CFTimeInterval, gameTime: Double? = nil) {
        if let r = rearm, let g = gameTime, g >= r.at {
            rearm = nil
            setTimer(r.seconds, force: true)
        }
        // event-driven counters held back from a tap frame (not throttled: at most one write per event)
        if let m = movesPending { movesPending = nil; setMoves(m) }
        if let g = goalsPending { goalsPending = nil; setGoals(g) }
        guard now - lastThrottled >= minInterval else { return }
        var wrote = false
        if rearm == nil {
            let s = session.clock.displayedSeconds
            if s != shownSeconds { setTimer(s, force: false); wrote = true }
        }
        if let f = frozenPending {
            frozenPending = nil
            if hud.timerFrozen != f { write("timerFrozen") { hud.timerFrozen = f }; wrote = true }
        }
        if wrote { lastThrottled = now }
    }

    /// The next stage's limit shows at the board swap (W + stage gap), not at the draw's end.
    func scheduleRearm(atGameTime t: Double, seconds: Int) { rearm = (t, seconds) }

    func setTag(_ t: LevelTag) { if hud.tag != t { write("tag") { hud.tag = t } } }

    func setLabel(_ l: LocalizedStringResource) { write("levelLabel") { hud.levelLabel = l } }

    func setCoins(_ n: Int) { if hud.coins != n { write("coins") { hud.coins = n } } }

    func setBoosters(_ b: [BoosterSlotVM]) { if hud.boosters != b { write("boosters") { hud.boosters = b } } }

    func setIntro(_ p: HUDIntroPhase) { if hud.introPhase != p { write("introPhase") { hud.introPhase = p } } }

    /// The level screen goes away.
    func end() {
        rearm = nil
        frozenPending = nil
        movesPending = nil
        goalsPending = nil
        if hud.isVisible { write("isVisible") { hud.isVisible = false } }
        write("introPhase") { hud.introPhase = .hidden }
    }

    // MARK: fields

    private func setTimer(_ seconds: Int, force: Bool) {
        let s = max(0, seconds)
        guard force || s != shownSeconds else { return }
        shownSeconds = s
        let text = Self.text(s)
        if hud.timerText != text { write("timerText") { hud.timerText = text } }
        if hud.timerSeconds != s { write("timerSeconds") { hud.timerSeconds = s } }
    }

    private func setMoves(_ left: Int) {
        let v = max(0, left)
        if hud.movesLeft != v { write("movesLeft") { hud.movesLeft = v } }
    }

    private func setGoals(_ goals: [GoalState]) {
        if hud.goals != goals { write("goals") { hud.goals = goals } }
    }

    private func setHearts(_ remaining: Int) {
        slots = max(slots, remaining)
        let v: [HeartSlotVM] = (0..<slots).map { $0 < remaining ? .full : .lost }
        if hud.hearts != v { write("hearts") { hud.hearts = v } }
    }

    private func write(_ field: String, _ body: () -> Void) {
        body()
        writes += 1
        onWrite?(field)
    }

    /// "m:ss" with no leading zero on the minutes ("3:00", "0:59", "0:00"; SPEC-motion-audio §4, CONSISTENCY T-2): the timer
    /// pill's formatter (TimerPill.swift `TimerText`, the kit's hud-timer).
    nonisolated static func text(_ seconds: Int) -> String { TimerText.text(seconds) }
}
