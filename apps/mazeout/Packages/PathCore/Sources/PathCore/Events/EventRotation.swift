import Foundation

// C3 — B1 EVENTS-P (PUBLISH item 14 "oh this week this challenge came"; SPEC.md ruling 38 EVENTS; design/publish/events.md §4,
// §8.1; the reference = design/publish/tools/rotation_ref.py, T7 final, with its 1,044-week fixture). The featured events of
// event-week w are a pure function of w, one constant seed and the tunables in social.json `events.rotation`: the same
// calendar on every device, forever, with no server and no stored table (a live-ops calendar computed offline).
//
//   slot                 members                                 period
//   always · daily       Streak Race (+ the multiplier)          every event day
//   always · weekly      Weekly Contest                          every event week
//   featured · ladder    Claw Challenge ⇄ Up & Away (balloonRise) the event week (the bar under the top row)
//   featured · race      Rocket Race ⇄ Sky Jump, ~1 week in 7    the event week (daily offers inside it)
//                        both ("Double Event Week")
//
// The generator (PORTING RULES of rotation_ref.py, bit for bit): iterate w' = 0…w with the O(1) state (ladderLast, ladderRun,
// raceLastSingle, raceSingleRun, lastDouble); the three draws of week w' are the stateless SocialHash u01(seed, "ladder" |
// "race" | "raceDouble", w'); every comparison is a strict `<` on doubles.
//   ladder: pin | no history → ladder[0] if u < 0.5 else ladder[1] | ladderRun ≥ maxRun → the other | u < pSwitch → the other
//           | else the same.
//   race:   pin | w' > 0 and (no Double yet or w' − lastDouble ≥ doubleMinGap) and ud < pDouble → DOUBLE
//           | no single yet → race[0] if u < 0.5 else race[1] | raceSingleRun ≥ maxRun or u < pSwitch → the other single
//           | else the same single. A Double week leaves the single run untouched.
// w < 0 (a clock before the anchor) takes week 0's picks. An O(w) recompute (≈ 3 hashes a week: ~3,000 at 20 years, a few
// µs) keeps it pure and thread-agnostic: no cache.
// Rewind-safe: the week comes from the rewind-safe SocialTime (max(device clock, high-water)), so a clock set back freezes
// the calendar until real time catches up; last week's event never comes back.
// Per-player segmentation (events.md §4.4) never changes the calendar: a single race pick the player has not unlocked is
// replaced by the other member when that one is unlocked (a Rocket week shows Sky Jump to L40-54), a Double week shows each
// unlocked member; the ladder pick needs its unlock (both members: L33). The kill switch (`enabled` false, the compiled
// default) = the v552 plan: Claw + Rocket + Sky + the two always-on events, each behind its own unlock; Up & Away never.

extension EventRules {
    /// social.json `events.rotation` (C3's layout; rotation_ref.py CONFIG spells the shipped block).
    public struct Rotation: Codable, Sendable, Equatable {
        /// A pinned week: the ladder member's raw value and the race code ("rocketRace" | "skyJump" | "double").
        public struct Pin: Codable, Sendable, Equatable {
            public var ladder: String
            public var race: String
            public init(ladder: String, race: String) { self.ladder = ladder; self.race = race }
        }

        /// OFF by default (compiled): every existing C3 rule and test keeps the v552 plan; the shipped social.json turns it on.
        public var enabled = false
        /// Week 0 = Mon 2026-04-27 07:00:00 UTC = the event calendar's anchor (`Calendar.epoch`), pinned here on its own (it is
        /// not the social world's epoch, OD9: a slipped release never changes a week).
        public var epoch: Int64 = 1_777_273_200
        /// "ROTATION": a constant, never the install seed (one calendar for everyone, events.md §4.1.2).
        public var seed = "0x524F544154494F4E"
        public var always = ["streakRace", "weeklyContest"]
        public var ladder = ["clawChallenge", "balloonRise"]
        public var race = ["rocketRace", "skyJump"]
        public var pSwitch = 0.65
        public var pDouble = 0.22
        public var doubleMinGap = 3
        public var maxRun = 2
        /// Week index (decimal text) → a pinned pick. A pin enters the history: the weeks after it are re-derived.
        public var pins: [String: Pin] = [:]
        /// At most this many unrequested pages per home visit (week-start pages + daily offers + the Streak list; G2).
        public var announceCap = 2
        /// The "Coming next" teaser shows in a featured event's last `teaserHours`.
        public var teaserHours = 24
        /// Event notifications only inside [from, to] local hours (G2 `LocalNotifications`, EventNotifications).
        public var notifyWindow = [10, 21]
        /// RUNTIME ONLY (never encoded): featured members this build cannot show (the app's Release art gate). `live` treats
        /// such a pick like a locked one: the other member of its slot runs that week instead.
        public var unavailable: Set<String> = []

