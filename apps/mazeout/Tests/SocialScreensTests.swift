import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// SOCIAL SOC2 (SPEC-architecture §12.2 SOC2 acceptance; CONSISTENCY V-29 "social = 0 ms main thread"; SPEC.md §5.24). Hosted
/// checks of the social screens' data path and list engine:
/// - determinism: two worlds with the same install seed at the same time give identical rows on every board (World, Country,
///   Weekly, Streak Race) — the "two launches render identical rows" acceptance, at the snapshot level;
/// - rewind safety: a device clock set back (the SocialClock high-water mark) shows the later world, never less progress;
/// - list composition (SPEC-social §3.3 / CONSISTENCY V-19, V-20): World 1-100 + "• • •" + R ± 10 with the player's green row;
///   Country continuous to R + 10 while R ≤ 600; Weekly group of 10 (podium 1-3 + rows 4-10); Streak Race 50 rows with the
///   2000 / 1000 / 500 / 100 × 7 prizes;
/// - the CA list recycles (≈ a screenful of row views whatever the length), pins the player's row at the edges, and publishing
///   a 440-row snapshot on the main thread stays under a frame's budget; shaping is safe from many threads at once;
/// - scenarios drive C3's real state machines (Rocket Race lanes: the player + 4 rivals; Sky Jump: the attempt's curve);
/// - honesty: no SOC2 source or string says the players are simulated, bots, or online (SPEC.md §5.24).
@MainActor final class SocialScreensTests: XCTestCase {
    private let tuning = Tuning.load(bundle: .main)
    private lazy var rules = ShellEconomy.rules(tuning)
    private lazy var names: NameBank = {
        (try? NameBank.load(folder: Bundle.main.resourceURL!.appendingPathComponent("Social"))) ?? NameBank()
    }()
    /// 25 Sep 2026 12:00 UTC (the capture clock).
    private let t0 = Date(timeIntervalSince1970: 1_790_337_600)
    /// t0 + 19 weeks = Fri 5 Feb 2027 12:00 UTC. B2 (requirement change, ruling 39 OD9: the shipped v2 world starts
    /// 2026-09-07, 19 weeks after the world this suite was written on): the SAME world age for the checks that need the
    /// phone-sized Turkey board (#456 at Level 62 there; 18 days after its epoch the v2 world's Turkey board holds 235
    /// players and a Level-62 player ranks #65). The event scenarios keep t0: their week decides the featured events.
    private let tSameAge = Date(timeIntervalSince1970: 1_790_337_600 + 19 * 604_800)

    private func world(seed: UInt64 = 1) -> SocialWorld { SocialWorld(installSeed: seed, config: tuning.social.config, names: names) }

    private func state(level: Int, country: String = "TR", seed: UInt64 = 1) -> PlayerState {
        var s = PlayerState()
        s.installSeed = seed
        s.level = level
        s.homeSeen = true
        s.social.country = country
        return s
    }

    private func inputs(_ w: SocialWorld, _ s: PlayerState, at date: Date) -> SocInputs {
        let now = EconomyClock.peekSocial(s, wall: date)
        return SocInputs(world: w, state: s, now: now, me: s.social.standing(installSeed: s.installSeed, level: s.level),
                         config: tuning.social.config, rules: rules, scale: 3, captionLevel: "Level", captionScore: "Score")
    }

    private func signature(_ c: SocListContent) -> [String] {
        c.items.map {
            switch $0 {
            case .row(let r): return "\(r.rank)|\(r.id)|\(r.name)|\(r.value)|\(r.isMe)"
            case .separator: return "---"
            }
        }
    }

    // MARK: determinism + rewind

    func testSameSeedSameTimeGivesIdenticalRows() {
        let s = state(level: 62)
        let a = inputs(world(), s, at: t0), b = inputs(world(), s, at: t0)
        XCTAssertEqual(signature(SocCompute.worldList(a)), signature(SocCompute.worldList(b)))
        XCTAssertEqual(signature(SocCompute.countryList(a)), signature(SocCompute.countryList(b)))
        let sa = SocCompute.streak(a), sb = SocCompute.streak(b)
        XCTAssertNotNil(sa)
        XCTAssertEqual(signature(sa!.list), signature(sb!.list))
    }

