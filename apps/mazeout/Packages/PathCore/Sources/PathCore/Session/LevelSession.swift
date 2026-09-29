import Foundation

// C2 (SPEC-architecture §4.5, D7). One Play = one session = 1…n stages ("Levels 1-4" is four boards in ONE session with
// one win, VERIFIED tutorials §2). The state machine:
//
//   start() → .intro(k) ─ack(.introFinished)→ .ready(k) ─first arrow tap (exit OR bump)→ .playing(k)
//   .playing: taps / bumps / obstacles / boosters
//     time 0 (tick) ─────────────────────→ .offer(outOfTime, step 0)
//     hearts 0 (at the bump's CONTACT ack) → .offer(outOfHearts, step 0)
//     last arrow of a non-final stage tapped → .stageClear(k) ─ack(.stageTransitionDone)→ .ready(k+1) (fresh clock)
//     last arrow of the last stage tapped ──→ .won(result)   (win at the TAP: timer stops, input locks)
//   .offer(o) ─acceptContinue→ .playing (+time / hearts) · ─declineContinue→ next step … last → .lost(.timeUp|.hearts)
//   any live phase ─quit()→ .lost(.quit)
//
// Events come back in causal order and GAME forwards them unchanged (§8.1). The core never sleeps or schedules: the board
// reports presentation-timed facts through `ack` (bump contact → the heart; door burst → the door opens; the stage
// transition). A WIN BEATS A FAIL: once won, time cannot run out and a pending bump contact only marks its arrow.
//
// Decisions (tagged in RulesTuning): the stage transition's `.stageTransitionDone` ack covers the next board's build-in,
// so the next stage opens in `.ready` (no second intro ack); a tap on an empty point returns `.tapIgnored(nil, .noArrow)`
// and starts nothing; boosters never start the timer (VERIFIED boosters.md).

public final class LevelSession {
    public let plan: SessionPlan
    public let stages: [LevelSpec]
    public let setup: AttemptSetup
    public let rules: RulesTuning

    public private(set) var phase: Phase
    public private(set) var stage: Int
    public private(set) var board: BoardState
    public private(set) var clock: LevelClock
    public private(set) var hearts: Int
    public private(set) var combo: ComboTracker
    /// true after `start()`.
    public private(set) var started = false
    /// Bumps this session (every bump plan, repeats included) and heart-costing bumps.
    public private(set) var bumps = 0
    public private(set) var heartsLost = 0
    /// Resolved arrow taps (exits + bumps) this session.
    public private(set) var taps = 0
    /// The streak multiplier is above x1: the fail chain includes its "You will lose … your streak!" step (VERIFIED
    /// fail.md §1). GAME sets it from the events state before `start()`.
    public var streakActive = false

    public init(plan: SessionPlan, stages: [LevelSpec], setup: AttemptSetup, rules: RulesTuning = .default) {
        precondition(!stages.isEmpty, "a session needs at least one stage")
        self.plan = plan
        self.stages = stages
        self.setup = setup
        self.rules = rules
        let first = min(max(0, setup.firstStage), stages.count - 1)
        stage = first
        phase = .intro(stage: first)
        board = BoardState(level: stages[first], rules: rules)
        clock = LevelSession.makeClock(stages[first], rules)
        hearts = max(0, stages[first].hearts)
        combo = ComboTracker(window: rules.combo.window, bumpBreaks: rules.combo.bumpBreaks)
    }

    static func makeClock(_ s: LevelSpec, _ rules: RulesTuning) -> LevelClock {
        LevelClock(limit: s.timerSeconds, alerts: rules.clock.alerts,
                   freezeRunsBeforeStart: rules.boosters.freezeRunsBeforeStart)
    }

    public var level: LevelSpec { stages[stage] }
    public var isFinished: Bool {
        switch phase { case .won, .lost: return true; default: return false }
    }
    /// The highest tag of the session's boards.
    public var tag: LevelTag {
        let rank: [LevelTag: Int] = [.normal: 0, .hard: 1, .superHard: 2]
        return stages.map(\.tag).max { rank[$0]! < rank[$1]! } ?? .normal
    }

