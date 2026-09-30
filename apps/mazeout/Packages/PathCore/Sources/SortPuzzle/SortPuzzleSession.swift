import Foundation
import GameCore

// SortPuzzle behind GameCore's contract (docs/architecture/PUZZLE-MODULE.md §3, §6b). The state machine:
//
//   start() → .intro(k) ─ack(.introFinished)→ .ready(k) ─first selection→ .playing(k)
//   select s (a non-empty tube) → selected · select s again → deselected · select t → pour s → t, or refused (a failed move)
//     the last pour of a non-final stage → .stageClear(k) ─ack(.stageTransitionDone)→ .ready(k+1)
//     the last pour of the last stage ──→ .won(result)   (decided at the pour; the board acks .boardCleared at W)
//     a pour that leaves no legal pour ─→ .offer(stuck, step 0) (the config's chain; default grant: an extra empty tube)
//   .offer(o) ─acceptContinue→ .playing (+ the grant; still stuck → the next step) · ─declineContinue→ next … → .lost(.stuck)
//   any live phase ─quit()→ .lost(.quit)
//
// No timer and no hearts: the clock is an idle `LevelClock(limit: 0)` (never started, never expires), `timerArmed` says 0 s,
// `timerStarted` marks the stage's first selection (tutorials' "first tap"). The HUD reads `goalProgress` ("sorted" tubes of
// the level's colours). Boosters: `undo` (the last pour back) and `extraTube` (one more empty tube, `play.maxExtraTubes` per
// stage). Deterministic: no wall clock, no randomness in play (the levels are the seeded data).

// MARK: - events (the board's; opaque to the shell)

public enum SortEvent: PuzzleEvent, Equatable {
    /// The tube's top run lifted (`count` units).
    case selected(tube: Int, count: Int)
    case deselected(tube: Int)
    /// `count` units of `color` poured from `from` onto `to` (a move).
    case poured(from: Int, to: Int, count: Int, color: Int)
    /// The rules refused `from` → `to` (a failed move: the target shakes, the selection drops).
    case refused(from: Int, to: Int)
    /// A selection that does nothing (an empty tube with nothing lifted, no tube, not playing).
    case ignored(tube: Int?)
    /// A pour filled `tube` with one colour.
    case tubeCompleted(tube: Int, color: Int)
    /// `count` empty tubes were added (booster or continue); `total` tubes now.
    case tubesAdded(count: Int, total: Int)
    /// Undo: `count` units go back from `from` (the pour's target) to `to` (its source).
    case undone(from: Int, to: Int, count: Int)

    /// Pours and refusals are the player's resolved moves (the tap haptic and cue, tutorials, bots); the target is the second
    /// pick.
    public var move: PuzzleMove? {
        switch self {
        case .poured(_, let to, _, _): return PuzzleMove(target: PuzzleTarget(to), failed: false)
        case .refused(_, let to): return PuzzleMove(target: PuzzleTarget(to), failed: true)
        case .selected, .deselected, .ignored, .tubeCompleted, .tubesAdded, .undone: return nil
        }
    }
}

extension SessionOutput {
    /// The sort board's events of a batch, in order.
    public static func sortEvents(_ outputs: [SessionOutput]) -> [SortEvent] {
        outputs.compactMap { o -> SortEvent? in
            if case .puzzle(let p) = o { return p as? SortEvent }
            return nil
        }
    }
}

/// One pour of the undo history.
public struct SortPour: Hashable, Sendable {
    public var from: Int
    public var to: Int
    public var count: Int
    public init(from: Int, to: Int, count: Int) { self.from = from; self.to = to; self.count = count }
}

// MARK: - the session

public final class SortPuzzleSession: PuzzleSession {
    public let stages: [SortLevel]
    /// The session's level numbers (the plan's; `WinResult.levels`).
    public let levels: [Int]
    public let setup: AttemptSetup
    /// Rewards and the fail chains (rules.json + this module's defaults, `SortRules.meta(over:)`).
    public let meta: MetaRules
    public let rules: SortRules
    /// The plan's reward (nil = by tag).
    public let reward: Int?
    /// The streak multiplier is above x1: the chain keeps its streak step (set before `start()`).
    public var streakActive: Bool

