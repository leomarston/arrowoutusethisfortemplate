import Foundation

// C3 — B1 EVENTS-P (events.md §6.4; SPEC.md ruling 38 "event notifications on (≤ 1/day, daytime)"; ruling 5: the permission
// is asked once, as before — this is more USE of it). The pure planner of the offline event notifications; GAME's
// `LocalNotifications` schedules its items at every background (only with Settings' Notifications ON and iOS's permission)
// and cancels everything at every foreground.
//   weeklyEnding  (existing, unchanged) `weeklyEndingHours` before the Weekly Contest's end, when the player joined this week's
//                 contest; a fixed moment, not moved into the window.
//   eventEnding   the week's live ladder event (Treasure Climb / Up & Away) when the player has progress in it and has not
//                 finished it: 3 h before the Monday 07:00 UTC end when that local time is inside the window ("… ends in 3
//                 hours!"), else at the window's last moment before it ("… ends soon!").
//   eventStart    next week's featured events that this week does not have (for this player's level): at the first local time
//                 ≥ the week start inside the window (else the window's start the next morning). A Double Event Week reads
//                 as one. Nothing new next week → nothing.
// At most ONE event notification in any 24 h, the last delivered one included (EventNotifyState.lastAt); priority
// weeklyEnding > eventEnding > eventStart. An ending is dropped when it would break the cap; a start moves to the first
// in-window time 24 h after the one it collides with (at most 3 days into its week), else it is dropped.
// Every eventStart / eventEnding fires inside [notifyWindow[0]:00, notifyWindow[1]:00] LOCAL time (the device's time zone,
// DST included).

/// The event notifications scheduled at the last background, and the last one delivered (the cap's memory).
public struct EventNotifyState: Codable, Sendable, Equatable {
    /// Kind raw value → fire time (epoch seconds) of what the last background scheduled.
    public var pending: [String: Int64] = [:]
    /// The fire time of the last event notification that was delivered.
    public var lastAt: Int64?

    public init(pending: [String: Int64] = [:], lastAt: Int64? = nil) { self.pending = pending; self.lastAt = lastAt }

    enum CodingKeys: String, CodingKey { case pending, lastAt }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        pending = try c.v(.pending, [:]); lastAt = try c.decodeIfPresent(Int64.self, forKey: .lastAt)
    }
}

public enum EventNotifications {
    public enum Kind: String, Codable, Sendable, CaseIterable { case weeklyEnding, eventEnding, eventStart }

    public struct Item: Equatable, Sendable {
        public var kind: Kind
        /// Fire time, epoch seconds.
        public var at: Int64
        /// eventStart: the new featured events (ladder first); eventEnding: the ladder event; weeklyEnding: the Weekly Contest.
        public var events: [EventID]
        /// eventStart on a Double Event Week (both race events).
        public var double = false
        /// eventEnding exactly 3 h before the end ("… ends in 3 hours!"); false = earlier ("… ends soon!").
        public var threeHours = false

        public init(kind: Kind, at: Int64, events: [EventID], double: Bool = false, threeHours: Bool = false) {
            self.kind = kind; self.at = at; self.events = events; self.double = double; self.threeHours = threeHours
        }
    }

    public static let gap: Int64 = 86_400
    public static let endingLead: Int64 = 3 * 3600

    /// Foreground (and the start of every plan): a pending notification whose time has passed was delivered while the game was
    /// away; the rest were cancelled.
    public static func foreground(_ s: inout PlayerState, now: Date) {
        let wall = Int64(now.timeIntervalSince1970.rounded(.down))
        let fired = s.events.notify.pending.values.filter { $0 <= wall }
        if let last = fired.max() { s.events.notify.lastAt = max(s.events.notify.lastAt ?? last, last) }
        s.events.notify.pending = [:]
    }

    /// Records what the background scheduled.
    public static func record(_ s: inout PlayerState, _ items: [Item]) {
        s.events.notify.pending = Dictionary(items.map { ($0.kind.rawValue, $0.at) }, uniquingKeysWith: { a, _ in a })
    }

    /// Seconds since local midnight of the instant `t` in `zone`.
    static func localSecond(_ t: Int64, _ zone: TimeZone) -> Int64 {
        let off = Int64(zone.secondsFromGMT(for: Date(timeIntervalSince1970: Double(t))))
        let x = (t + off) % 86_400
        return x < 0 ? x + 86_400 : x
    }

