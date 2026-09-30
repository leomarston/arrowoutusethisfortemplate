import Foundation
import GameCore

// C2 (SPEC-architecture §4.15). Plays a LevelSession with no UI, in simulated time: a strategy (the solver's hint order,
// or a random free unit), a human-like tap interval, a mistake probability (a deliberate tap on a blocked arrow), and
// MODELLED acks, i.e. what the board would report: the intro after `Timing.introDone`, a bump's contact and return from
// `Curves.bump` (v552 profile), a door burst `Timing.doorBurstAfterTap` after its key's tap, the last exit leaving the
// board from `ExitKinematics`, the stage transition `Timing.stageGap` after that. Users: HeadlessTests (every recorded
// level), the generator gate, `pclevels bot`, difficulty bands. Deterministic for a given seed. The app's AutoPlayer
// drives the REAL board instead (§8.4).

public struct DriverConfig: Sendable {
    public enum Strategy: String, Codable, Sendable, CaseIterable {
        /// The hint's unit (the greedy order's first unit).
        case solver
        /// A random free unit (seeded).
        case randomFree
    }
    public enum ContinuePolicy: Sendable, Equatable {
        case decline
        /// Accept up to `max` offers (the caller's coins are not modelled).
        case accept(max: Int)
    }

    public var strategy: Strategy = .solver
    /// Seconds between two taps.
    public var tapInterval: Double = 0.6
    /// Probability that a tap is a deliberate tap on a blocked arrow (when one exists).
    public var mistakes: Double = 0
    public var seed: UInt64 = 1
    public var continues: ContinuePolicy = .decline
    public var introDuration: Double = Timing.introDone
    public var stageGap: Double = Timing.stageGap
    public var doorBurst: Double = Timing.doorBurstAfterTap
    public var bump: BumpCurve = Curves.bump
    public var exits: ExitKinematics = .measured
    /// Give up after this much simulated time.
    public var maxSeconds: Double = 3600
    /// Keep the event log (large for long sessions).
    public var recordEvents: Bool = true

    public init(strategy: Strategy = .solver, tapInterval: Double = 0.6, mistakes: Double = 0, seed: UInt64 = 1,
                continues: ContinuePolicy = .decline) {
        self.strategy = strategy; self.tapInterval = tapInterval; self.mistakes = mistakes; self.seed = seed
        self.continues = continues
    }
}

public struct DriverResult: Sendable {
    public var won: Bool
    /// The HUD seconds at the win (0 when not won).
    public var timeLeft: Int
    /// Exact remaining seconds of the last stage's clock.
    public var remaining: Double
    /// remaining / the last stage's limit.
    public var timeLeftFraction: Double
    public var heartsLeft: Int
    public var bumps: Int
    public var taps: Int
    public var events: [SessionEvent]
    public var phase: Phase
    /// Simulated seconds from start() to the end.
    public var elapsed: Double
    /// Nothing was free and nothing pending: the arrows left (live + hidden).
    public var stuck: [ArrowID]
    public var loss: LossReason?
}

public enum HeadlessDriver {

    /// Plays a one-stage session of `level`.
    public static func play(level: LevelSpec, rules: RulesTuning = .default, config: DriverConfig = DriverConfig())
        -> DriverResult {
        let plan = SessionPlan(id: "L\(level.level)", levels: [level.level])
        let session = LevelSession(plan: plan, stages: [level], setup: AttemptSetup(levels: [level.level], seed: config.seed),
                                   rules: rules)
        return play(session, config: config)
    }

