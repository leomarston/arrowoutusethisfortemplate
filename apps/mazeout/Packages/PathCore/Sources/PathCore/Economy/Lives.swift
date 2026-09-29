import Foundation

// C3 (SPEC-architecture §4.8; SPEC-gameplay §8; VERIFIED research/economy.md §2/§2b, fail.md §6). Adapted from MF Lives
// (e10a076) with OUR rules:
// - max 5; a life is TAKEN when a level starts (Play / Try Again) and GIVEN BACK when that attempt is won (a failed or quit
//   attempt keeps it spent); `rules.lives.cost = .atLoss` is the architecture's first placeholder, kept as a switch.
// - one life per `refillSeconds` (1800, VERIFIED) on ONE continuous clock: `anchor` = the start of the running refill period,
//   the next life is due at `anchor + refillSeconds`; nil exactly when the count is full. The phase is set when the count
//   first drops below max (the level start that took it); a tick never restarts it; a refund never moves it.
//     take       if count == max { anchor = t }; count -= 1
//     tick       gained = floor((t − anchor) / refill); count = min(max, count + gained); anchor += gained × refill
//     give back  count += 1 (capped); anchor unchanged unless the count is full again (then nil)
// - unlimited lives (`unlimitedLivesUntil`): checked at the level START only; grants stack `until = max(until, t) + d`
//   (VERIFIED 30 m + 1 h = "1h 20m", L55). The chain keeps running underneath.
// - TIME: every decision uses `EconomyClock` = the ONE rewind-safe world clock (`SocialClock` over
//   `PlayerState.social.highWater`, whole seconds). A device clock set back therefore never grants a life, never shortens
//   an ∞ period's remaining time and never takes a life away: the chain waits until wall time catches up.

// MARK: - The clock

public enum EconomyClock {
    /// The effective time of lives, ∞ lives and events: `max(wall, highWater)` in whole seconds (the ◆ SocialClock), and
    /// the high-water mark is raised to it. If the clock's policy ever steps back (SPEC-social §5: a one-time rebase after a
    /// > 30-day future clock is repaired), the stored economy times move by the same step, so remaining durations are kept
    /// and nothing is granted by the step.
    public static func now(_ s: inout PlayerState, wall: Date) -> Date {
        Date(timeIntervalSince1970: Double(social(&s, wall: wall).seconds))
    }

    /// The same moment as a `SocialTime` (the events' calendar).
    public static func social(_ s: inout PlayerState, wall: Date) -> SocialTime {
        let before = s.social.highWater
        let t = SocialClock.now(wall: wall, highWater: &s.social.highWater)
        if before > 0, t.seconds < before { shift(&s, by: Double(t.seconds - before), from: SocialTime(seconds: before)) }
        return t
    }

    /// The effective time without raising the mark (read-only queries).
    public static func peek(_ s: PlayerState, wall: Date) -> Date {
        var c = s
        return now(&c, wall: wall)
    }

    /// `peek` as a `SocialTime`.
    public static func peekSocial(_ s: PlayerState, wall: Date) -> SocialTime {
        var c = s
        return social(&c, wall: wall)
    }

    /// True when the device clock is behind the high-water mark (it was set back): the economy is waiting for it.
    public static func isBehind(_ s: PlayerState, wall: Date) -> Bool {
        Int64(wall.timeIntervalSince1970.rounded(.down)) < s.social.highWater
    }

    /// Moves every stored absolute economy time by `delta` seconds (the rebase case only) and ends the event state that
    /// was stamped in the abandoned future (`Events.rebase`; `last` = the high-water mark before the step).
    static func shift(_ s: inout PlayerState, by delta: Double, from last: SocialTime) {
        if let a = s.lives.anchor { s.lives.anchor = a.addingTimeInterval(delta) }
        if let u = s.unlimitedLivesUntil { s.unlimitedLivesUntil = u.addingTimeInterval(delta) }
        if let a = s.activeAttempt { s.activeAttempt?.startedAt = a.startedAt.addingTimeInterval(delta) }
        Events.rebase(&s, to: SocialTime(seconds: s.social.highWater), from: last)
    }

