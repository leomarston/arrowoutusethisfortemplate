import XCTest
import SwiftUI
import PathCore
@testable import ArrowOut

/// SHELL S3 (SPEC-architecture §12.2 S3). Hosted checks of the home completion, the Shop, Profile and the meta popups:
/// - FakeStore: 12 products at the device region's price list (TL for TR, US $ elsewhere), `isTestStore`, a purchase grants
///   once through Economy.applyPurchase and is saved; a replayed transaction id grants nothing;
/// - the shop's number formats (thin-space thousands, TL / $ prices, durations) and its layout (the test-store row, the section
///   pitches, the Special section collapsing once bought);
/// - the username rules (3-16, letters of any script, digits, "_", no `player_…`, the blocklists) and the name + avatar round
///   trip through PlayerStore across a "relaunch";
/// - the payout plan and timeline (SPEC-motion-audio §8.3: C0 = H + 0.35 alone, A-end + 0.40 after the Claw, B0 + 1.25 after
///   the strip; A's end H + 2.11 for 7 ticks; landings C0 + 0.77 + 0.085·k; N/5 shares with the remainder last);
/// - the countdown format (CONSISTENCY S-32), the avatar table (V-24: 0 … 8), the S3 popups registered with the host;
/// - every ui.json key the S3 code reads exists.
@MainActor final class ShellS3Tests: XCTestCase {
    private let tuning = Tuning.load(bundle: .main)