    public private(set) var phase: Phase
    public private(set) var stage: Int
    public private(set) var tubes: [[Int]]
    /// The lifted tube, if any.
    public private(set) var selection: Int?
    /// This stage's pours, for undo.
    public private(set) var history: [SortPour] = []
    public private(set) var clock = LevelClock(limit: 0)
    public private(set) var started = false
    /// Session totals (WinResult.stats): pours, refused pours, undos, extra tubes (booster + continue).
    public private(set) var pours = 0
    public private(set) var refusals = 0
    public private(set) var undos = 0
    public private(set) var tubesAdded = 0
    /// Extra-tube boosters used this stage (capped by `play.maxExtraTubes`).
    public private(set) var extraTubesUsed = 0
    private var stageStarted = false
    /// The solver's plan from `plan.state` (the hint follows it while the player does).
    private var plan: (state: [[Int]], moves: ArraySlice<SortMove>)?

    public init(stages: [SortLevel], levels: [Int]? = nil, setup: AttemptSetup, meta: MetaRules, rules: SortRules,
                reward: Int? = nil, streakActive: Bool = false) {
        precondition(!stages.isEmpty, "a session needs at least one stage")
        self.stages = stages
        self.levels = levels ?? stages.map(\.level)
        self.setup = setup
        self.meta = meta
        self.rules = rules
        self.reward = reward
        self.streakActive = streakActive
        let first = min(max(0, setup.firstStage), stages.count - 1)
        stage = first
        phase = .intro(stage: first)
        tubes = stages[first].tubes
    }

    public var level: SortLevel { stages[stage] }
    public var capacity: Int { stages[stage].capacity }
    public var stageCount: Int { stages.count }
    public var hearts: Int? { nil }
    public var isFinished: Bool {
        switch phase { case .won, .lost: return true; default: return false }
    }
    /// Complete tubes now.
    public var completedCount: Int { tubes.filter { SortMechanics.isComplete($0, capacity: capacity) }.count }
    /// The highest tag of the session's boards.
    public var tag: LevelTag {
        let rank: [LevelTag: Int] = [.normal: 0, .hard: 1, .superHard: 2]
        return stages.map(\.tag).max { (rank[$0] ?? 0) < (rank[$1] ?? 0) } ?? .normal
    }

    private var isLive: Bool {
        switch phase { case .ready, .playing: return true; default: return false }
    }

    // MARK: lifecycle

    public func start() -> [SessionOutput] {
        guard !started else { return [] }
        started = true
        clock.hold(.intro)
        return [.meta(.stageLoaded(stage: stage, of: stages.count, level: stages[stage].level))]
    }

    public func ack(_ a: PuzzleAck) -> [SessionOutput] {
        guard started else { return [] }
        switch a {
        case .introFinished:
            guard case .intro(let k) = phase else { return [] }
            clock.release(.intro)
            phase = .ready(stage: k)
            return [.meta(.timerArmed(stage: k, seconds: 0)), progress()]
        case .stageTransitionDone:
            guard case .stageClear(let k) = phase, k + 1 < stages.count else { return [] }
            let next = k + 1
            stage = next
            tubes = stages[next].tubes
            selection = nil
            history = []
            extraTubesUsed = 0
            stageStarted = false
            plan = nil
            clock = LevelClock(limit: 0)
            phase = .ready(stage: next)
            return [.meta(.stageAdvanced(to: next)),
                    .meta(.stageLoaded(stage: next, of: stages.count, level: stages[next].level)),
                    .meta(.timerArmed(stage: next, seconds: 0)), progress()]
        case .boardCleared, .contact, .beat:
            return []
        }
    }

    public func tick(_ dt: Double) -> [SessionOutput] { [] }
    public func hold(_ r: HoldReason) { clock.hold(r) }
    public func release(_ r: HoldReason) { clock.release(r) }

    // MARK: input

    /// `.select` (the board's input) and `.tap` pick tubes; `.drag(from:to:)` is both picks at once.
    public func input(_ e: PuzzleInput, at gameTime: Double) -> [SessionOutput] {
        switch e {
        case .select(let t): return select(t.raw)
        case .tap(let t): return select(t?.raw)
        case .drag(let from, let to):
            var out: [SessionOutput] = []
            if let s = selection, s != from.raw { out += select(s) }          // another tube was lifted: drop it first
            if selection != from.raw { out += select(from.raw) }
            if let to, selection == from.raw { out += select(to.raw) }
            return out
        case .swap, .custom:
            return []
        }
    }