    func testClockSetBackNeverShowsLessProgress() {
        let w = world()
        var s = state(level: 62)
        let later = t0.addingTimeInterval(6 * 3600)
        _ = EconomyClock.social(&s, wall: later)                  // the world was shown at `later` (high-water mark)
        let atLater = SocCompute.worldList(inputs(w, s, at: later))
        let setBack = SocCompute.worldList(inputs(w, s, at: t0))  // the device clock now reads 6 h earlier
        XCTAssertEqual(signature(setBack), signature(atLater), "a clock set back freezes the world at the high-water mark")
        // and the world moves forward (monotone) over real time
        let early = SocCompute.worldList(inputs(w, state(level: 62), at: t0))
        let e1 = Dictionary(early.rows.filter { !$0.isMe }.map { ($0.id, $0.value) }, uniquingKeysWith: max)
        for r in atLater.rows where !r.isMe {
            if let v0 = e1[r.id] { XCTAssertGreaterThanOrEqual(r.value, v0, "player \(r.id) went backwards") }
        }
    }

    // MARK: list composition

    func testWorldListTop100SeparatorAndWindow() throws {
        let c = SocCompute.worldList(inputs(world(), state(level: 62), at: t0))
        let rows = c.rows
        XCTAssertGreaterThan(c.myRank, 110, "a Level-62 player is far below the World top 100")
        XCTAssertEqual(Array(rows.prefix(100)).map(\.rank), Array(1...100))
        let sep = try XCTUnwrap(c.items.firstIndex { if case .separator = $0 { return true }; return false })
        XCTAssertEqual(sep, 100)
        let window = Array(rows.dropFirst(100))
        XCTAssertEqual(window.map(\.rank), Array((c.myRank - 10)...(c.myRank + 10)))
        XCTAssertEqual(window.first(where: \.isMe)?.rank, c.myRank)
        XCTAssertEqual(rows.filter(\.isMe).count, 1)
        // levels are non-increasing down the list
        for (a, b) in zip(rows, rows.dropFirst()) where a.rank + 1 == b.rank { XCTAssertGreaterThanOrEqual(a.value, b.value) }
        XCTAssertEqual(rows.first?.badge, .rank1Badge)
        XCTAssertEqual(rows.dropFirst(3).first?.badge, nil)
    }

    func testCountryContinuousWhileRankWithin600() {
        let c = SocCompute.countryList(inputs(world(), state(level: 62, country: "TR"), at: tSameAge))
        XCTAssertGreaterThan(c.myRank, 0)
        XCTAssertLessThanOrEqual(c.myRank, 600, "Turkey #≈430 at Level 62 (phone #455, SPEC-social §14.3)")
        XCTAssertFalse(c.items.contains { if case .separator = $0 { return true }; return false })
        XCTAssertEqual(c.rows.map(\.rank), Array(1...(c.myRank + 10)))
        XCTAssertGreaterThanOrEqual(c.rows.count, 200, "the 200-row scroll acceptance runs on this list")
        XCTAssertEqual(c.rows.first(where: \.isMe)?.value, 62)
    }

    func testWeeklyGroupOfTenWithPodium() throws {
        var s = state(level: 62)
        XCTAssertTrue(Events.joinWeekly(&s, now: t0, rules: rules))
        let w = try XCTUnwrap(SocCompute.weekly(inputs(world(), s, at: t0.addingTimeInterval(3600))))
        XCTAssertEqual(w.podium.count, 3)
        XCTAssertEqual(w.podium.map(\.rank), [1, 2, 3])
        XCTAssertEqual(w.list.rows.map(\.rank), Array(4...10), "10-player group (VERIFIED meta-013..015)")
        XCTAssertEqual(w.prizes, [2000, 1000, 500])
        XCTAssertTrue((w.podium.map(\.isMe) + w.list.rows.map(\.isMe)).contains(true))
    }

