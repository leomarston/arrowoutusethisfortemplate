import SwiftUI
import PathCore

// Kit component `economy-ui` (kit/economy/economy-ui): the economy's display helpers every coin- or reward-drawing screen shares
// (the Shop, the lives and booster popups, the home bars, the event pages). Moved as they were in the kit decoupling step:
// `ShopTitles` and `ShopFormat` from ShopEconomy.swift (whose `ShellEconomy` — the economy table itself — stays in core: the
// shell's own event-art and rotation policies read it), `CoinPillDisplay` from the home's PayoutSequence.swift, `LivesText`
// (the lives pill / timer texts) from the home's HomeTopBar.swift (the More Lives popup draws its clock too).

/// The catalogue's titles and the section a product sits in (SPEC-gameplay §9.4, §16.8; strings keys = these literals).
enum ShopTitles {
    static func title(_ p: ShopProduct) -> LocalizedStringResource {
        switch p.id {
        case "offer.special": return "Special Offer"
        case "bundle.mini": return "Mini Bundle"
        case "bundle.epic": return "Epic Bundle"
        case "bundle.elite": return "Elite Bundle"
        case "bundle.mega": return "Mega Bundle"
        case "bundle.legendary": return "Legendary Bundle"
        default: return "Coins"
        }
    }

    /// The English title (StoreProductInfo.displayName and the logs; the page draws `title`).
    static func english(_ p: ShopProduct) -> String {
        switch p.id {
        case "offer.special": return "Special Offer"
        case "bundle.mini": return "Mini Bundle"
        case "bundle.epic": return "Epic Bundle"
        case "bundle.elite": return "Elite Bundle"
        case "bundle.mega": return "Mega Bundle"
        case "bundle.legendary": return "Legendary Bundle"
        default: return "\(ShopFormat.amount(p.grant.coins)) Coins"
        }
    }
}

/// Number formats of the shop (SPEC-ui §2.12.2: a thin space groups thousands, "1 000", in both languages). Money is never
/// formatted here: the Shop shows StoreKit's `displayPrice` (A1, release-plan §3.2); the DEBUG FakeStore's reference price
/// lists live in FakeStore.swift (DEBUG only).
enum ShopFormat {
    /// "1 000", "60 000", "100 000" (U+2009 THIN SPACE, VERIFIED EN on a TR phone).
    static func amount(_ n: Int) -> String {
        let digits = String(abs(n))
        var out = ""
        for (i, ch) in digits.enumerated() {
            if i > 0 && (digits.count - i) % 3 == 0 { out.append("\u{2009}") }
            out.append(ch)
        }
        return (n < 0 ? "-" : "") + out
    }

    /// "1h", "3h", "72h" for an unlimited-lives duration; "30m" below an hour.
    static func duration(_ seconds: Double) -> String {
        let m = Int((seconds / 60).rounded())
        return m >= 60 && m % 60 == 0 ? "\(m / 60)h" : (m >= 60 ? "\(m / 60)h \(m % 60)m" : "\(m)m")
    }
}

/// What the home coin pills show: the banked coins minus what has not landed yet (`pendingCoinFly` before the sequence takes
/// it, then the coins still flying).
@MainActor @Observable final class CoinPillDisplay {
    static let shared = CoinPillDisplay()
    var flying = 0
    func shown(_ s: PlayerState) -> Int { max(0, s.coins - max(0, s.pendingCoinFly) - flying) }
}

/// The lives pill's text and its accessibility value (`home.lives`: "n|mm:ss|full|inf:mm:ss", §9.8). SPEC-ui §2.2.2: counting
/// "mm:ss" (always two-digit minutes); the word "Finished" for ≈ 1 s when a life has just arrived; unlimited "mm:ss" below an
/// hour, "1h 20m" from an hour.
enum LivesText {
    enum Pill: Equatable { case full, finished, time(String) }

    static func state(_ s: PlayerState, now: Date, refill: Double) -> Pill {
        if let until = s.unlimitedLivesUntil, until > now {
            let left = until.timeIntervalSince(now)
            return .time(left >= 3600 ? hoursMinutes(left) : clock(left))
        }
        guard s.lives.count < 5 else { return .full }
        guard let anchor = s.lives.anchor else { return .time(clock(refill)) }
        let elapsed = now.timeIntervalSince(anchor)
        let period = max(refill, 1)
        if elapsed >= period, elapsed.truncatingRemainder(dividingBy: period) < 1 { return .finished }
        return .time(clock(max(0, period - elapsed.truncatingRemainder(dividingBy: period))))
    }

    /// nil = "Full" / "Finished"; else the time text.
    static func pill(_ s: PlayerState, now: Date, refill: Double) -> String? {
        if case .time(let t) = state(s, now: now, refill: refill) { return t }
        return nil
    }

    static func value(_ s: PlayerState, now: Date, refill: Double) -> String {
        if let until = s.unlimitedLivesUntil, until > now, case .time(let shown) = state(s, now: now, refill: refill) {
            return "inf:" + shown                                   // CONSISTENCY Y-4: "inf:<the displayed text>"
        }
        switch state(s, now: now, refill: refill) {
        case .full: return "full"
        case .finished: return "\(s.lives.count)|finished"
        case .time(let t): return "\(s.lives.count)|\(t)"
        }
    }

    /// mm:ss (h:mm:ss above an hour: the accessibility value).
    static func clock(_ seconds: Double) -> String {
        let t = Int(seconds.rounded(.up))
        let h = t / 3600, mnt = (t % 3600) / 60, sec = t % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, mnt, sec) : String(format: "%02d:%02d", mnt, sec)
    }

    /// "1h 20m" (units are the original's letters in both languages).
    static func hoursMinutes(_ seconds: Double) -> String {
        let t = Int(seconds.rounded(.up))
        return "\(t / 3600)h \(((t % 3600) / 60))m"
    }
}