        public init() {}

        enum CodingKeys: String, CodingKey {
            case enabled, epoch, seed, always, ladder, race, pSwitch, pDouble, doubleMinGap, maxRun, pins, announceCap, teaserHours,
                 notifyWindow
        }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Rotation()
            enabled = try c.v(.enabled, d.enabled)
            epoch = try c.v(.epoch, d.epoch)
            seed = try c.v(.seed, d.seed)
            if Self.parseSeed(seed) == nil { seed = d.seed }
            always = try c.v(.always, d.always)
            ladder = try c.v(.ladder, d.ladder)
            race = try c.v(.race, d.race)
            // two distinct members per featured slot, or the defaults (rotation_ref.py asserts the same shape)
            if ladder.count != 2 || race.count != 2 || Set(ladder + race).count != 4 { ladder = d.ladder; race = d.race }
            pSwitch = try c.v(.pSwitch, d.pSwitch)
            pDouble = try c.v(.pDouble, d.pDouble)
            doubleMinGap = try c.v(.doubleMinGap, d.doubleMinGap)
            maxRun = try c.v(.maxRun, d.maxRun)
            pins = try c.v(.pins, d.pins)
            announceCap = try c.v(.announceCap, d.announceCap)
            teaserHours = try c.v(.teaserHours, d.teaserHours)
            notifyWindow = try c.v(.notifyWindow, d.notifyWindow)
            if notifyWindow.count != 2 || notifyWindow[0] > notifyWindow[1] { notifyWindow = d.notifyWindow }
        }

        public func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            try c.encode(enabled, forKey: .enabled); try c.encode(epoch, forKey: .epoch); try c.encode(seed, forKey: .seed)
            try c.encode(always, forKey: .always); try c.encode(ladder, forKey: .ladder); try c.encode(race, forKey: .race)
            try c.encode(pSwitch, forKey: .pSwitch); try c.encode(pDouble, forKey: .pDouble)
            try c.encode(doubleMinGap, forKey: .doubleMinGap); try c.encode(maxRun, forKey: .maxRun)
            try c.encode(pins, forKey: .pins); try c.encode(announceCap, forKey: .announceCap)
            try c.encode(teaserHours, forKey: .teaserHours); try c.encode(notifyWindow, forKey: .notifyWindow)
        }

        /// "0x…" (or bare hex) → the 64-bit seed.
        static func parseSeed(_ text: String) -> UInt64? {
            let t = text.lowercased().hasPrefix("0x") ? String(text.dropFirst(2)) : text
            return t.isEmpty ? nil : UInt64(t, radix: 16)
        }
        public var seedValue: UInt64 { Self.parseSeed(seed) ?? 0x524F_5441_5449_4F4E }
    }
}

/// The calendar's featured picks of one event week (the same for every player).
public struct WeekPlan: Equatable, Sendable, Hashable {
    public var week: Int
    /// The ladder slot's event (Claw Challenge or Up & Away).
    public var ladder: EventID
    /// The race slot's events: one, or both on a Double Event Week (config order: Rocket, Sky).
    public var race: [EventID]
    public var start: SocialTime
    public var end: SocialTime
    public var isDouble: Bool { race.count > 1 }

    public init(week: Int, ladder: EventID, race: [EventID], start: SocialTime, end: SocialTime) {
        self.week = week; self.ladder = ladder; self.race = race; self.start = start; self.end = end
    }
}