    func testStreakRaceFiftyRowsWithPrizes() throws {
        var s = state(level: 62)
        _ = Events.refresh(&s, now: t0, rivals: world(), me: s.social.standing(installSeed: 1, level: 62), rules: rules, home: true)
        let st = try XCTUnwrap(SocCompute.streak(inputs(world(), s, at: t0.addingTimeInterval(1800))))
        XCTAssertEqual(st.list.rows.count, 50, "50 rows (VERIFIED meta-045..052)")
        XCTAssertEqual(st.list.rows.map(\.rank), Array(1...50))
        XCTAssertEqual(st.list.rows.prefix(10).map(\.prize), [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100])
        XCTAssertTrue(st.list.rows.dropFirst(10).allSatisfy { $0.prize == 0 })
        XCTAssertEqual(st.list.rows[0].look, .gold)
        XCTAssertEqual(st.list.rows[1].look, .silver)
        XCTAssertEqual(st.list.rows[2].look, .bronze)
        XCTAssertEqual(st.list.rows.filter(\.isMe).count, 1)
    }

    // MARK: the CA list

    func testListRecyclesPinsAndPublishesUnderBudget() throws {
        let c = SocCompute.countryList(inputs(world(), state(level: 62), at: t0))
        let list = SocListView(spec: .init(kind: .country, geo: .leaderboard, firstTop: 17.2, bottomPad: 90, pinTop: 10.4,
                                           pinBottom: 569, opensAtMe: true, jump: .top), scale: 3)
        list.frame = CGRect(x: 0, y: 0, width: 393, height: 581.7)
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
        window.addSubview(list)
        window.isHidden = false
        list.apply(c)
        list.layoutIfNeeded()
        func rowViews() -> Int { list.scroll.subviews.first?.subviews.filter { !$0.isHidden }.count ?? 0 }
        XCTAssertLessThanOrEqual(rowViews(), 12, "only about a screenful of row views")
        XCTAssertGreaterThan(list.scroll.contentOffset.y, 1000, "Country opens centred on the player's row (#\(c.myRank))")
        // scroll to the top: the player's row pins at the bottom edge
        list.scroll.contentOffset = .zero
        list.layoutIfNeeded()
        XCTAssertLessThanOrEqual(rowViews(), 12)
        let pinned = try XCTUnwrap(list.subviews.first { ($0.accessibilityIdentifier ?? "") == "leaderboard.me.pinned" })
        XCTAssertFalse(pinned.isHidden)
        XCTAssertEqual(pinned.frame.minY - 1.9 + 66.4, 569, accuracy: 0.5, "the pinned face ends at the viewport bottom (VERIFIED meta-027)")
        // a new snapshot on the main thread: layer writes only
        var worst = 0.0
        for _ in 0..<20 {
            let t = CACurrentMediaTime()
            list.apply(c)
            list.layoutIfNeeded()
            worst = max(worst, (CACurrentMediaTime() - t) * 1000)
        }
        XCTAssertLessThan(worst, 8, "publishing \(c.items.count) rows costs \(worst) ms on the main thread (simulator)")
    }