    private func select(_ t: Int?) -> [SessionOutput] {
        let k: Int
        switch phase {
        case .ready(let s), .playing(let s): k = s
        default: return [.puzzle(SortEvent.ignored(tube: t))]
        }
        guard let t, tubes.indices.contains(t) else { return [.puzzle(SortEvent.ignored(tube: nil))] }
        guard let s = selection else {
            guard !tubes[t].isEmpty else { return [.puzzle(SortEvent.ignored(tube: t))] }
            selection = t
            return startStage(k) + [.puzzle(SortEvent.selected(tube: t, count: SortMechanics.topRun(tubes[t])))]
        }
        selection = nil
        if s == t { return [.puzzle(SortEvent.deselected(tube: t))] }
        guard SortMechanics.canPour(tubes, from: s, to: t, capacity: capacity) else {
            refusals += 1
            return [.puzzle(SortEvent.refused(from: s, to: t))]
        }
        return pour(SortMove(s, t), stage: k)
    }

    /// The stage's first selection (the idle clock is never started: nothing can expire).
    private func startStage(_ k: Int) -> [SessionOutput] {
        guard !stageStarted else { return [] }
        stageStarted = true
        if case .ready = phase { phase = .playing(stage: k) }
        return [.meta(.timerStarted(stage: k))]
    }

    private func pour(_ m: SortMove, stage k: Int) -> [SessionOutput] {
        let c = capacity
        let before = tubes
        let n = SortMechanics.pourCount(tubes, from: m.from, to: m.to, capacity: c)
        let colour = tubes[m.from].last ?? 0
        let completedBefore = completedCount
        tubes = SortMechanics.apply(tubes, m, capacity: c)
        history.append(SortPour(from: m.from, to: m.to, count: n))
        pours += 1
        if let p = plan, p.state == before, p.moves.first == m {
            plan = (tubes, p.moves.dropFirst())
        } else {
            plan = nil
        }
        var out: [SessionOutput] = [.puzzle(SortEvent.poured(from: m.from, to: m.to, count: n, color: colour))]
        if SortMechanics.isComplete(tubes[m.to], capacity: c) {
            out.append(.puzzle(SortEvent.tubeCompleted(tube: m.to, color: colour)))
        }
        if completedCount != completedBefore { out.append(progress()) }
        if SortMechanics.isSolved(tubes, capacity: c) { return out + cleared(k) }
        if !SortMechanics.hasLegalMove(tubes, capacity: c) { out += openOffer(.stuck, step: 0) }
        return out
    }

    /// The stage's last pour: the next stage after the transition, or the win (decided here, banked by the shell at once).
    private func cleared(_ k: Int) -> [SessionOutput] {
        if k + 1 < stages.count {
            phase = .stageClear(stage: k)
            clock.hold(.stageTransition)
            return [.meta(.stageCleared(stage: k))]
        }
        clock.hold(.winSequence)
        let t = tag
        let result = WinResult(levels: levels, tag: t, timeLeft: 0, heartsLeft: 0, firstTry: setup.attemptIndex <= 1,
                               reward: reward ?? meta.rewards.reward(for: t), bumps: refusals, stars: nil,
                               stats: ["pours": Double(pours), "refused": Double(refusals), "undos": Double(undos),
                                       "tubesAdded": Double(tubesAdded)])
        phase = .won(result)
        return [.meta(.won(result))]
    }

    private func progress() -> SessionOutput {
        .meta(.goalProgress([GoalState(id: SortPuzzleModule.progressGoal, current: completedCount,
                                       target: stages[stage].colors)]))
    }

    // MARK: fail chain

    public func chain(_ kind: ContinueOffer.Kind) -> [ContinueOffer] { meta.chain(kind, streakActive: streakActive) }

    private func openOffer(_ kind: ContinueOffer.Kind, step: Int) -> [SessionOutput] {
        let steps = chain(kind)
        selection = nil
        guard step < steps.count else {
            let reason = kind.lossReason
            phase = .lost(reason)
            clock.hold(.offer)
            return [.meta(.lost(reason))]
        }
        let o = steps[step]
        phase = .offer(o)
        clock.hold(.offer)
        return [.meta(.offer(o))]
    }