    // MARK: lifecycle

    /// → `.intro(firstStage)`: the board builds in; the timer shows its limit, frozen.
    public func start() -> [SessionEvent] {
        guard !started else { return [] }
        started = true
        clock.hold(.intro)
        return [.stageLoaded(stage: stage, of: stages.count, level: stages[stage].level)]
    }

    public func ack(_ a: SessionAck) -> [SessionEvent] {
        guard started else { return [] }
        switch a {
        case .introFinished:
            guard case .intro(let k) = phase else { return [] }
            clock.release(.intro)
            phase = .ready(stage: k)
            return [.timerArmed(stage: k, seconds: clock.limit)]
        case .bumpContact(let id):
            return contact(id)
        case .bumpFinished(let id):
            board.ack(.bumpFinished(id))
            return []
        case .doorBurst(let d):
            return board.ack(.doorBurst(d)).compactMap(Self.map)
        case .lastExitLeftBoard:
            return []
        case .stageTransitionDone:
            guard case .stageClear(let k) = phase, k + 1 < stages.count else { return [] }
            let next = k + 1
            stage = next
            board = BoardState(level: stages[next], rules: rules)
            clock = LevelSession.makeClock(stages[next], rules)
            if plan.hearts == .reset { hearts = max(0, stages[next].hearts) }
            phase = .ready(stage: next)
            return [.stageAdvanced(to: next),
                    .stageLoaded(stage: next, of: stages.count, level: stages[next].level),
                    .timerArmed(stage: next, seconds: clock.limit)]
        }
    }

    // MARK: taps

    public func tap(_ arrow: ArrowID?, at t: TimeInterval) -> [SessionEvent] {
        let k: Int
        switch phase {
        case .ready(let s), .playing(let s): k = s
        case .intro, .lost: return [.tapIgnored(arrow, .notPlaying)]
        case .stageClear, .offer, .won: return [.tapIgnored(arrow, .inputLocked)]
        }
        guard started else { return [.tapIgnored(arrow, .notPlaying)] }
        if !clock.holds.isDisjoint(with: rules.session.inputLockingHolds) { return [.tapIgnored(arrow, .inputLocked)] }
        guard let arrow else {
            var ev: [SessionEvent] = []
            if rules.clock.emptyTapStartsTimer { ev += startTimer(k) }
            return ev + [.tapIgnored(nil, .noArrow)]
        }
        let r = board.resolve(tap: arrow)
        switch r {
        case .ignored(let why):
            return [.tapIgnored(arrow, why)]
        case .exit(var plan):
            taps += 1
            var ev = startTimer(k)
            plan.combo = combo.register(tapAt: t, isBump: false)
            ev.append(.exited(plan))
            ev += board.commit(.exit(plan)).compactMap(Self.map)
            if board.isCleared { ev += cleared(k) }
            return ev
        case .bump(let plan):
            taps += 1
            bumps += 1
            var ev = rules.bump.startsTimer ? startTimer(k) : []
            _ = combo.register(tapAt: t, isBump: true)
            ev.append(.bumped(plan))
            board.commit(.bump(plan))
            return ev
        }
    }

    func startTimer(_ k: Int) -> [SessionEvent] {
        guard !clock.started else { return [] }
        clock.startOnFirstTap()
        if case .ready = phase { phase = .playing(stage: k) }
        return [.timerStarted(stage: k)]
    }

    /// The stage's last arrow was tapped (the win is decided at the tap).
    func cleared(_ k: Int) -> [SessionEvent] {
        if k + 1 < stages.count {
            phase = .stageClear(stage: k)
            clock.hold(.stageTransition)
            return [.stageCleared(stage: k)]
        }
        clock.hold(.winSequence)
        let result = WinResult(levels: plan.levels, tag: tag, timeLeft: clock.displayedSeconds, heartsLeft: hearts,
                               firstTry: setup.attemptIndex <= 1, reward: plan.reward ?? rules.rewards.reward(for: tag),
                               bumps: bumps)
        phase = .won(result)
        return [.won(result)]
    }