    /// FIX-V2 F-04: the page's own event refresh lands a few frames after the first snapshot and can move the player several
    /// rows; while the list is still opening it follows the player (V2: the Streak Race page opened with the player pinned
    /// at the top as #31 over rows 42-45), and a snapshot that does not move the player leaves the viewport alone.
    func testAnOpeningListFollowsThePlayersRow() throws {
        let c = SocCompute.countryList(inputs(world(), state(level: 62), at: t0))
        let list = SocListView(spec: .init(kind: .country, geo: .leaderboard, firstTop: 17.2, bottomPad: 90, pinTop: 10.4,
                                           pinBottom: 569, opensAtMe: true, jump: .top), scale: 3)
        list.frame = CGRect(x: 0, y: 0, width: 393, height: 581.7)
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
        window.addSubview(list)
        window.isHidden = false
        list.pageOpened()
        list.apply(c)
        list.layoutIfNeeded()
        let m0 = try XCTUnwrap(c.meIndex)
        XCTAssertGreaterThan(m0, 10)
        func meOnScreen() -> Bool {
            let pinned = list.subviews.first { ($0.accessibilityIdentifier ?? "") == "leaderboard.me.pinned" }
            let row = (list.accessibilityElements ?? []).compactMap { $0 as? UIView }
                .first { $0.accessibilityIdentifier == "leaderboard.me" && $0 !== pinned && !$0.isHidden }
            guard let row else { return false }
            let r = row.convert(row.bounds, to: list)
            return r.minY >= 0 && r.maxY <= list.bounds.height && (pinned?.isHidden ?? true)
        }
        XCTAssertTrue(meOnScreen(), "opens on the player's row")
        // the refresh: the same rows, the player 8 places higher
        var items = c.items
        let me = items.remove(at: m0)
        items.insert(me, at: m0 - 8)
        let moved = SocListContent(kind: c.kind, items: items, myRank: c.myRank - 8, total: c.total, computedAt: c.computedAt)
        list.apply(moved)
        list.layoutIfNeeded()
        XCTAssertTrue(meOnScreen(), "a refresh that lands while the page opens re-centres on the player")
        let y = list.scroll.contentOffset.y
        list.apply(moved)
        list.layoutIfNeeded()
        XCTAssertEqual(list.scroll.contentOffset.y, y, accuracy: 0.01, "a snapshot that leaves the player where they are moves nothing")
    }

    func testShapingIsThreadSafeAndFits() {
        let long = "Serenityinator_16"
        let st = SocRowStyles.name(.world)
        let group = DispatchGroup()
        var results = [CGFloat](repeating: 0, count: 64)
        let lock = NSLock()
        for i in 0..<64 {
            group.enter()
            DispatchQueue.global().async {
                let s = SocType.shape(i % 2 == 0 ? long : "player_\(i)abcdef", st)
                lock.lock(); results[i] = s.advance; lock.unlock()
                group.leave()
            }
        }
        XCTAssertEqual(group.wait(timeout: .now() + 10), .success)
        XCTAssertTrue(results.allSatisfy { $0 > 0 && $0 <= 180.5 }, "every name fits the 180 pt box (shrink 0.7, then …)")
        let n = SocType.number(1_048_397, SocRowStyles.value)
        XCTAssertLessThanOrEqual(n.advance, 52.5, "7-digit numbers shrink into the value box (\"14669\" ≈ 18 pt on meta-018)")
    }

    func testRowArtExistsForEveryAvatarAndLook() {
        for i in 0...8 {
            XCTAssertNotNil(SocArt.avatarTile(i, me: false, size: CGSize(width: 53, height: 53.4), scale: 3), "avatar \(i)")
            XCTAssertNotNil(ArtStore.image(Avatars.art(i)), "the portrait \(Avatars.art(i).rawValue) ships")
        }
        for l in SocRowLook.allCases { XCTAssertNotNil(SocArt.rowFace(l, size: CGSize(width: 378, height: 64.4), scale: 3)) }
        // A4 ART-INTEG (R8 EVENT-ART, owner items 14 + 15): the same 18 rasters under their D1 ids (podium, Hot Streak header,
        // Rocket Rally backdrop + rockets, Cloud Hop backdrop / pad / island, Treasure Climb header) — each must still ship
        for a in [UIArt.rank1Badge, .rank2Badge, .rank3Badge, .rewardCoinBowl, .socialScoreChip, .leaderboardPodium, .eventStreakRaceHeader,
                  .eventRocketRaceBackdrop, .eventRocketRaceRacerMine, .eventRocketRaceRacerOther, .rank1Wings, .eventSkyJumpBackdrop, .eventSkyJumpPad, .eventSkyJumpPlatform,
                  .eventClawChallengeHeader, .iconInfo, .iconPointerDown, .iconPointer] {
            XCTAssertNotNil(ArtStore.image(a), "\(a.rawValue) ships")
        }
    }