    private func tempStore(_ name: String) -> (PlayerStore, URL) {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("s3-\(name)-\(UUID().uuidString)")
        return (PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05), dir)
    }

    // MARK: FakeStore

    func testFakeStoreRegionPricesAndTestNote() {
        let rules = ShellEconomy.rules(tuning)
        let (store, dir) = tempStore("prices")
        defer { try? FileManager.default.removeItem(at: dir) }
        let clock = MotionClock(args: LaunchArgs())
        let tr = FakeStore(rules: rules, region: "TR", store: store, clock: clock)
        let us = FakeStore(rules: rules, region: "US", store: store, clock: clock)
        XCTAssertTrue(tr.isTestStore, "the Shop shows 'Test store: nothing is charged'")
        XCTAssertEqual(tr.products.count, 12)
        XCTAssertEqual(tr.products.map(\.id), rules.shop.storeIDs)
        XCTAssertEqual(tr.products.first?.displayPrice, "49,99 TL", "VERIFIED meta-012 on the TR phone")
        XCTAssertEqual(tr.products.first { $0.id.hasSuffix("bundle.mega") }?.displayPrice, "2.499,99 TL")
        XCTAssertEqual(us.products.first?.displayPrice, "$0.99")
        XCTAssertEqual(us.products.last?.displayPrice, "$99.99")
    }

    func testFakeStorePurchaseGrantsOnceAndPersists() async throws {
        let rules = ShellEconomy.rules(tuning)
        let (store, dir) = tempStore("buy")
        defer { try? FileManager.default.removeItem(at: dir) }
        let fake = FakeStore(rules: rules, region: "TR", store: store, clock: MotionClock(args: LaunchArgs()))
        fake.latency = 0.01
        let coins0 = store.state.coins, freeze0 = store.state.boosters["freeze"] ?? 0
        let outcome = await fake.purchase("com.manycode.arrowout.bundle.mini")
        XCTAssertEqual(outcome, .granted)
        XCTAssertEqual(store.state.coins, coins0 + 2000)
        XCTAssertEqual(store.state.boosters["freeze"], freeze0 + 1)
        XCTAssertNotNil(store.state.unlimitedLivesUntil)
        let tx = try XCTUnwrap(store.state.processedTransactions.first)
        XCTAssertNil(ShellEconomy.applyPurchase(store: store, rules: rules, productID: "com.manycode.arrowout.bundle.mini",
                                                transactionID: tx, now: Date()), "a replayed transaction grants nothing")
        XCTAssertEqual(store.state.coins, coins0 + 2000)
        store.flush()
        let again = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir)
        XCTAssertEqual(again.state.coins, coins0 + 2000, "saved at once (a purchase survives a kill)")
        let unknown = await fake.purchase("com.manycode.arrowout.nope")
        if case .failed = unknown {} else { XCTFail("unknown product must fail") }
    }

    // MARK: formats and the shop layout

    func testShopFormats() {
        XCTAssertEqual(ShopFormat.amount(1000), "1\u{2009}000")
        XCTAssertEqual(ShopFormat.amount(100_000), "100\u{2009}000")
        XCTAssertEqual(ShopFormat.amount(20), "20")
        XCTAssertEqual(ShopFormat.duration(3600), "1h")
        XCTAssertEqual(ShopFormat.duration(72 * 3600), "72h")
        XCTAssertEqual(ShopFormat.duration(1800), "30m")
        XCTAssertEqual(ShopFormat.list(region: "tr"), .tl)
        XCTAssertEqual(ShopFormat.list(region: nil), .usd)
    }

    func testShopLayoutFollowsMeta012() {
        let rules = ShellEconomy.rules(tuning)
        let all = rules.shop.products
        let l = ShopLayout(products: all, testStore: true)
        XCTAssertEqual(l.offer?.top ?? 0, 190.2 - 115 + 30, accuracy: 1e-9, "the test-store row moves the sections down 30 pt")
        XCTAssertEqual(l.bundles.count, 5)
        XCTAssertEqual(l.bundles[0].top, 472.7 - 115 + 30, accuracy: 1e-6)
        XCTAssertEqual(l.bundles[4].top - l.bundles[0].top, 4 * 203.5, accuracy: 1e-6)
        XCTAssertEqual(l.coins.count, 6)
        XCTAssertEqual(l.coins[3].top - l.coins[0].top, 171.8, accuracy: 1e-6)
        let bought = ShopLayout(products: all.filter { $0.section != "offer" }, testStore: true)
        XCTAssertNil(bought.offer)
        XCTAssertEqual(l.bundles[0].top - bought.bundles[0].top, 213.5, accuracy: 1e-6, "the Special section collapses")
    }

    // MARK: username + avatar

    func testUsernameRules() {
        func ok(_ s: String) -> Bool { if case .ok = Usernames.check(s) { return true }; return false }
        XCTAssertTrue(ok("Hsheh"))
        XCTAssertTrue(ok("Ayşe_99"), "letters of any script, digits, _")
        XCTAssertTrue(ok("ab_"))
        XCTAssertFalse(ok("ab"), "3-16 characters")
        XCTAssertFalse(ok("abcdefghijklmnopq"), "17 characters")
        XCTAssertFalse(ok("hello world"), "no spaces")
        XCTAssertFalse(ok("player_1234567"), "a default-shaped name")
        // a name from the bundled blocklist (read at run time so no blocked word lives in this file). B2: the app ships the v2
        // name bank as ONE file (Social/social_names.json; the v1 .txt copies are gone), so the entry comes from its lists
        let json = (try? Data(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("Social/social_names.json")))
            .flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
        let blocked = ((json?["blockNames"] as? [String] ?? []) + (json?["blockToken"] as? [String] ?? []))
            .first { (3...16).contains($0.count) && $0.allSatisfy { $0.isLetter } }
        XCTAssertNotNil(blocked, "the bundled name bank carries a blocklist")
        XCTAssertFalse(ok(blocked ?? "x"), "a blocklisted name (\(blocked?.count ?? 0) letters) is refused")
        // B2 (social-intl P2-4): two characters suffice for Hangul / Han / kana names, 3 elsewhere
        XCTAssertTrue(ok("민수")); XCTAssertTrue(ok("小明")); XCTAssertTrue(ok("たろ"))
        XCTAssertFalse(ok("민"), "one character never")
    }

    func testNameAndAvatarRoundTripPersists() throws {
        let (store, dir) = tempStore("profile")
        defer { try? FileManager.default.removeItem(at: dir) }
        XCTAssertNil(store.state.social.username)
        XCTAssertEqual(store.state.social.avatar, 0)
        guard case .ok(let name) = Usernames.check("  Hsheh ") else { return XCTFail("valid name refused") }
        store.mutateAndSave { $0.social.username = name; $0.social.avatar = 5 }
        store.flush()
        let again = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir)
        XCTAssertEqual(again.state.social.username, "Hsheh")
        XCTAssertEqual(again.state.social.avatar, 5)
        XCTAssertEqual(again.state.social.displayName(installSeed: again.state.installSeed), "Hsheh")
        // A4 ART-INTEG (R2 CAST, requirement change owner item 1 / ruling 37b: new characters): slot 5 keeps its place in the
        // 9-slot order (the social engine indexes slots, not names) and now holds the D1 boss portrait — same exact equality
        XCTAssertEqual(Avatars.art(5), .avatar5)
        XCTAssertEqual(Avatars.count, 9, "default + 8 portraits (CONSISTENCY V-24)")
        XCTAssertEqual(Avatars.art(14), .avatar0, "out of range → the silhouette")
    }

    // MARK: payout

    func testPayoutTimelineFollowsSegmentAnchors() {
        let tm = HomeReturnTiming(tuning.ui.tokens)
        let alone = PayoutPlan(claw: nil, streak: nil, coins: 120)
        XCTAssertEqual(alone.timeline(tm).c0, 0.35, accuracy: 1e-9)
        let clawOnly = PayoutPlan(claw: .init(added: 25, total: 165, target: 300, multiplier: 25), streak: nil, coins: 20)
        XCTAssertEqual(clawOnly.timeline(tm).aEnd, 2.11, accuracy: 0.002, "7 ticks: A ends at H + 2.11")
        XCTAssertEqual(clawOnly.timeline(tm).c0, 2.11 + 0.40, accuracy: 0.002)
        let full = PayoutPlan(claw: .init(added: 25, total: 165, target: 300, multiplier: 25), streak: .init(from: 25, to: 100, flags: 25), coins: 20)
        XCTAssertEqual(full.timeline(tm).b0 ?? 0, 2.11, accuracy: 0.002)
        XCTAssertEqual(full.timeline(tm).c0, 2.11 + 1.25, accuracy: 0.002)
        let streakOnly = PayoutPlan(claw: nil, streak: .init(from: 5, to: 10, flags: 5), coins: 20)
        XCTAssertEqual(streakOnly.timeline(tm).c0, 0.10 + 1.25, accuracy: 1e-9)
        let x1 = PayoutPlan(claw: .init(added: 1, total: 1, target: 1, multiplier: 1), streak: nil, coins: 20)
        XCTAssertEqual(x1.timeline(tm).clawShift, -0.73, accuracy: 1e-9)
        let spec = tm.coins
        XCTAssertEqual(spec.landing(0), 0.77, accuracy: 1e-9)
        XCTAssertEqual(spec.landing(4), 0.77 + 4 * 0.085, accuracy: 1e-9)
        XCTAssertEqual(spec.shares(120), [24, 24, 24, 24, 24], "1000 → 1024 … 1120 (VERIFIED vflows §6)")
        XCTAssertEqual(spec.shares(22), [4, 4, 4, 4, 6])
    }

    func testPayoutPlanReadsTheWinOutcomes() {
        let summary = WinSummary(levels: [39], reward: 20, tag: .normal,
                                 outcomes: [.multiplier(from: 25, to: 100), .clawPoints(added: 25, total: 165, target: 300), .streakRaceScore(25)])
        let p = PayoutPlan.make(entry: .afterWin(summary), pending: 20, clawRunning: true, streakRunning: true)
        XCTAssertEqual(p.claw?.added, 25)
        XCTAssertEqual(p.streak?.from, 25)
        XCTAssertEqual(p.streak?.to, 100)
        XCTAssertEqual(p.coins, 20)
        let locked = PayoutPlan.make(entry: .afterWin(summary), pending: 20, clawRunning: false, streakRunning: false)
        XCTAssertNil(locked.claw)
        XCTAssertNil(locked.streak)
        let first = PayoutPlan.make(entry: .firstHome(WinSummary(levels: [6], reward: 20, tag: .normal)), pending: 120,
                                    clawRunning: false, streakRunning: false)
        XCTAssertEqual(first, PayoutPlan(claw: nil, streak: nil, coins: 120), "the FTUE's first home: +120 only")
        XCTAssertTrue(PayoutPlan.make(entry: .normal, pending: 0, clawRunning: true, streakRunning: true).isEmpty)
    }

    func testCoinPillHidesTheBankedFly() {
        var s = PlayerState()
        s.coins = 1120
        s.pendingCoinFly = 120
        XCTAssertEqual(CoinPillDisplay.shared.shown(s), 1000, "the first home shows 1000 until the coins land")
    }

    // MARK: countdowns, popups, tokens

    func testCountdownFormat() {
        // REQUIREMENT CHANGE (FIX-2 lane B, L28 / F-10 — the phone wins, v582 PH-0a build/p/PH0a/before-reset.png): an exact
        // hour keeps its minutes ("2h 0m", as the win strip always read — was "2h"), and under an hour the countdown reads
        // mm:ss ("45:10", "00:20" — was "45m", "1m"). Same five cases, exact strings.
        let cases: [(Double, String)] = [(280_740, "3d 5h"), (18_820, "5h 13m"), (7_200, "2h 0m"), (2_710, "45:10"), (20, "00:20")]
        for (seconds, text) in cases { XCTAssertEqual(Countdown.text(seconds), text) }
    }

    func testS3PopupsAreRegistered() {
        for r: PopupRequest in [.username, .editProfile, .noLives, .boosterBuy(.hint), .custom(id: ShopPage.popupID, params: [:])] {
            XCTAssertTrue(PopupContent.hasPanel(r), "\(r.id) has a panel")
        }
        XCTAssertTrue(PopupContent.isPage(.custom(id: ShopPage.popupID, params: [:])), "the closable Shop is a full page")
        XCTAssertFalse(PopupContent.isPage(.noLives))
    }

    func testEveryS3TokenKeyIsInUIJson() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        let files = ["App/Shell/Home/ClawBar.swift", "App/Shell/Home/EventBadges.swift", "App/Shell/Home/HomeView.swift",
                     "App/Shell/Popups/NoLivesPopup.swift", "App/Shell/Popups/BoosterBuyPopup.swift", "App/Shell/Shop/ShopView.swift",
                     "App/Shell/Profile/ProfileView.swift"]
        let prefix = ["frame": "frames.", "text": "text.", "color": "colors.", "colors": "colors.", "number": ""]
        let re = try NSRegularExpression(pattern: #"\bt\.(frame|text|colors?|number)\("([A-Za-z0-9_.]+)""#)
        let file = tuning.ui.file
        var missing: [String] = []
        for f in files {
            let src = try String(contentsOf: root.appendingPathComponent(f), encoding: .utf8)
            for m in re.matches(in: src, range: NSRange(src.startIndex..., in: src)) {
                let kind = String(src[Range(m.range(at: 1), in: src)!]), key = String(src[Range(m.range(at: 2), in: src)!])
                if f.hasSuffix("HomeView.swift"), !key.hasPrefix("home.pile") { continue }        // S1's keys: ShellTests
                let full = (prefix[kind] ?? "") + key
                if !file.has(full) { missing.append("\(f): \(full)") }
            }
        }
        XCTAssertEqual(missing, [], "ui.json keys the S3 code reads")
    }
}