    /// The board's contact frame: the heart (unless a repeat on a red arrow), the red marks, a possible offer.
    func contact(_ id: ArrowID) -> [SessionEvent] {
        let raw = board.ack(.bumpContact(id))
        var repeatBump = false
        var marks: [SessionEvent] = []
        for e in raw {
            switch e {
            case .bumpContact(_, let rep): repeatBump = rep
            case .arrowMarked(let a): marks.append(.arrowMarked(a))
            default: break
            }
        }
        guard raw.contains(where: { if case .bumpContact = $0 { return true }; return false }) else { return [] }
        let live: Bool
        switch phase { case .ready, .playing: live = true; default: live = false }
        guard live, !repeatBump || rules.bump.repeatOnMarkedCostsHeart else { return marks }
        hearts = max(0, hearts - 1)
        heartsLost += 1
        var ev: [SessionEvent] = [.heartLost(remaining: hearts)]
        ev += marks
        if hearts == 0 { ev += openOffer(.outOfHearts, step: 0) }
        return ev
    }

    // MARK: time

    public func tick(_ dt: Double) -> [SessionEvent] {
        guard started else { return [] }
        var ev: [SessionEvent] = []
        for e in clock.tick(dt) {
            switch e {
            case .freezeEnded: ev.append(.freezeEnded)
            case .alert(let n): ev.append(.timerAlert(.threshold(n)))
            case .expired:
                if case .playing = phase { ev += openOffer(.outOfTime, step: 0) }
            }
        }
        return ev
    }

    public func hold(_ r: HoldReason) { clock.hold(r) }
    public func release(_ r: HoldReason) { clock.release(r) }

    // MARK: fail chain

    /// The chain of `kind` for this session (steps needing a streak dropped when `streakActive` is false).
    public func chain(_ kind: ContinueOffer.Kind) -> [ContinueOffer] { rules.chain(kind, streakActive: streakActive) }

    func openOffer(_ kind: ContinueOffer.Kind, step: Int) -> [SessionEvent] {
        let steps = chain(kind)
        guard step < steps.count else {
            let reason: LossReason = kind == .outOfTime ? .timeUp : .hearts
            phase = .lost(reason)
            clock.hold(.offer)
            return [.lost(reason)]
        }
        let o = steps[step]
        phase = .offer(o)
        clock.hold(.offer)
        return [.offer(o)]
    }

    /// The caller has already charged `offer.price`.
    public func acceptContinue() -> [SessionEvent] {
        guard case .offer(let o) = phase else { return [] }
        var ev: [SessionEvent] = [.continued(o)]
        switch o.grant {
        case .addTime(let s):
            clock.add(s)
            ev.append(.timeAdded(seconds: s, cause: .continueOffer))
        case .refillHearts(let n):
            hearts = max(0, hearts) + max(0, n)
        case .none:
            break
        }
        clock.release(.offer)
        phase = .playing(stage: stage)
        // Still nothing left to play with (a grant that does not fix the cause): the chain goes on.
        if o.kind == .outOfTime && clock.isExpired { ev += openOffer(.outOfTime, step: 0) }
        if o.kind == .outOfHearts && hearts == 0 { ev += openOffer(.outOfHearts, step: 0) }
        return ev
    }

    public func declineContinue() -> [SessionEvent] {
        guard case .offer(let o) = phase else { return [] }
        return openOffer(o.kind, step: o.step + 1)
    }

    public func quit() -> [SessionEvent] {
        guard started, !isFinished else { return [] }
        phase = .lost(.quit)
        clock.hold(.offer)
        return [.lost(.quit)]
    }

    // MARK: boosters (stock is the caller's, §4.9)

    /// The hourglass freezes the clock for `boosters.freezeTotal` (flight + countdown) of RUNNING time from the use (before
    /// the first tap it waits whole, `freezeRunsBeforeStart` false); the bulb shows `hint()`'s greedy unit. The app's
    /// BoosterDirector uses `useBooster(_:hintPolicy:freezeFlightFromUse:)` (SPEC.md rulings 30 + 31).
    public func useBooster(_ b: BoosterID) -> [SessionEvent] {
        use(b, freezeLead: 0) { hint() }
    }