/// What one player sees in a week: the calendar after segmentation, the unlocks and the kill switch.
public struct LiveEvents: Equatable, Sendable, Hashable {
    public var always: [EventID]
    public var ladder: EventID?
    public var race: [EventID]

    public init(always: [EventID] = [], ladder: EventID? = nil, race: [EventID] = []) {
        self.always = always; self.ladder = ladder; self.race = race
    }

    public func contains(_ e: EventID) -> Bool { ladder == e || race.contains(e) || always.contains(e) }
    /// The featured events (ladder, then race) — what a week-start announcement is about.
    public var featured: [EventID] { (ladder.map { [$0] } ?? []) + race }
}

public enum EventRotation {
    static let lLadder = Label("ladder"), lRace = Label("race"), lDouble = Label("raceDouble")
    /// The race code of a Double Event Week (both race members).
    static let double = 2

    /// Event week of `t` on the rotation's anchor (floor division: times before the anchor stay correct).
    public static func week(_ t: SocialTime, _ r: EventRules) -> Int {
        Int(EventSchedule.floorDiv(t.seconds - r.rotation.epoch, r.calendar.week))
    }

    public static func weekStart(_ w: Int, _ r: EventRules) -> SocialTime {
        SocialTime(seconds: r.rotation.epoch + Int64(w) * r.calendar.week)
    }

    /// The generator's O(1) state (member indices 0 / 1; race code 0, 1 or `double`).
    struct Gen {
        var ladderLast: Int?, ladderRun = 0, raceLast: Int?, raceRun = 0, lastDouble: Int?
    }

    /// The picks (ladder index, race code) of weeks 0…n−1, in order.
    static func picks(count n: Int, _ rot: EventRules.Rotation) -> [(ladder: Int, race: Int)] {
        var out: [(ladder: Int, race: Int)] = []
        out.reserveCapacity(max(0, n))
        var g = Gen()
        for w in 0..<max(0, n) { out.append(step(&g, w, rot)) }
        return out
    }

    /// The picks of week `w` only (the same iteration, keeping nothing).
    static func pick(week w: Int, _ rot: EventRules.Rotation) -> (ladder: Int, race: Int) {
        var g = Gen()
        var last = (ladder: 0, race: 0)
        for x in 0...max(0, w) { last = step(&g, x, rot) }
        return last
    }

    /// One week of the state machine (rotation_ref.py `Rotation._step`).
    static func step(_ g: inout Gen, _ w: Int, _ rot: EventRules.Rotation) -> (ladder: Int, race: Int) {
        let seed = rot.seedValue
        let maxRun = max(1, rot.maxRun), gap = max(1, rot.doubleMinGap)
        let pin = rot.pins[String(w)]
        // ladder
        let lad: Int
        if let pin, let i = rot.ladder.firstIndex(of: pin.ladder) {
            lad = i
        } else if let last = g.ladderLast {
            if g.ladderRun >= maxRun { lad = 1 - last } else {
                lad = SocialHash.u01(seed, lLadder, w) < rot.pSwitch ? 1 - last : last
            }
        } else {
            lad = SocialHash.u01(seed, lLadder, w) < 0.5 ? 0 : 1
        }
        g.ladderRun = lad == g.ladderLast ? g.ladderRun + 1 : 1
        g.ladderLast = lad
        // race
        let rac: Int
        if let pin, pin.race == "double" || rot.race.contains(pin.race) {
            rac = pin.race == "double" ? double : rot.race.firstIndex(of: pin.race)!
        } else {
            let dblOK = w > 0 && (g.lastDouble.map { w - $0 >= gap } ?? true)
            if dblOK && SocialHash.u01(seed, lDouble, w) < rot.pDouble {
                rac = double
            } else if let last = g.raceLast {
                if g.raceRun >= maxRun { rac = 1 - last } else {
                    rac = SocialHash.u01(seed, lRace, w) < rot.pSwitch ? 1 - last : last
                }
            } else {
                rac = SocialHash.u01(seed, lRace, w) < 0.5 ? 0 : 1
            }
        }
        if rac == double {
            g.lastDouble = w
        } else {
            g.raceRun = rac == g.raceLast ? g.raceRun + 1 : 1
            g.raceLast = rac
        }
        return (lad, rac)
    }

