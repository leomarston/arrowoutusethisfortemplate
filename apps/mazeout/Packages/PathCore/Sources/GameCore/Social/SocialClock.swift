import Foundation

// SOC1 (SPEC-architecture §4.11 invariant 5, SPEC-social §5; reference design/social/tools/socialsim/clock.py).
// The ◆ file calls exactly `SocialClockRules.now(wall:highWater:)`: keep it.
//
// simNow = max(deviceNow, highWater); highWater is raised on every read (and persisted with the player save). Setting the
// device clock back therefore FREEZES the world until real time catches up: no score, rank, race or countdown rewinds
// (the same rule as the lives: "a clock set back never punishes"). Forward jumps are accepted (events end early — the
// user's own doing, as with a real server's time). One exception: a clock that was more than 30 days in the future and
// got repaired would otherwise freeze the world for a month, so it REBASES once (highWater = deviceNow); the only case in
// which displayed values may drop (SPEC-social §5, tested).

public enum SocialClockRules {
    /// A repaired clock more than this far behind the high-water mark rebases instead of freezing (SPEC-social §5).
    public static let rebaseAfter: Int64 = 30 * 86_400

    /// Effective world time in whole epoch seconds (floor) and the raised high-water mark.
    static func now(wall: Date, highWater: inout Int64) -> SocialTime {
        advance(wall: wall, highWater: &highWater).time
    }

    /// `now` plus whether this read rebased the clock (the app logs `social.clock.rebase` and settles open events with
    /// their stored state when it did).
    public static func advance(wall: Date, highWater: inout Int64) -> (time: SocialTime, rebased: Bool) {
        let device = Int64(wall.timeIntervalSince1970.rounded(.down))
        if highWater - device > rebaseAfter {
            highWater = device
            return (SocialTime(seconds: device), true)
        }
        if device > highWater { highWater = device }
        return (SocialTime(seconds: highWater), false)
    }
}