    /// CORE-2, SPEC.md rulings 30 + 31 — the booster entry the app's BoosterDirector calls (only it):
    /// - hourglass with `freezeFlightFromUse`: `clock.freeze(freezeTotal, lead: freezeFlight)` — the flight counts from
    ///   the use (B) even before the first tap and the 10 s countdown from the first tap: a first tap after the flight
    ///   leaves 10 s of freeze, one during it the rest of the flight + 10 s (the countdown ends at B + flight + 10). Once
    ///   the timer has started this is exactly `useBooster(_:)`'s freeze. Without it: `useBooster(_:)`'s freeze.
    /// - bulb: `.hintShown(hint(policy: hintPolicy) ?? [])` (rules.json `boosters.hintPolicy`, SPEC-gameplay §6.3).
    /// Same events, phases and guards as `useBooster(_:)`; neither ever starts the timer.
    public func useBooster(_ b: BoosterID, hintPolicy: RulesTuning.HintPolicy, freezeFlightFromUse: Bool) -> [SessionEvent] {
        use(b, freezeLead: freezeFlightFromUse ? rules.boosters.freezeFlight : 0) { hint(policy: hintPolicy) }
    }

    func use(_ b: BoosterID, freezeLead: Double, hintUnit: () -> [ArrowID]?) -> [SessionEvent] {
        switch phase { case .ready, .playing: break; default: return [] }
        switch rules.boosters.action(b) {
        case .freezeTimer:
            let s = rules.boosters.freezeTotal
            clock.freeze(s, lead: freezeLead)
            return [.boosterUsed(b), .freezeStarted(seconds: s)]
        case .hint:
            return [.boosterUsed(b), .hintShown(hintUnit() ?? [])]
        case .none:
            return []
        }
    }

    /// The first unit of a solvable order from the live board (the HeadlessDriver's solver strategy and `useBooster(_:)`'s
    /// bulb); nil = none free. Stays greedy (SPEC.md ruling 31: no pinned driver test moves).
    public func hint() -> [ArrowID]? { Solver.hintUnit(board) }

    /// SPEC.md ruling 31: the bulb's unit under `policy` (`unblocksMost`, SPEC-gameplay §6.3) from the live board; nil =
    /// none free (a door still opening). Only the app's BoosterDirector calls it.
    public func hint(policy: RulesTuning.HintPolicy) -> [ArrowID]? { Solver.hintUnit(board, policy: policy) }

    // MARK: probe

    public func snapshot() -> SessionSnapshot {
        let name: String
        switch phase {
        case .intro: name = "intro"
        case .ready: name = "ready"
        case .playing: name = "playing"
        case .stageClear: name = "stageClear"
        case .offer: name = "offer"
        case .won: name = "won"
        case .lost: name = "lost"
        }
        return SessionSnapshot(levels: plan.levels, stage: stage, phase: name, remaining: clock.remaining,
                               timerStarted: clock.started, hearts: hearts, live: board.live, free: board.freeUnits(),
                               counters: board.counters, combo: combo.count)
    }

    // MARK: mapping

    static func map(_ e: RuleEvent) -> SessionEvent? {
        switch e {
        case .keyDispatched(let k, let d): return .keyDispatched(key: k, door: d)
        case .doorOpened(let d, let r): return .doorOpened(d, revealed: r)
        case .pipeUsed(let p, let n): return .pipeUsed(p, remaining: n)
        case .pipeBroken(let p): return .pipeBroken(p)
        case .counterChanged(let b, let n): return .counterChanged(b, remaining: n)
        case .counterBroken(let b, let r): return .counterBroken(b, revealed: r)
        case .elevatorActivated(let e, let r): return .elevatorActivated(e, revealed: r)
        case .arrowMarked(let a): return .arrowMarked(a)
        case .bumpContact: return nil
        }
    }
}
