import XCTest
@testable import GameCore
@testable import ArrowEscape

// SOC1: the ◆ SocialWorld surface as SOC2 / GAME / C3 will call it (SPEC-architecture §4.10-§4.11; SPEC-social §3).

final class SocialWorldAPITests: XCTestCase {
    typealias F = SocFix
    /// 2026-09-25 01:31 UTC (the phone's moment) + 19 weeks (PUBLISH B2: the shipped v2 world starts 2026-09-07, 19 weeks
    /// after the calibrated world these tests were written on, so this is the SAME world age; a Friday 01:31 UTC again).
    static let t = SocialTime(seconds: 1_790_299_860 + 19 * 604_800)

    func me(_ level: Int, country: String = "TR", ledger: [LedgerEntry] = []) -> PlayerStanding {
        PlayerStanding(name: "Hsheh", avatar: 3, country: country, level: level, ledger: ledger)
    }

    func assertBoardShape(_ p: LeaderboardPage, from a: Int, me: PlayerStanding, _ what: String) {
        XCTAssertEqual(p.rows.map(\.rank), Array(a..<(a + p.rows.count)), "\(what): contiguous ranks")
        let v = p.rows.map(\.value)
        XCTAssertFalse(zip(v, v.dropFirst()).contains { $0 < $1 }, "\(what): levels never rise going down")
        XCTAssertEqual(Set(p.rows.map(\.player.id)).count, p.rows.count, "\(what): no duplicate player")
        for r in p.rows where r.isMe { XCTAssertEqual(r.rank, p.myRank); XCTAssertEqual(r.value, me.level) }
        for r in p.rows where !r.isMe {
            if r.rank < p.myRank { XCTAssertGreaterThan(r.value, me.level, "\(what): above the player = a higher level") }
            if p.myRank > 0 && r.rank > p.myRank { XCTAssertLessThanOrEqual(r.value, me.level, "\(what): the player leads its level") }
        }
    }

    func testWorldAndCountryPages() {
        let w = SocialWorld(installSeed: 1, config: .default, names: F.bankV2)
        let m = me(62)
        let top = w.page(.world, me: m, at: Self.t, ranks: 1...50)
        XCTAssertEqual(top.rows.count, 50)
        assertBoardShape(top, from: 1, me: m, "world top")
        XCTAssertEqual(top.total, w.population(country: nil, me: m, at: Self.t) + 1)
        XCTAssertFalse(top.rows.contains { $0.isMe })
        let tr = w.page(.country("TR"), me: m, at: Self.t, around: 0, radius: 0)       // just the rank
        let around = w.page(.country("TR"), me: m, at: Self.t, around: tr.myRank, radius: 10)
        XCTAssertEqual(around.rows.count, 21)
        XCTAssertEqual(around.rows.filter(\.isMe).count, 1)
        assertBoardShape(around, from: tr.myRank - 10, me: m, "TR around")
        // Country is continuous from rank 1 to the player (the phone opens it scrolled to the player)
        let full = w.page(.country("TR"), me: m, at: Self.t, ranks: 1...(tr.myRank + 10))
        assertBoardShape(full, from: 1, me: m, "TR continuous")
        XCTAssertEqual(Array(full.rows.suffix(21)), around.rows)
        // a deep World page far from the player (ranks past the top-k merge): level bisection + neighbours
        let deep = w.page(.world, me: m, at: Self.t, ranks: 20_000...20_020)
        XCTAssertEqual(deep.rows.count, 21)
        assertBoardShape(deep, from: 20_000, me: m, "deep world")
        let aboveDeep = w.page(.world, me: m, at: Self.t, ranks: 19_990...20_000)
        XCTAssertEqual(aboveDeep.rows.last, deep.rows.first, "pages join up")
        // the player's own row and the rows around it
        let wr = w.rank(level: 62, country: nil, me: m, at: Self.t)
        let mine = w.page(.world, me: m, at: Self.t, around: wr, radius: 3)
        assertBoardShape(mine, from: wr - 3, me: m, "world around me")
        XCTAssertEqual(mine.rows[3].isMe, true)
    }