    // MARK: scenarios drive the real state machines

    func testRocketScenarioLanes() throws {
        let w = world()
        let s0 = state(level: 62)
        let s = try XCTUnwrap(SocScenario.build("rocketMid", from: s0, wall: t0, world: w, rules: rules))
        let run = try XCTUnwrap(s.events.rocket.active)
        XCTAssertEqual(run.progress, 1)
        let snap = try XCTUnwrap(SocCompute.rocket(inputs(w, s, at: t0), memo: nil).0)
        XCTAssertEqual(snap.lanes.count, 5)
        XCTAssertTrue(snap.lanes[0].isMe, "lane 1 = the player (SPEC-ui §2.17.3)")
        XCTAssertEqual(snap.lanes[0].progress, 1)
        XCTAssertEqual(Set(snap.lanes.map(\.rank)), Set(1...5))
        XCTAssertEqual(snap.goal, 5)
    }

    func testSkyScenarioCurve() throws {
        let w = world()
        let s = try XCTUnwrap(SocScenario.build("skyStep2", from: state(level: 45), wall: t0, world: w, rules: rules))
        let snap = try XCTUnwrap(SocCompute.sky(inputs(w, s, at: t0), memo: nil).0)
        XCTAssertEqual(snap.progress, 2)
        XCTAssertEqual(snap.goal, 5)
        XCTAssertEqual(snap.alive.first, 100)
        XCTAssertLessThan(snap.playersLeft, 100)
        XCTAssertTrue(zip(snap.alive, snap.alive.dropFirst()).allSatisfy { $0 >= $1 }, "players only drop")
        XCTAssertEqual(snap.share, 5000 / max(1, snap.winners))
    }

    // MARK: Profile stats (SOC2's settle step feeds S3's Profile tiles)

    func testEndedWeekSettlesIntoTheProfileStats() throws {
        let w = world()
        var s = state(level: 62)
        let weekly = try XCTUnwrap(ProfileStat.all.first { $0.id == "weekly" })
        XCTAssertEqual(weekly.value(s), 0)
        // this week (it ends Mon 28 Sep 07:00 UTC): joined at t0, then a run of wins far beyond any group rival's pace
        XCTAssertTrue(Events.joinWeekly(&s, now: t0, rules: rules))
        for i in 0..<300 {
            let win = WinContext(levels: [s.level], tag: .normal, firstTry: true, now: t0.addingTimeInterval(Double(i) * 120))
            _ = Events.onWin(&s, win, rivals: w, rules: rules)
            s.level += 1
        }
        XCTAssertEqual(s.events.weekly.score, 300)
        // next Monday: the calendar roll leaves the week waiting for its rank; SOC2's settle asks the world, C3 pays
        let later = t0.addingTimeInterval(3 * 86_400)
        _ = Events.refresh(&s, now: later, rivals: w, me: s.social.standing(installSeed: s.installSeed, level: s.level), rules: rules)
        XCTAssertEqual(Events.weeksToSettle(s).count, 1)
        SocialFlows.settleWeeks(&s, world: w, rules: rules, fallback: "US")
        XCTAssertTrue(Events.weeksToSettle(s).isEmpty)
        XCTAssertEqual(weekly.value(s), 1, "rank 1 = one Weekly Contest Win on the Profile")
        let prize = try XCTUnwrap(s.events.claims.first { $0.kind == .weeklyPrize })
        XCTAssertEqual(prize.value, 1)
        XCTAssertEqual(prize.grant, .coins(rules.events.weekly.prizes[0]))
    }

    // MARK: honesty (SPEC.md §5.24)