    static func date(_ t: SocialTime) -> Date { Date(timeIntervalSince1970: Double(t.seconds)) }
    static func social(_ d: Date) -> SocialTime { SocialTime(seconds: Int64(d.timeIntervalSince1970.rounded(.down))) }
}

// MARK: - Status

public enum LivesStatus: Equatable, Sendable {
    case full
    case counting(count: Int, nextAt: Date)
    case unlimited(until: Date)
}

// MARK: - The chain (pure; the Economy calls these with the EFFECTIVE time)

extension Economy {
    /// True while a timed unlimited-lives reward runs at effective time `t`.
    static func unlimited(_ s: PlayerState, at t: Date) -> Bool {
        if let until = s.unlimitedLivesUntil, until > t { return true }
        return false
    }

    /// Whole refill periods completed from `anchor` to `t`.
    static func periods(since anchor: Date, to t: Date, _ r: EconomyRules.Lives) -> Int {
        let elapsed = t.timeIntervalSince(anchor)
        guard elapsed > 0, r.refillSeconds > 0 else { return 0 }
        return Int(((elapsed + r.refillEpsilon) / r.refillSeconds).rounded(.down))
    }

    /// Writes the refills due by `t` into the stored count and anchor and repairs an inconsistent pair (a count below max
    /// without an anchor starts the chain at `t`; an anchor after `t` — only after a clock rebase or a hand-made state — is
    /// clamped to `t`, which grants nothing; a negative count becomes 0). Returns the lives gained.
    @discardableResult
    static func normalizeLives(_ s: inout PlayerState, at t: Date, _ r: EconomyRules.Lives) -> Int {
        if s.lives.count < 0 { s.lives.count = 0 }
        guard s.lives.count < r.max else { s.lives.anchor = nil; return 0 }
        let anchor = min(s.lives.anchor ?? t, t)
        let gained = periods(since: anchor, to: t, r)
        let count = min(r.max, s.lives.count + gained)
        let added = count - s.lives.count
        s.lives.count = count
        s.lives.anchor = count >= r.max ? nil : anchor.addingTimeInterval(Double(gained) * r.refillSeconds)
        return added
    }

    /// Takes one life at `t` ("take"): the chain starts at `t` if the count was full.
    static func takeLife(_ s: inout PlayerState, at t: Date, _ r: EconomyRules.Lives) {
        normalizeLives(&s, at: t, r)
        guard s.lives.count > 0 else { return }
        if s.lives.count >= r.max { s.lives.anchor = t }
        s.lives.count -= 1
        if s.lives.count >= r.max { s.lives.anchor = nil }     // a debug count above max stays "full"
    }

    /// Gives one life back at `t` ("give back"): the running countdown is kept unless the count is full again.
    static func giveLifeBack(_ s: inout PlayerState, at t: Date, _ r: EconomyRules.Lives) {
        normalizeLives(&s, at: t, r)
        s.lives.count = min(r.max, s.lives.count + 1)
        if s.lives.count >= r.max { s.lives.anchor = nil }
    }

    /// Stacks an unlimited-lives duration at `t`: `until = max(until, t) + seconds`.
    static func addUnlimited(_ s: inout PlayerState, seconds: TimeInterval, at t: Date) {
        guard seconds > 0 else { return }
        let base = max(s.unlimitedLivesUntil ?? t, t)
        s.unlimitedLivesUntil = base.addingTimeInterval(seconds)
    }

    // MARK: public queries