    /// One shared world: two installs see the same World and Country boards (only their own rows differ).
    func testSharedWorldAcrossInstalls() {
        let a = SocialWorld(installSeed: 11, config: .default, names: F.bankV2)
        let b = SocialWorld(installSeed: 99_999, config: .default, names: F.bankV2)
        let m = me(62)
        XCTAssertEqual(a.page(.world, me: m, at: Self.t, ranks: 1...30).rows, b.page(.world, me: m, at: Self.t, ranks: 1...30).rows)
        let r = a.page(.country("TR"), me: m, at: Self.t, ranks: 1...1).myRank
        XCTAssertEqual(a.page(.country("TR"), me: m, at: Self.t, around: r, radius: 8).rows,
                       b.page(.country("TR"), me: m, at: Self.t, around: r, radius: 8).rows)
        // and a row's identity is the same through player(id)
        for row in a.page(.world, me: m, at: Self.t, ranks: 1...10).rows {
            XCTAssertEqual(a.player(row.player.id), row.player)
        }
    }

    func testWeeklyPageAndPodium() {
        let w = SocialWorld(installSeed: 20_260_925, config: .default, names: F.bankV2)
        var st = SocialState()
        st.setHomeIfNeeded(region: "TR", offsetMinutes: 180)
        let week = SocialCalendar.eventWeek(Int(Self.t.seconds))
        XCTAssertEqual(w.page(.weekly(week: week), me: st.standing(installSeed: 1, level: 62), at: Self.t, ranks: 1...10).rows.count, 0,
                       "no group before the join")
        let join = SocialTime(seconds: Self.t.seconds - 5000)
        st.joinWeekly(week: week, level: 55, at: join)
        for k in 0..<4 { st.recordWin(level: 55 + k, firstTry: true, points: 25, at: SocialTime(seconds: join.seconds + 600 + Int64(k) * 300)) }
        let m = st.standing(installSeed: 1, level: 59)
        let p = w.page(.weekly(week: week), me: m, at: Self.t, ranks: 1...10)
        XCTAssertEqual(p.total, 10)
        XCTAssertEqual(p.rows.map(\.rank), Array(1...10))
        XCTAssertEqual(p.rows.first { $0.isMe }?.value, 4, "the player's score = wins since the join")
        let v = p.rows.map(\.value)
        XCTAssertFalse(zip(v, v.dropFirst()).contains { $0 < $1 })
        XCTAssertEqual(w.weeklyPodium(week: week, at: Self.t), Array(p.rows.prefix(3)))
        let board = w.weeklyBoard(week: week, me: m, at: Self.t)
        XCTAssertEqual(board?.rows, p.rows)
        XCTAssertEqual(board?.endsAt.seconds, Int64(SocialCalendar.eventWeekStart(week + 1)))
        // marker-less: the group forms at the week's first counted win (C3's auto-join) and is stable
        var st2 = SocialState()
        st2.recordWin(level: 51, firstTry: true, points: 5, at: SocialTime(seconds: Self.t.seconds - 3000))
        let m2 = st2.standing(installSeed: 1, level: 52)
        let p2 = w.page(.weekly(week: week), me: m2, at: Self.t, ranks: 1...10)
        XCTAssertEqual(p2.total, 10)
        XCTAssertEqual(w.page(.weekly(week: week), me: m2, at: Self.t, ranks: 1...10).rows, p2.rows)
    }