    func testNoCopySaysSimulatedOrOnline() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        let folder = root.appendingPathComponent("App/Shell/Social")
        let files = try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil).filter { $0.pathExtension == "swift" }
        XCTAssertFalse(files.isEmpty)
        let banned = ["simulat", "simüle", "online", "bot "]
        for f in files {
            let text = try String(contentsOf: f, encoding: .utf8)
            // only string literals are user-facing
            for line in text.split(separator: "\n") where !line.trimmingCharacters(in: .whitespaces).hasPrefix("//") {
                for lit in line.split(separator: "\"").enumerated().filter({ $0.offset % 2 == 1 }).map(\.element) {
                    for b in banned { XCTAssertFalse(lit.lowercased().contains(b), "\(f.lastPathComponent): \"\(lit)\"") }
                }
            }
        }
        let tsv = try String(contentsOf: root.appendingPathComponent("App/Resources/Strings/requests/social.tsv"), encoding: .utf8)
        for line in tsv.split(separator: "\n") where !line.hasPrefix("#") {
            let cols = line.split(separator: "\t", omittingEmptySubsequences: false)
            for c in cols.prefix(2) { for b in banned { XCTAssertFalse(c.lowercased().contains(b), "social.tsv: \(line)") } }
        }
    }

    // MARK: FIX-2 lane B (R8-o3, F-17): the Up & Away chests and the Cloud Hop header, measured

    /// R8-o3 (v582: the chests sit at x ≈ 130-200, left of the balloon's column): no ledge's chest is ever under the balloon,
    /// at every count from the ground to the last platform (B1/A4's box at page x 206-284 overlapped platform 1's chest at
    /// counts 0-3).
    /// FIX-2 B review (L26): the Weekly tutorial's lock is a hit map, not gesture state — `TutorialTouchSwallow`'s view claims
    /// EVERY point of the screen outside the trophy tab's hole (UIKit then delivers the whole touch sequence to it, and it
    /// drops it) and NO point inside it (the tab under it takes the touch), at 1 pt steps; it carries no gesture recognizer
    /// (nothing a SwiftUI body rebuild could reset between touch-down and touch-up), and a new hole moves the map. Controls:
    /// an empty hole claims every point, a full-screen hole none. (The UI stress test did NOT reproduce the pre-L26 1-in-8
    /// leak — 0 of 12 runs, 540 distinct gestures, build/p/FIX2/B-R/neg — so this map is the falsifiable part of the proof.)
    func testTheWeeklyTutorialSwallowClaimsEveryPointOutsideTheTab() {
        let hole = CGRect(x: 279.2, y: 772.3, width: 93.7, height: 80.4)
        let v = TutorialTouchSwallow.SwallowView(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
        v.hole = hole
        func claimed(_ v: TutorialTouchSwallow.SwallowView) -> (outside: Int, inside: Int, total: Int, nonHole: Int) {
            var outside = 0, inside = 0, total = 0, nonHole = 0
            for y in stride(from: 0.5, to: 852, by: 1.0) {
                for x in stride(from: 0.5, to: 393, by: 1.0) {
                    let p = CGPoint(x: x, y: y)
                    total += 1
                    let hit = v.hitTest(p, with: nil)
                    if v.hole.contains(p) { if hit != nil { inside += 1 } } else { nonHole += 1; if hit === v { outside += 1 } }
                }
            }
            return (outside, inside, total, nonHole)
        }
        let r = claimed(v)
        XCTAssertEqual(r.inside, 0, "no point of the trophy tab's hole is claimed")
        XCTAssertEqual(r.outside, r.nonHole, "every point outside the hole is claimed")
        XCTAssertEqual(r.total - r.nonHole, 94 * 80, "the hole is the tab's 94 x 80 pt")
        XCTAssertNil(v.hitTest(CGPoint(x: -1, y: 400), with: nil), "nothing outside the screen")
        XCTAssertTrue(v.gestureRecognizers?.isEmpty ?? true, "no gesture recognizer: no state a body rebuild can reset")
        v.hole = .zero
        XCTAssertEqual(claimed(v).outside, r.total, "control: an empty hole claims every point")
        v.hole = v.bounds.insetBy(dx: -1, dy: -1)
        XCTAssertEqual(claimed(v).outside, 0, "control: a full-screen hole claims none")
        XCTAssertTrue(claimed(v).inside == 0)
    }

    func testBalloonChestNeverUnderTheBalloon() {
        let platforms = rules.events.balloonRise.platforms.map(\.at)
        XCTAssertGreaterThanOrEqual(platforms.count, 3)
        let geo = BalloonTrackGeometry(platforms: platforms)
        var overlaps: [String] = []
        for c in 0...(platforms.last ?? 0) {
            let hero = BalloonLayout.heroFrame(geo, count: Double(c))
            for i in platforms.indices where BalloonLayout.chestFrame(geo, i).intersects(hero) {
                overlaps.append("count \(c): chest \(i + 1) \(BalloonLayout.chestFrame(geo, i)) under \(hero)")
            }
        }
        XCTAssertEqual(overlaps, [])
        let chest = BalloonLayout.chestFrame(geo, 0)
        XCTAssertEqual(chest.minX, 130, accuracy: 1, "v582's chest band starts at x ≈ 130")
        XCTAssertLessThanOrEqual(chest.maxX, 210, "and ends left of the balloon's frame")
        // the chest stays on its ledge art (240 pt wide from x 60) and clear of the "Step N" board (local y 112-140)
        XCTAssertTrue(CGRect(origin: BalloonLayout.ledgeOrigin(geo, 0), size: BalloonLayout.ledgeSize).contains(chest))
        XCTAssertLessThan(BalloonLayout.chestBox.maxY, 112)
        // negative control: B1's old box (local x 146) WAS under the balloon at count 0
        let old = CGRect(x: 146, y: 22, width: 78, height: 70).offsetBy(dx: 60, dy: geo.y(platform: 0) - 94)
        XCTAssertTrue(old.intersects(BalloonLayout.heroFrame(geo, count: 0)))
    }

    /// F-17: the Cloud Hop header plate is inset like the phone's (080: x 13.0 → 380.0 on the 1178 px shot), not full width.
    func testCloudHopHeaderPlateIsInsetLikeThePhone() {
        let r = SocSkyMap.headerPlate
        XCTAssertEqual(r.minX, 13.0, accuracy: 1)
        XCTAssertEqual(r.maxX, 380.0, accuracy: 1)
        XCTAssertEqual(r.minY, 103.4, accuracy: 0.01, "the band's height and place are unchanged")
        XCTAssertEqual(r.height, 103.4, accuracy: 0.01)
    }

    /// B3-o3 guard: "You are sharing the reward with %lld other winners!" has no plural variants (13 languages; pl / sk / sl use
    /// a number-last label form). It is correct only while a Sky Jump attempt always has ≥ 3 winners (others ≥ 2): the shipped
    /// curve draws 5-10 / 12-18 / 5-9 winners per stage. Over 1,000 attempts per stage the winners stay in the spec's band and
    /// never below 3 — if the curve ever allows 1-2 winners, this fails and the string needs its plural variants first.
    func testSkyJumpAlwaysHasSeveralOtherWinners() throws {
        let spec = SocialSkySpec.shipped
        let drops = try XCTUnwrap(spec.drops)
        XCTAssertTrue(drops.allSatisfy { $0.wlo >= 3 }, "the spec's winner floors: \(drops.map(\.wlo))")
        var lowest = Int.max
        for stage in 1...spec.levels.count {
            let band = drops[stage - 1]
            for attempt in 0..<1000 {
                let j = SocialSkyJump(installSeed: 0x5EED_0000 &+ UInt64(attempt) &* 7919, attemptId: attempt, stage: stage, spec: spec)
                let winners = try XCTUnwrap(j.alive.last)
                XCTAssertTrue((band.wlo...band.whi).contains(winners), "stage \(stage) attempt \(attempt): \(winners) winners")
                lowest = min(lowest, winners)
            }
        }
        XCTAssertGreaterThanOrEqual(lowest - 1, 2, "others = winners - 1 stays plural in every language")
    }
}