    /// Plays `session` (not yet started) to its end: won, lost, stuck or out of simulated time.
    public static func play(_ session: LevelSession, config: DriverConfig = DriverConfig()) -> DriverResult {
        var rng = PathRandom(seed: config.seed).fork("autoplay")
        var now = 0.0
        var log: [SessionEvent] = []
        var pending: [(t: Double, seq: Int, ack: SessionAck)] = []
        var seq = 0
        var accepted = 0
        var lastExitLeaves = 0.0
        var nextTap = 0.0
        var stuck: [ArrowID] = []

        func schedule(_ t: Double, _ a: SessionAck) {
            seq += 1
            pending.append((t, seq, a))
            pending.sort { $0.t != $1.t ? $0.t < $1.t : $0.seq < $1.seq }
        }
        func note(_ ev: [SessionEvent]) {
            if config.recordEvents { log.append(contentsOf: ev) }
            for e in ev {
                switch e {
                case .exited(let plan):
                    for key in plan.beats { if case let .keyReleased(_, door, _) = key { schedule(now + config.doorBurst, .doorBurst(door)) } }
                    var longest = 0.0
                    for (_, p) in plan.paths { longest = max(longest, p.toGridEdge + Double(max(0, p.bodyCellCount - 1))) }
                    lastExitLeaves = max(lastExitLeaves, now + config.exits.time(toTravel: longest))
                case .bumped(let plan):
                    schedule(now + config.bump.outDuration(contactCells: plan.contactCells), .bumpContact(plan.arrow))
                    schedule(now + config.bump.duration(contactCells: plan.contactCells), .bumpFinished(plan.arrow))
                case .stageCleared:
                    schedule(max(now, lastExitLeaves), .lastExitLeftBoard)
                    schedule(max(now, lastExitLeaves) + config.stageGap, .stageTransitionDone)
                case .stageAdvanced:
                    nextTap = now + config.tapInterval
                default:
                    break
                }
            }
        }
        func handleOffers() {
            while case .offer = session.phase {
                switch config.continues {
                case .accept(let m) where accepted < m:
                    accepted += 1
                    note(session.acceptContinue())
                default:
                    note(session.declineContinue())
                }
            }
        }
        func advance(to t: Double) {
            guard t > now else { return }
            note(session.tick(t - now))
            now = t
            handleOffers()
        }

        note(session.start())
        schedule(config.introDuration, .introFinished)
        nextTap = config.introDuration + config.tapInterval

        while !session.isFinished && now < config.maxSeconds {
            // acks due now
            if let p = pending.first, p.t <= now {
                pending.removeFirst()
                note(session.ack(p.ack))
                handleOffers()
                continue
            }
            let canTap: Bool
            switch session.phase { case .ready, .playing: canTap = true; default: canTap = false }
            if !canTap {
                guard let p = pending.first else { break }          // nothing will change any more
                advance(to: p.t)
                continue
            }
            if now < nextTap {
                advance(to: min(nextTap, pending.first?.t ?? nextTap))
                continue
            }
            // choose a tap
            let board = session.board
            var target: ArrowID?
            if config.mistakes > 0, rng.unit() < config.mistakes {
                let blocked = board.live.filter { !board.isBumping($0) && !board.isFree($0) }
                if !blocked.isEmpty { target = blocked[rng.below(blocked.count)] }
            }
            if target == nil {
                switch config.strategy {
                case .solver:
                    target = session.hint()?.first
                case .randomFree:
                    let free = board.freeUnits()
                    if !free.isEmpty { target = free[rng.below(free.count)].first }
                }
            }
            guard let tapID = target else {
                if let p = pending.first { advance(to: p.t); continue }   // wait for a door / a bump to settle
                stuck = (board.live + board.hidden).sorted()
                break
            }
            note(session.tap(tapID, at: now))
            handleOffers()
            nextTap = now + config.tapInterval
        }

        var won = false, timeLeft = 0, loss: LossReason?
        switch session.phase {
        case .won(let r): won = true; timeLeft = r.timeLeft
        case .lost(let r): loss = r
        default: break
        }
        let limit = Double(max(1, session.clock.limit))
        return DriverResult(won: won, timeLeft: timeLeft, remaining: session.clock.remaining,
                            timeLeftFraction: session.clock.remaining / limit, heartsLeft: session.hearts,
                            bumps: session.bumps, taps: session.taps, events: log, phase: session.phase, elapsed: now,
                            stuck: stuck, loss: loss)
    }
}