    /// The lives pill: `.unlimited(until)` while ∞ runs, else `.full` or `.counting(count, nextAt)`.
    public static func lives(_ s: PlayerState, now: Date, rules: EconomyRules) -> LivesStatus {
        var c = s
        let t = EconomyClock.now(&c, wall: now)
        normalizeLives(&c, at: t, rules.lives)
        if unlimited(c, at: t), let u = c.unlimitedLivesUntil { return .unlimited(until: u) }
        if c.lives.count >= rules.lives.max { return .full }
        let anchor = c.lives.anchor ?? t
        return .counting(count: c.lives.count, nextAt: anchor.addingTimeInterval(rules.lives.refillSeconds))
    }

    /// The life count at `now` (refills applied; ∞ does not change the count).
    public static func livesCount(_ s: PlayerState, now: Date, rules: EconomyRules) -> Int {
        var c = s
        let t = EconomyClock.now(&c, wall: now)
        normalizeLives(&c, at: t, rules.lives)
        return c.lives.count
    }

    /// True while unlimited lives run at `now` (effective time).
    public static func hasUnlimitedLives(_ s: PlayerState, now: Date) -> Bool {
        unlimited(s, at: EconomyClock.peek(s, wall: now))
    }

    /// Seconds until the next life (nil when full or under ∞) or until ∞ ends — what the pill counts down.
    public static func countdown(_ s: PlayerState, now: Date, rules: EconomyRules) -> TimeInterval? {
        let t = EconomyClock.peek(s, wall: now)
        switch lives(s, now: now, rules: rules) {
        case .full: return nil
        case .counting(_, let next): return max(0, next.timeIntervalSince(t))
        case .unlimited(let until): return max(0, until.timeIntervalSince(t))
        }
    }

    /// When the count will be back at max (the "lives full" local notification, SPEC-gameplay §12.5); nil when full now.
    /// Unlimited lives do not change it (the chain runs underneath).
    public static func livesFullAt(_ s: PlayerState, now: Date, rules: EconomyRules) -> Date? {
        var c = s
        let t = EconomyClock.now(&c, wall: now)
        normalizeLives(&c, at: t, rules.lives)
        guard c.lives.count < rules.lives.max else { return nil }
        let anchor = c.lives.anchor ?? t
        return anchor.addingTimeInterval(Double(rules.lives.max - c.lives.count) * rules.lives.refillSeconds)
    }

    /// Applies the refills that are due (the launch / foreground reconcile uses it). Returns the lives gained.
    @discardableResult
    public static func refreshLives(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> Int {
        let t = EconomyClock.now(&s, wall: now)
        let gained = normalizeLives(&s, at: t, rules.lives)
        if let u = s.unlimitedLivesUntil, u <= t { s.unlimitedLivesUntil = nil }
        return gained
    }

    /// "Refill [coin] 900" (More Lives): coins − `refillPrice`, lives to max. False (nothing changes) when full, under ∞, or
    /// short of coins.
    public static func refillLives(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> Bool {
        let t = EconomyClock.now(&s, wall: now)
        normalizeLives(&s, at: t, rules.lives)
        guard s.lives.count < rules.lives.max, !unlimited(s, at: t) else { return false }
        guard spend(&s, rules.lives.refillPrice) else { return false }
        s.lives.count = rules.lives.max
        s.lives.anchor = nil
        return true
    }

    /// Debug / launch-argument helper (`-pc.lives N -pc.livesNextIn S`): `count` lives with the next one due in `nextIn`
    /// seconds (default: a full period).
    public static func setLives(_ s: inout PlayerState, count: Int, nextIn: TimeInterval? = nil, now: Date, rules: EconomyRules) {
        let t = EconomyClock.now(&s, wall: now)
        let r = rules.lives
        s.lives.count = max(0, count)
        if s.lives.count >= r.max { s.lives.anchor = nil; return }
        let next = min(max(nextIn ?? r.refillSeconds, 0), r.refillSeconds)
        s.lives.anchor = t.addingTimeInterval(next - r.refillSeconds)
    }
}
