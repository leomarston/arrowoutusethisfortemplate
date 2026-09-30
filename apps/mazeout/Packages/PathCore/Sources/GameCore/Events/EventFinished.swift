import Foundation

// C3 — B1b EVENTS FINISHED STATE (owner item 14; design/publish/events.md "PH-0a"). VERIFIED on the owner's phone (v582,
// build/p/PH0a/before-reset.png 09:50 vs after-reset.png 10:10 TRT, the same home across the Monday 07:00 UTC roll, no touch
// in between): the ended events do NOT vanish at the roll. Their home badges stay and read "Finished" — the Hot Streak flags,
// the balloon badge, and the ladder bar's timer chip while the bar keeps its final "537/800" — and the trophy tab gets a red
// "!" (the Weekly results to see). The next events show once the player has opened the result.
//
// The model (INFERRED from that pair of shots; DECISION where they are silent, each one marked):
// - An instance the player TOOK PART in (joined: the day's Hot Streak, the week's Weekly Cup, the week's Treasure Climb or Up &
//   Away) that ends at a roll becomes a `FinishedEvent` — a snapshot of what its badge showed at the end.
// - It is HELD until the player opens its result (`openFinished`: the event's page, the Hot Streak list, the Leaderboard tab
//   for the Weekly Cup) or claims it (the rank prize of that very instance, `Events.claim`: the claim, then the new week).
// - DECISION: a counted win moves the player into the new instance of the events it scores (Hot Streak; the live ladder
//   event) and drops their holds — the home never shows a Finished bar over points that win just earned. A loss drops
//   nothing. The Weekly Cup's "!" is news about the ended week: only opening or claiming it clears it.
// - DECISION: one instance deep — a hold lives while its instance is the one right before the current one; the next roll
//   drops it (a player who never opens it loses one period's badge, never an event). A returning player whose last joined
//   instance is older sees no stale "Finished".
// - The RULES are untouched: the new instances join and score exactly as before (`refresh`, the hooks, the joins); a hold is
//   what the home SHOWS in the slot (`Events.Status.finished`) and what the home queue waits on (the ladder's week-start page).
// - Only while the rotation runs (`rotation.enabled`, the shipped social.json): the kill switch keeps the v552 plan byte for
//   byte (no hold is ever stored, so a save re-encodes as before).
// - Rewind-safe like every event: the roll runs on the SocialTime high-water clock, so a clock set back never re-creates or
//   duplicates a hold; the one-time rebase drops holds of the abandoned future.

/// An ended event instance the player took part in, held until its result is opened (v582 "Finished", PH-0a).
public struct FinishedEvent: Codable, Sendable, Equatable {
    public var event: EventID
    /// Event day (Hot Streak) or event week (Weekly Cup, Treasure Climb, Up & Away) of the ended instance.
    public var index: Int
    /// The contest score at the end (Hot Streak flags, Weekly Cup wins); 0 for the ladder events.
    public var score: Int
    /// Treasure Climb as it stood at the end (the bar keeps "points/target").
    public var claw: ClawState?
    /// Up & Away as it stood at the end.
    public var balloon: BalloonState?

    public init(event: EventID, index: Int, score: Int = 0, claw: ClawState? = nil, balloon: BalloonState? = nil) {
        self.event = event; self.index = index; self.score = score; self.claw = claw; self.balloon = balloon
    }

    enum CodingKeys: String, CodingKey { case event, index, score, claw, balloon }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        event = try c.decode(EventID.self, forKey: .event)
        index = try c.decode(Int.self, forKey: .index)
        score = try c.v(.score, 0)
        claw = try c.decodeIfPresent(ClawState.self, forKey: .claw)
        balloon = try c.decodeIfPresent(BalloonState.self, forKey: .balloon)
    }
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(event, forKey: .event)
        try c.encode(index, forKey: .index)
        try c.encode(score, forKey: .score)
        try c.encodeIfPresent(claw, forKey: .claw)
        try c.encodeIfPresent(balloon, forKey: .balloon)
    }
}

extension Events {
    /// The events that can be held (the ones with a result on home): the order the home reads them in.
    public static let finishable: [EventID] = [.streakRace, .weeklyContest, .clawChallenge, .balloonRise]

    /// The index `e`'s instances count in at `t` (the day for Hot Streak and a daily Treasure Climb, else the week).
    static func finishedIndex(_ e: EventID, at t: SocialTime, _ r: EconomyRules) -> Int {
        switch e {
        case .streakRace: return EventSchedule.day(t, r.events.calendar)
        case .clawChallenge: return clawIndex(t, r)
        default: return EventSchedule.week(t, r.events.calendar)
        }
    }