    /// The caller has already charged `offer.price`. A `puzzleAction` grant runs here ("extraTube" n, "undo" n); a grant of
    /// another kind changes nothing on this board. Still stuck afterwards → the chain's next step.
    public func acceptContinue() -> [SessionOutput] {
        guard case .offer(let o) = phase else { return [] }
        var out: [SessionOutput] = [.meta(.continued(o))]
        if case .puzzleAction(let id, let amount) = o.grant { out += perform(id, amount: amount) }
        clock.release(.offer)
        phase = .playing(stage: stage)
        if !SortMechanics.hasLegalMove(tubes, capacity: capacity) { out += openOffer(o.kind, step: o.step + 1) }
        return out
    }

    public func declineContinue() -> [SessionOutput] {
        guard case .offer(let o) = phase else { return [] }
        return openOffer(o.kind, step: o.step + 1)
    }

    public func quit() -> [SessionOutput] {
        guard started, !isFinished else { return [] }
        selection = nil
        phase = .lost(.quit)
        clock.hold(.offer)
        return [.meta(.lost(.quit))]
    }

    // MARK: boosters and rescues

    /// The module's action behind a booster id (`capabilities.boosters`).
    static func action(of id: BoosterID) -> String? {
        guard let spec = SortPuzzleModule.capabilities.booster(id), case .puzzleAction(let a) = spec.effect else { return nil }
        return a
    }

    public func canUseBooster(_ id: BoosterID) -> Bool {
        guard isLive, let action = Self.action(of: id) else { return false }
        switch action {
        case SortPuzzleModule.undoAction: return !history.isEmpty
        case SortPuzzleModule.extraTubeAction: return extraTubesUsed < rules.play.maxExtraTubes
        default: return false
        }
    }

    /// The caller has already taken the stock. Boosters never start the stage (like the reference module's).
    public func useBooster(_ id: BoosterID) -> [SessionOutput] {
        guard canUseBooster(id), let action = Self.action(of: id) else { return [] }
        var out: [SessionOutput] = [.meta(.boosterUsed(id))]
        if let s = selection {
            selection = nil
            out.append(.puzzle(SortEvent.deselected(tube: s)))
        }
        if action == SortPuzzleModule.extraTubeAction { extraTubesUsed += 1 }
        return out + perform(action, amount: 1)
    }

    /// A puzzle action: "extraTube" adds `amount` empty tubes, "undo" takes back up to `amount` pours.
    private func perform(_ action: String, amount: Int) -> [SessionOutput] {
        switch action {
        case SortPuzzleModule.extraTubeAction:
            let n = max(0, amount)
            guard n > 0 else { return [] }
            for _ in 0..<n { tubes.append([]) }
            tubesAdded += n
            plan = nil
            return [.puzzle(SortEvent.tubesAdded(count: n, total: tubes.count))]
        case SortPuzzleModule.undoAction:
            let completedBefore = completedCount
            var out: [SessionOutput] = []
            for _ in 0..<max(0, amount) {
                guard let e = undoOnce() else { break }
                out.append(.puzzle(e))
            }
            if !out.isEmpty && completedCount != completedBefore { out.append(progress()) }
            return out
        default:
            return []
        }
    }

    private func undoOnce() -> SortEvent? {
        guard let last = history.last, tubes.indices.contains(last.to), tubes.indices.contains(last.from),
              tubes[last.to].count >= last.count else { return nil }
        history.removeLast()
        let moved = Array(tubes[last.to].suffix(last.count))
        tubes[last.to].removeLast(last.count)
        tubes[last.from].append(contentsOf: moved)
        undos += 1
        plan = nil
        return .undone(from: last.to, to: last.from, count: last.count)
    }

    // MARK: hints (bots, debug jumps)

    /// The next tube to pick along the solver's plan: its source, then its target; a different tube lifted → that tube
    /// (picking it again drops it). nil outside play.
    public func hint() -> PuzzleTarget? {
        guard isLive else { return nil }
        guard let m = nextMove() else { return selection.map { PuzzleTarget($0) } }
        guard let s = selection else { return PuzzleTarget(m.from) }
        return PuzzleTarget(s == m.from ? m.to : s)
    }

    /// The plan's next pour (the solver from the current tubes, `play.hintBudget`); without a plan the first useful, then the
    /// first legal pour; nil = none.
    public func nextMove() -> SortMove? {
        if let p = plan, p.state == tubes, let m = p.moves.first { return m }
        let c = capacity
        if let solution = SortSolver.solve(tubes, capacity: c, budget: rules.play.hintBudget), let m = solution.first {
            plan = (tubes, solution[...])
            return m
        }
        plan = nil
        return SortMechanics.usefulMoves(tubes, capacity: c).first ?? SortMechanics.legalMoves(tubes, capacity: c).first
    }
}