    func testRaceConventions() {
        let w = SocialWorld(installSeed: 4242, config: .default, names: F.bankV2)
        let day = SocialCalendar.eventDay(Int(Self.t.seconds))
        let inst = EventInstance(event: .streakRace, index: day, start: SocialTime(seconds: Int64(SocialCalendar.eventDayStart(day))),
                                 end: SocialTime(seconds: Int64(SocialCalendar.eventDayStart(day + 1))))
        var st = SocialState()
        for k in 0..<8 { st.recordWin(level: 40 + k, firstTry: true, points: [1, 5, 10, 25, 100, 100, 100, 100][k],
                                      at: SocialTime(seconds: inst.start.seconds + 3600 + Int64(k) * 400)) }
        let rows = w.streakRace(inst, player: st.standing(installSeed: 1, level: 48), at: Self.t)
        XCTAssertEqual(rows.count, 50, "phone v552: 50 rows")
        XCTAssertEqual(rows.filter(\.isMe).first?.score, 441)
        XCTAssertEqual(rows.map(\.rank), Array(1...50))
        XCTAssertFalse(zip(rows, rows.dropFirst()).contains { $0.score < $1.score })
        // Rocket Race: the ◆ call returns the 4 rivals; "rocketRace.2" is stage 2 (7 levels)
        let rk = EventInstance(event: .rocketRace, index: 3, start: Self.t, end: SocialTime(seconds: Int64(SocialCalendar.eventDayStart(day + 1))))
        let lanes = w.rocketRace(rk, joinedAt: Self.t, at: SocialTime(seconds: Self.t.seconds + 3600))
        XCTAssertEqual(lanes.count, 4)
        XCTAssertTrue(lanes.allSatisfy { !$0.isMe && (0...5).contains($0.score) })
        let rk2 = EventInstance(event: EventID("rocketRace.2"), index: 3, start: Self.t, end: rk.end)
        XCTAssertTrue(w.rocketRace(rk2, joinedAt: Self.t, at: SocialTime(seconds: Self.t.seconds + 7200)).allSatisfy { (0...7).contains($0.score) })
        let board = w.rocketBoard(raceId: 3, stage: 1, joinedAt: Self.t, secondsPerWin: 100,
                                  userWins: (1...5).map { SocialTime(seconds: Self.t.seconds + Int64($0) * 60) },
                                  me: me(56), at: SocialTime(seconds: Self.t.seconds + 600))
        XCTAssertEqual(board.lanes.count, 5)
        XCTAssertEqual(board.levels, 5)
        XCTAssertEqual(board.result, "win", "5 wins in 5 minutes beat any rival (5 levels take a player >= 7.7 min)")
        // Sky Jump: 100 players, fewer after each first-try win, winners only at the end (C3's 1-based stage)
        let run0 = SkyJumpRun(instance: EventInstance(event: .skyJump, index: 7, start: Self.t, end: Self.t), joinedAt: Self.t, stage: 1)
        let f0 = w.skyJump(run0, at: Self.t)
        XCTAssertEqual([f0.total, f0.left, f0.winners], [100, 100, 0])
        XCTAssertLessThanOrEqual(f0.shown.count, 14)
        XCTAssertTrue(f0.shown.allSatisfy { $0.avatar != 0 })
        var prev = 100
        for k in 1...5 {
            var r = run0; r.progress = k
            let f = w.skyJump(r, at: Self.t)
            XCTAssertLessThanOrEqual(f.left, prev); prev = f.left
            XCTAssertEqual(f.winners, k == 5 ? f.left : 0)
        }
        XCTAssertEqual(w.skyJumpCurve(attemptId: 7, stage: 1).alive.last, prev)
    }