    /// `t` lies inside the local window [from:00, to:00].
    public static func inWindow(_ t: Int64, zone: TimeZone, window: [Int]) -> Bool {
        let sod = localSecond(t, zone)
        return sod >= Int64(window[0]) * 3600 && sod <= Int64(window[1]) * 3600
    }

    /// The first instant ≥ `t` inside the window.
    public static func firstInWindow(atOrAfter t: Int64, zone: TimeZone, window: [Int]) -> Int64 {
        var x = t
        for _ in 0..<4 where !inWindow(x, zone: zone, window: window) {
            let sod = localSecond(x, zone)
            let from = Int64(window[0]) * 3600
            x += sod < from ? from - sod : 86_400 - sod + from
        }
        return x
    }

    /// The last instant ≤ `t` inside the window.
    public static func lastInWindow(atOrBefore t: Int64, zone: TimeZone, window: [Int]) -> Int64 {
        var x = t
        for _ in 0..<4 where !inWindow(x, zone: zone, window: window) {
            let sod = localSecond(x, zone)
            let to = Int64(window[1]) * 3600
            x -= sod > to ? sod - to : sod + (86_400 - to)
        }
        return x
    }

    /// The notifications to schedule at `now` (in firing order). `weeklyEndingHours` nil = that reminder is off.
    public static func plan(_ s0: PlayerState, now: Date, rules: EconomyRules, zone: TimeZone,
                            weeklyEndingHours: Double? = 2) -> [Item] {
        var s = s0
        foreground(&s, now: now)                          // what fired since the last background counts in the cap
        let wall = Int64(now.timeIntervalSince1970.rounded(.down))
        let ev = rules.events
        let window = ev.rotation.notifyWindow
        let status = Events.status(s, now: now, rules: rules)
        let t = EconomyClock.peekSocial(s, wall: now)
        let w = EventRotation.week(t, ev)
        let weekEnd = EventRotation.weekStart(w + 1, ev).seconds
        var cands: [Item] = []
        // weeklyEnding (the existing reminder)
        if let hours = weeklyEndingHours, let wk = status.weekly, wk.joined {
            cands.append(Item(kind: .weeklyEnding, at: wk.endsAt.seconds - Int64((hours * 3600).rounded(.down)), events: [.weeklyContest]))
        }
        // eventEnding: the live ladder event with progress, not finished
        var ladder: EventID?
        if let c = status.claw, !c.complete, c.points > 0 || c.step > 1 { ladder = .clawChallenge }
        if let b = status.balloon, !b.complete, b.streak > 0 || b.paid > 0 { ladder = .balloonRise }
        if let ladder {
            let ideal = weekEnd - endingLead
            let at = inWindow(ideal, zone: zone, window: window) ? ideal : lastInWindow(atOrBefore: ideal, zone: zone, window: window)
            cands.append(Item(kind: .eventEnding, at: at, events: [ladder], threeHours: at == ideal))
        }
        // eventStart: next week's new featured events
        let here = status.live.featured
        let next = EventRotation.live(week: w + 1, level: s.level, rules: ev)
        let fresh = next.featured.filter { !here.contains($0) }
        if !fresh.isEmpty {
            let start = EventRotation.weekStart(w + 1, ev).seconds
            let double = next.race.count > 1 && fresh.contains(where: { next.race.contains($0) })
            cands.append(Item(kind: .eventStart, at: firstInWindow(atOrAfter: start, zone: zone, window: window), events: fresh,
                              double: double))
        }
        // the cap, in priority order
        var taken: [Int64] = s.events.notify.lastAt.map { [$0] } ?? []
        var out: [Item] = []
        for var c in cands {
            guard c.at > wall + 1 else { continue }
            var clash = taken.filter { abs($0 - c.at) < gap }
            if c.kind == .eventStart, !clash.isEmpty {
                let latest = EventRotation.weekStart(w + 1, ev).seconds + 3 * 86_400
                var at = c.at
                for _ in 0..<4 where !clash.isEmpty {
                    at = firstInWindow(atOrAfter: clash.max()! + gap, zone: zone, window: window)
                    clash = taken.filter { abs($0 - at) < gap }
                }
                guard clash.isEmpty, at <= latest else { continue }
                c.at = at
            }
            guard clash.isEmpty else { continue }
            taken.append(c.at)
            out.append(c)
        }
        return out.sorted { $0.at < $1.at }
    }
}