// MARK: - the module

/// SortPuzzle's pure half (`puzzle.module: sort-puzzle` in a game.yml that uses it).
public enum SortPuzzleModule: PuzzleModule {
    public static let id = "sort-puzzle"
    public static let contractVersion = PuzzleContract.version

    public static let undo = BoosterID("undo")
    public static let extraTube = BoosterID("extraTube")
    /// The puzzle actions (boosters and fail-chain grants: sort.json `failChain.*.action`).
    public static let undoAction = "undo"
    public static let extraTubeAction = "extraTube"
    /// The `goalProgress` counter: complete tubes of the level's colours.
    public static let progressGoal = "sorted"
    /// The custom fail rule ("stuck": no legal pour left).
    public static let stuckRule = "stuck"

    /// Fail rule "stuck" (no timer, no hearts), pick-then-target input (+ a drag), boosters undo and extra tube, the progress
    /// widget, a fixed board, multi-board sessions.
    public static var capabilities: PuzzleCapabilities {
        PuzzleCapabilities(failRules: [.custom(stuckRule)], inputs: [.select2, .drag],
                           boosters: [BoosterSpec(id: undo, effect: .puzzleAction(undoAction)),
                                      BoosterSpec(id: extraTube, effect: .puzzleAction(extraTubeAction))],
                           hud: [.progress], zoomable: false, multiStageSessions: true)
    }

    /// Level `n` (generated, the same for everyone).
    public static func level(_ n: Int, rules: SortRules) -> SortLevel { SortGenerator.level(n, rules: rules) }

    /// The generic description of one board.
    public static func stage(_ level: SortLevel) -> PuzzleStage {
        PuzzleStage(level: level.level, tag: level.tag, timerSeconds: nil, hearts: nil, summary: level.summary, content: level)
    }

    public static func makeSession(stages: [SortLevel], levels: [Int]? = nil, setup: AttemptSetup, meta: MetaRules,
                                   rules: SortRules, reward: Int? = nil, streakActive: Bool = false) -> SortPuzzleSession {
        SortPuzzleSession(stages: stages, levels: levels, setup: setup, meta: rules.meta(over: meta), rules: rules,
                          reward: reward, streakActive: streakActive)
    }

    /// The first-win warm-up: level 1 played to its win by the bot, headless. Pure; the app runs it off the main thread.
    public static func warmUpWin(meta: MetaRules, rules: SortRules) -> WinResult? {
        let l = level(1, rules: rules)
        let s = makeSession(stages: [l], setup: AttemptSetup(levels: [l.level]), meta: meta, rules: rules)
        return SortBot.play(s).result
    }
}

/// A headless player that uses ONLY the generic contract (`PuzzleSession`): start, the intro ack, then the session's own
/// hint as `.select` inputs; stage transitions acked like a board would; offers accepted. Tests and the warm-up use it.
public enum SortBot {
    public struct Outcome {
        public var result: WinResult?
        public var lost: LossReason?
        public var inputs: Int
        /// Every output, in order.
        public var outputs: [SessionOutput]
    }

    public static func play(_ s: any PuzzleSession, maxInputs: Int = 5_000) -> Outcome {
        var all: [SessionOutput] = []
        var outcome = Outcome(result: nil, lost: nil, inputs: 0, outputs: [])
        func take(_ batch: [SessionOutput]) {
            all += batch
            for o in batch {
                guard case .meta(let m) = o else { continue }
                switch m {
                case .won(let r): outcome.result = r
                case .lost(let r): outcome.lost = r
                default: break
                }
            }
        }
        take(s.start())
        take(s.ack(.introFinished))
        while !s.isFinished && outcome.inputs < maxInputs {
            switch s.phase {
            case .stageClear:
                take(s.ack(.boardCleared))
                take(s.ack(.stageTransitionDone))
                continue
            case .offer:
                take(s.acceptContinue())
                continue
            default:
                break
            }
            guard let t = s.hint() else { break }
            outcome.inputs += 1
            take(s.input(.select(t), at: Double(outcome.inputs)))
        }
        if s.isFinished, case .won = s.phase { take(s.ack(.boardCleared)) }
        outcome.outputs = all
        return outcome
    }
}