    /// A home region code no table knows gets its device-only LOCAL partition: its board has players and the shared World
    /// is unchanged for everyone else. PUBLISH B2 (requirement change, social-intl P0-2 / M4): in the shipped v2 world every
    /// Locale.Region code resolves to a board (Iceland is a table row now), so the LOCAL partition exists only for an
    /// unknown 2-letter code ("ZZ"), keyed by its ISO, at offset 0 — the same assertions on that code, plus Iceland's board
    /// is the shared world's.
    func testLocalCountry() {
        var cfg = SocialConfig.default
        cfg.homeCountry = "ZZ"
        let w = SocialWorld(installSeed: 5, config: cfg, names: F.bankV2)
        let m = me(62, country: "ZZ")
        let p = w.page(.country("ZZ"), me: m, at: Self.t, ranks: 1...20)
        XCTAssertEqual(p.rows.count, 20)
        XCTAssertTrue(p.rows.filter { !$0.isMe }.allSatisfy { $0.player.country == "ZZ" && $0.player.id >= 1 << 40 })
        assertBoardShape(p, from: 1, me: m, "an unknown region")
        let other = SocialWorld(installSeed: 5, config: .default, names: F.bankV2)
        let tr = me(62)
        XCTAssertEqual(w.page(.country("TR"), me: tr, at: Self.t, ranks: 1...15).rows, other.page(.country("TR"), me: tr, at: Self.t, ranks: 1...15).rows)
        let iceland = me(62, country: "IS")
        let isPage = w.page(.country("IS"), me: iceland, at: Self.t, ranks: 1...20)
        XCTAssertEqual(isPage.rows.count, 20)
        XCTAssertTrue(isPage.rows.filter { !$0.isMe }.allSatisfy { $0.player.country == "IS" && $0.player.id < 1 << 40 },
                      "Iceland plays on the shared world")
        XCTAssertEqual(isPage.rows, other.page(.country("IS"), me: iceland, at: Self.t, ranks: 1...20).rows)
    }

    /// PUBLISH B2 (M3): a territory plays on its parent's board (IC -> ES), a numeric region on its representative's; the
    /// player's row sits on that board and the Country tab names that country (SocialWorld.boardCountry).
    func testTerritoriesAndNumericRegionsPlayOnTheirBoard() throws {
        let w = SocialWorld(installSeed: 5, config: .default, names: F.bankV2)
        let intl = try XCTUnwrap(SocialWorldModel.shipped.intl)
        let alias = "IC"                                              // the Canary Islands
        XCTAssertEqual(intl.regions[alias]?.kind, .alias)
        let board = try XCTUnwrap(intl.regions[alias]?.board)
        XCTAssertEqual(board, "ES")
        XCTAssertEqual(w.boardCountry(alias), board)
        let canary = me(62, country: alias), parent = me(62, country: board)
        let a = w.page(.country(alias), me: canary, at: Self.t, ranks: 1...25)
        let b = w.page(.country(board), me: parent, at: Self.t, ranks: 1...25)
        XCTAssertEqual(a.myRank, b.myRank)
        XCTAssertEqual(a.rows.filter { !$0.isMe }, b.rows.filter { !$0.isMe })
        XCTAssertTrue(a.rows.contains { $0.isMe } == b.rows.contains { $0.isMe })
        let numeric = try XCTUnwrap(intl.regions.first { $0.value.kind == .numeric })
        XCTAssertEqual(w.boardCountry(numeric.key), numeric.value.board)
        XCTAssertEqual(w.rank(level: 62, country: numeric.key, me: me(62, country: numeric.key), at: Self.t),
                       w.rank(level: 62, country: numeric.value.board, me: me(62, country: numeric.value.board), at: Self.t))
    }

    /// An empty NameBank (APISurfaceTests builds the world with `NameBank()`) degrades to `player_` names, never crashes.
    func testEmptyNameBankDegrades() {
        let w = SocialWorld(installSeed: 1, config: SocialConfig(), names: NameBank())
        let p = w.page(.world, me: me(32), at: SocialTime(seconds: 1_790_000_000), ranks: 1...20)
        XCTAssertEqual(p.rows.count, 20)
        XCTAssertTrue(p.rows.allSatisfy { $0.player.name.hasPrefix("player_") })
        XCTAssertEqual(Set(p.rows.map(\.player.name)).count, 20)
    }
}