    /// The end of a held instance (its badge's last countdown reached 0 there).
    static func finishedEnd(_ f: FinishedEvent, _ r: EconomyRules) -> SocialTime {
        let c = r.events.calendar
        switch f.event {
        case .streakRace: return EventSchedule.dayStart(f.index + 1, c)
        case .clawChallenge where r.claw.period == "day": return EventSchedule.dayStart(f.index + 1, c)
        default: return EventSchedule.weekStart(f.index + 1, c)
        }
    }

    /// The holds at `t`: the stored ones still one instance deep, plus the joined instances that ended and are not stored yet
    /// (what the next roll stores). Pure; [] while the rotation is off.
    public static func finished(_ s: PlayerState, at t: SocialTime, rules r: EconomyRules) -> [FinishedEvent] {
        guard r.events.rotation.enabled else { return [] }
        var out = s.events.finished
        let ev = s.events
        func ended(_ e: EventID, _ index: Int?) -> Int? {
            guard let i = index, i < finishedIndex(e, at: t, r) else { return nil }
            return i
        }
        func put(_ f: FinishedEvent) {
            out.removeAll { $0.event == f.event }
            out.append(f)
        }
        if let i = ended(.streakRace, ev.streakRace.index) { put(FinishedEvent(event: .streakRace, index: i, score: ev.streakRace.score)) }
        if let i = ended(.weeklyContest, ev.weekly.index) { put(FinishedEvent(event: .weeklyContest, index: i, score: ev.weekly.score)) }
        if let i = ended(.clawChallenge, ev.claw.week) { put(FinishedEvent(event: .clawChallenge, index: i, claw: ev.claw)) }
        if let i = ended(.balloonRise, ev.balloon.week) { put(FinishedEvent(event: .balloonRise, index: i, balloon: ev.balloon)) }
        // one instance deep (DECISION): a hold older than the instance right before the current one is dropped; a hold of the
        // current (or a later) instance cannot exist outside a rebase and is dropped too
        out.removeAll { f in
            let now = finishedIndex(f.event, at: t, r)
            return f.index < now - 1 || f.index >= now
        }
        return out
    }

    /// The roll's first step (before the contests and the ladder states are reset): store the holds of `t`.
    static func holdFinished(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        let f = finished(s, at: t, rules: r)
        if f != s.events.finished { s.events.finished = f }
    }

    /// The player opened `e`'s result (its page, the Hot Streak list, the Leaderboard tab): its hold goes, and the new instance
    /// shows in the slot. Rolls only the calendar events (no world query: a running Rocket Rally is left to `refresh`). True
    /// when a hold was dropped.
    @discardableResult
    public static func openFinished(_ s: inout PlayerState, _ e: EventID, now: Date, rules: EconomyRules) -> Bool {
        let t = EconomyClock.social(&s, wall: now)
        rollCalendar(&s, at: t, rules)
        let n = s.events.finished.count
        s.events.finished.removeAll { $0.event == e }
        return s.events.finished.count != n
    }

    /// Drops the holds a counted win moved past (DECISION: the win scored the new instance of these events).
    static func dropFinished(_ s: inout PlayerState, _ events: Set<EventID>) {
        guard !s.events.finished.isEmpty else { return }
        s.events.finished.removeAll { events.contains($0.event) }
    }

    /// The home's view of the holds (`Events.Status.finished`).
    public struct FinishedStatus: Equatable, Sendable {
        /// Treasure Climb's bar as it stood at the end (its `endsAt` = the roll).
        public var claw: ClawStatus?
        /// Up & Away as it stood at the end.
        public var balloon: BalloonStatus?
        /// The ended Hot Streak (its final flags in `score`).
        public var streakRace: ContestStatus?
        /// The ended Weekly Cup (the trophy tab's red "!").
        public var weekly: ContestStatus?

        public init() {}

        public var isEmpty: Bool { claw == nil && balloon == nil && streakRace == nil && weekly == nil }
        /// The ladder slot holds an ended event (the bar reads "Finished" in place of this week's ladder event).
        public var ladder: EventID? { claw != nil ? .clawChallenge : (balloon != nil ? .balloonRise : nil) }
    }

    /// The holds of a rolled state as the home shows them.
    static func finishedStatus(_ c: PlayerState, multiplier m: Int, rules: EconomyRules) -> FinishedStatus {
        var out = FinishedStatus()
        guard rules.events.rotation.enabled else { return out }
        for f in c.events.finished {
            let end = finishedEnd(f, rules)
            switch f.event {
            case .streakRace:
                out.streakRace = ContestStatus(index: f.index, joined: true, score: f.score, endsAt: end)
            case .weeklyContest:
                out.weekly = ContestStatus(index: f.index, joined: true, score: f.score, endsAt: end)
            case .clawChallenge:
                if let cs = f.claw, !rules.claw.ladder.isEmpty { out.claw = clawStatus(cs, endsAt: end, multiplier: m, rules: rules) }
            case .balloonRise:
                if let b = f.balloon { out.balloon = balloonStatus(b, week: f.index, rules) }
            default:
                break
            }
        }
        return out
    }
}