    static func makePlan(_ w: Int, _ p: (ladder: Int, race: Int), _ r: EventRules) -> WeekPlan {
        let rot = r.rotation
        let race = p.race == double ? rot.race.map { EventID($0) } : [EventID(rot.race[p.race])]
        return WeekPlan(week: w, ladder: EventID(rot.ladder[p.ladder]), race: race, start: weekStart(w, r), end: weekStart(w + 1, r))
    }

    /// The calendar's picks of week `w` (pure; independent of `enabled` and of any player). w < 0 takes week 0's picks.
    public static func plan(week w: Int, rules r: EventRules) -> WeekPlan {
        makePlan(w, pick(week: w, r.rotation), r)
    }

    /// Weeks 0…n−1 in one pass (tests, SocialLab's week picker).
    public static func plans(count n: Int, rules r: EventRules) -> [WeekPlan] {
        picks(count: n, r.rotation).enumerated().map { makePlan($0.offset, $0.element, r) }
    }

    /// What a player who has reached `level` sees in week `w` (events.md §4.4; rotation_ref.py `live` / `live_all_on`).
    public static func live(week w: Int, level: Int, rules r: EventRules) -> LiveEvents {
        r.rotation.enabled ? live(picks: pick(week: w, r.rotation), level: level, r) : allOn(level: level, r)
    }

    /// The kill switch (`enabled` false): the v552 plan — the Claw, every race member, the always-on events, each behind its
    /// unlock; Up & Away never.
    static func allOn(level: Int, _ r: EventRules) -> LiveEvents {
        let rot = r.rotation
        func usable(_ id: String) -> Bool { !rot.unavailable.contains(id) && (r.unlockLevel(EventID(id)).map { level >= $0 } ?? false) }
        return LiveEvents(always: rot.always.filter(usable).map { EventID($0) }, ladder: usable(rot.ladder[0]) ? EventID(rot.ladder[0]) : nil,
                          race: rot.race.filter(usable).map { EventID($0) })
    }

    /// Segmentation of drawn picks (rotation on).
    static func live(picks p: (ladder: Int, race: Int), level: Int, _ r: EventRules) -> LiveEvents {
        let rot = r.rotation
        func unlocked(_ id: String) -> Bool { r.unlockLevel(EventID(id)).map { level >= $0 } ?? false }
        func usable(_ id: String) -> Bool { !rot.unavailable.contains(id) && unlocked(id) }
        let pick = rot.ladder[p.ladder], other = rot.ladder[1 - p.ladder]
        let ladder: String?
        if rot.unavailable.contains(pick) { ladder = usable(other) ? other : nil } else { ladder = unlocked(pick) ? pick : nil }
        let race: [String]
        if p.race == double {
            race = rot.race.filter(usable)
        } else if usable(rot.race[p.race]) {
            race = [rot.race[p.race]]
        } else {
            let o = rot.race[1 - p.race]
            race = usable(o) ? [o] : []
        }
        return LiveEvents(always: rot.always.filter(usable).map { EventID($0) }, ladder: ladder.map { EventID($0) },
                          race: race.map { EventID($0) })
    }

    /// The live set at `t` for a player at `level`.
    public static func live(at t: SocialTime, level: Int, rules r: EventRules) -> LiveEvents {
        live(week: week(t, r), level: level, rules: r)
    }

    public static func isLive(_ e: EventID, at t: SocialTime, level: Int, rules r: EventRules) -> Bool {
        live(at: t, level: level, rules: r).contains(e)
    }

    /// The start of the first week after `w` (within `horizon` weeks) in which `e` is live for this level; nil = none.
    public static func nextStart(of e: EventID, after w: Int, level: Int, rules r: EventRules, horizon: Int = 26) -> SocialTime? {
        for x in (w + 1)..<(w + 1 + max(0, horizon)) where live(week: x, level: level, rules: r).contains(e) {
            return weekStart(x, r)
        }
        return nil
    }
}
