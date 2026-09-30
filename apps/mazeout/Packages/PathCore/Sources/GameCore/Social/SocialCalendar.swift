import Foundation

// SOC1 (SPEC-social §1.2, §4.1; SPEC-architecture §4.11 invariant 4). The event calendar of the offline world, a port of
// the calendar part of design/social/tools/socialsim/core.py. Event days start 07:00 UTC, weeks start Monday 07:00 UTC
// (12 countdowns on the owner's phone all ended at 10:00 TRT = 07:00 UTC). The world epoch is the original's launch day.

public enum SocialCalendar {
    /// The event-day anchor (a Monday 07:00 UTC; the reference game's is 2026-04-27): game.yml social.calendar_epoch, via
    /// the generated GameConfig.
    public static let epoch: Int = GameConfig.calendarEpoch
    public static let day: Int = 86_400
    public static let week: Int = 7 * 86_400
    /// The UTC day number of the epoch (floor(epoch / 86400); the reference game's: 20_570 = 2026-04-27).
    public static let epochUTCDay: Int = SocialHash.floorDiv(GameConfig.calendarEpoch, 86_400)

    /// Event day index (days start at 07:00 UTC).
    public static func eventDay(_ t: Int) -> Int { SocialHash.floorDiv(t - epoch, day) }
    /// Event day of a fractional time (core.event_day's float path: floor((t − EPOCH) / DAY) in doubles).
    public static func eventDay(_ t: Double) -> Int { SocialHash.floorInt((t - Double(epoch)) / Double(day)) }
    /// Event week index (weeks start Monday 07:00 UTC).
    public static func eventWeek(_ t: Int) -> Int { SocialHash.floorDiv(t - epoch, week) }
    public static func eventWeek(_ t: Double) -> Int { SocialHash.floorInt((t - Double(epoch)) / Double(week)) }
    public static func eventDayStart(_ d: Int) -> Int { epoch + d * day }
    public static func eventWeekStart(_ w: Int) -> Int { epoch + w * week }

    /// Local calendar day number (days since 1970-01-01 in local time) and minute of the day in [0, 1440).
    /// (core.local_day_minute: `ls = t + off·60`, `d = floordiv(floor(ls), DAY)`, `minute = (ls − d·DAY) / 60`.)
    @inline(__always)
    public static func localDayMinute(_ t: Double, offsetMinutes off: Int) -> (day: Int, minute: Double) {
        let ls = t + Double(off * 60)
        let d = SocialHash.floorDiv(SocialHash.floorInt(ls), day)
        return (d, (ls - Double(d * day)) / 60.0)
    }

    /// 0 = Monday … 6 = Sunday (1970-01-01 was a Thursday).
    public static func dayOfWeek(localDay d: Int) -> Int { SocialHash.posMod(d + 3, 7) }

    /// Countdown text as every captured timer shows it (floored): "Xd Yh" above one day, else "Xh Ym" (SPEC-social §4.1).
    /// Returns the numbers; the UI formats them ("3d 6h", "9h 50m").
    public static func countdown(seconds: Int) -> (big: Int, small: Int, days: Bool) {
        let s = max(0, seconds)
        if s >= day { return (s / day, (s % day) / 3600, true) }
        return (s / 3600, (s % 3600) / 60, false)
    }

    /// Seconds until the end of the event day / week that contains `t`.
    public static func secondsToDayEnd(_ t: Int) -> Int { eventDayStart(eventDay(t) + 1) - t }
    public static func secondsToWeekEnd(_ t: Int) -> Int { eventWeekStart(eventWeek(t) + 1) - t }
}
