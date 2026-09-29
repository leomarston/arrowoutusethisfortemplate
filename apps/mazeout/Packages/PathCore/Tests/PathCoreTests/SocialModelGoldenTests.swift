import XCTest
@testable import PathCore

// SOC1 (§12.2 acceptance: "bit-exact agreement with the Python reference on the whole fixture set: … leaderboard pages at
// >= 20 times across 3 years, race fields, Sky Jump fields"). Tests/Fixtures/soc_<model>_{world,events}.json are written
// by Tests/tools/soc_fixtures.py from the UNMODIFIED reference with SOC1's parameter sets (Tests/tools/soc_model.py):
// `reference` = the prototype, `v552` = the SHIPPED world calibrated to the owner's phone (SOC1c: drawn nicknames, Sky Jump
// stage 3 = 10 levels). Both must match bit for bit.

final class SocialModelGoldenTests: XCTestCase {
    typealias F = SocFix

    func testReferenceWorldBoards() throws { try boards("reference") }
    func testV552WorldBoards() throws { try boards("v552") }
    func testReferencePlayersCohortsLocal() throws { try players("reference") }
    func testV552PlayersCohortsLocal() throws { try players("v552") }
    func testReferenceEvents() throws { try events("reference") }
    func testV552Events() throws { try events("v552") }
    // PUBLISH B2: the shipped v2 world (socialsim/v2.py; soc_fixtures.py run unmodified on it by
    // design/social/tools/v2/fixtures_v2.py, board times moved +19 weeks = the same world ages)
    func testV2WorldBoards() throws { try boards("v2") }
    func testV2PlayersCohortsLocal() throws { try players("v2") }
    func testV2Events() throws { try events("v2") }

    // ------------------------------------------------------------ boards at 24 times, 2026-04 … 2029-09

    func boards(_ model: String) throws {
        let fx = try F.ownFixture("soc_\(model)_world.json")
        XCTAssertEqual(F.str(fx["model"]), model)
        let W = F.world(model)
        let boards = F.arr(fx["boards"])
        XCTAssertEqual(boards.count, 24)
        let tEnd = Double(F.i(F.obj(boards.last)["t"]))
        W.extend(to: tEnd + 2 * 86_400)
        let pEnd = SocialHash.floorDiv(Int(tEnd + 2 * 86_400) - W.epoch, SocialCalendar.week)
        XCTAssertEqual(W.cohorts.filter { $0.p <= pEnd }.count, F.i(fx["cohortCount"]))
        for e in boards {
            let b = F.obj(e)
            let t = Double(F.i(b["t"]))
            XCTAssertEqual(W.joined(t), F.i(b["joined"]), "joined \(t)")
            XCTAssertEqual(W.gidLimit(t), F.i(b["gidLimit"]))
            let top = W.top(t, 25)
            XCTAssertEqual(top.map(\.gid), F.arr(b["top"]).map { F.i(F.arr($0)[0]) }, "top gids \(t)")
            XCTAssertEqual(top.map(\.P.bitPattern), F.arr(b["top"]).map { F.d(F.arr($0)[1]).bitPattern }, "top P \(t)")
            checkRows(W, top.prefix(10).map { ($0.c, $0.j) }, F.arr(b["topRows"]), t, "topRows \(t)")
            for (k, v) in F.obj(b["rank"]) { XCTAssertEqual(W.rankOfLevel(Int(k)!, t), F.i(v), "rank L\(k) \(t)") }
            for (iso, cv) in F.obj(b["country"]) {
                let c = F.obj(cv)
                XCTAssertEqual(W.joined(t, iso: iso), F.i(c["joined"]), "\(iso) joined \(t)")
                for (k, v) in F.obj(c["rank"]) { XCTAssertEqual(W.rankOfLevel(Int(k)!, t, iso: iso), F.i(v), "\(iso) L\(k) \(t)") }
                SocTally.add(4)
            }
            for (key, iso) in [("nb62", nil), ("nbTR62", "TR")] as [(String, String?)] {
                let nb = F.obj(b[key])
                let n = iso == nil ? 5 : 6
                let (ab, be) = W.neighbours(62, t, above: n, below: n, iso: iso)
                XCTAssertEqual(ab.map(\.gid), F.arr(nb["above"]).map { F.i(F.arr($0)[0]) }, "\(key) above \(t)")
                XCTAssertEqual(be.map(\.gid), F.arr(nb["below"]).map { F.i(F.arr($0)[0]) }, "\(key) below \(t)")
                XCTAssertEqual(ab.map(\.P.bitPattern), F.arr(nb["above"]).map { F.d(F.arr($0)[1]).bitPattern })
                XCTAssertEqual(be.map(\.P.bitPattern), F.arr(nb["below"]).map { F.d(F.arr($0)[1]).bitPattern })
                if let rows = nb["rows"] { checkRows(W, (ab + be).map { ($0.c, $0.j) }, F.arr(rows), t, "\(key) rows \(t)") }
                SocTally.add(4 * n)
            }
            let topTR = W.top(t, 12, iso: "TR")
            checkRows(W, topTR.map { ($0.c, $0.j) }, F.arr(b["topTR"]), t, "topTR \(t)")
            SocTally.add(2 + 50 + 4)
        }
    }

    /// Rows [gid, name, style, avatar, level].
    func checkRows(_ W: SocialPopulation, _ refs: [(SocialCohort, Int)], _ want: [Any], _ t: Double, _ what: String) {
        XCTAssertEqual(refs.count, want.count, what)
        for (r, w) in zip(refs, want) {
            let v = F.arr(w)
            let (nm, st) = W.name(r.0, r.1)
            XCTAssertEqual(W.gid(r.0, r.1), F.i(v[0]), what)
            XCTAssertEqual(nm, F.str(v[1]), what)
            XCTAssertEqual(st, F.str(v[2]), what)
            XCTAssertEqual(W.avatar(r.0, r.1, style: st), F.i(v[3]), what)
            XCTAssertEqual(W.level(r.0, r.1, t), F.i(v[4]), what)
            SocTally.add(5)
        }
    }

    // ------------------------------------------------------------ 1,500 players, cohort samples, the LOCAL partition

    func players(_ model: String) throws {
        let fx = try F.ownFixture("soc_\(model)_world.json")
        let W = F.world(model)
        let boards = F.arr(fx["boards"])
        W.extend(to: Double(F.i(F.obj(boards.last)["t"])) + 2 * 86_400)
        let cs = W.cohorts
        let ps = F.arr(fx["players"])
        XCTAssertEqual(ps.count, 1500)
        var bad = 0
        for e in ps {
            let v = F.arr(e)
            guard F.i(v[0]) < cs.count, F.i(v[1]) < cs[F.i(v[0])].n else { bad += 1; continue }   // a different world
            let c = cs[F.i(v[0])], j = F.i(v[1]), t = Double(F.i(v[7]))
            let (nm, st) = W.name(c, j)
            let ok = W.gid(c, j) == F.i(v[2]) && nm == F.str(v[3]) && st == F.str(v[4]) && W.avatar(c, j, style: st) == F.i(v[5])
                && W.level(c, j, t) == F.i(v[6]) && F.same(W.progress(c, j, t), F.dOpt(v[8]))
            if !ok { bad += 1; if bad < 5 { XCTFail("player \(v) got \(nm) \(st) L\(W.level(c, j, t))") } }
            SocTally.add(7)
        }
        XCTAssertEqual(bad, 0, "player mismatches")
        let cws = F.arr(fx["cohorts"])
        XCTAssertGreaterThan(cws.count, 100)
        for e in cws {
            let v = F.arr(e)
            guard F.i(v[0]) < cs.count else { XCTFail("cohort \(F.i(v[0])) missing"); continue }
            let c = cs[F.i(v[0])]
            XCTAssertEqual([c.ck, c.p, c.b, c.a, c.day, c.n, c.gid0], (1...7).map { F.i(v[$0]) }, "cohort \(c.idx)")
            XCTAssertEqual([c.iso, c.culture], [F.str(v[8]), F.str(v[10])])       // v2 block cohorts: none (null)
            XCTAssertEqual(c.off, F.i(v[9]))
            XCTAssertTrue(F.same(c.v, F.d(v[11])) && F.same(c.pace, F.d(v[12])) && F.same(c.T, F.d(v[13]))
                          && F.same(c.Tl, F.d(v[14])) && F.same(c.join0, F.d(v[15])) && F.same(c.R, F.dOpt(v[16])), "cohort \(c.idx)")
            let styles = F.arr(v[17]).map { F.arr($0) }
            XCTAssertEqual(styles.map { [F.i($0[1]), F.i($0[2]), F.i($0[3])] },
                           zip(W.styleCum(c), W.styleBase(c)).map { [$0.0.lo, $0.0.hi, $0.1] })
            SocTally.add(16 + styles.count * 3)
        }
        // the LOCAL partition (a home country missing from the table: Iceland)
        let lo = F.obj(fx["local"])
        let tL = Double(F.i(lo["t"]))
        let WL = SocialPopulation(model: F.model(model),
                                  local: SocialLocalPartition(iso: "IS", offsetMinutes: 0, culture: "nordic"), names: F.bank(model))
        WL.extend(to: tL)
        XCTAssertEqual(WL.cohorts.count, F.i(lo["cohortCount"]))
        let lcs = WL.cohorts.filter { $0.local && $0.n > 0 }
        let rows = F.arr(lo["rows"])
        XCTAssertEqual(rows.count, 12)
        for (c, e) in zip(lcs, rows) {
            let v = F.arr(e)
            XCTAssertEqual([c.idx, c.gid0, c.n], [F.i(v[0]), F.i(v[1]), F.i(v[2])])
            let k = min(3, c.n)
            XCTAssertEqual((0..<k).map { WL.name(c, $0).name }, (0..<k).map { F.str(v[3 + $0])! }, "local names \(c.idx)")
            XCTAssertEqual(WL.level(c, c.n - 1, tL), F.i(v[3 + k]))
            SocTally.add(4 + k)
        }
        XCTAssertEqual(WL.rankOfLevel(62, tL, iso: "IS"), F.i(lo["rankIS62"]))
        XCTAssertEqual(WL.joined(tL, iso: "IS"), F.i(lo["joinedIS"]))
        let tis = WL.top(tL, 10, iso: "IS")
        XCTAssertEqual(tis.map(\.gid), F.arr(lo["topIS"]).map { F.i(F.arr($0)[0]) })
        XCTAssertEqual(tis.map(\.P.bitPattern), F.arr(lo["topIS"]).map { F.d(F.arr($0)[1]).bitPattern })
        SocTally.add(22)
        // the model's nickname decoding (styles × cultures × slots; the shipped 'leet' style and variants included)
        let wm = F.model(model)
        let bank = F.bank(model)
        let ws = F.arr(fx["customWeights"]).map { F.arr($0) }
        XCTAssertEqual(wm.nameStyle.weights.map(\.style), ws.map { F.str($0[0])! })
        XCTAssertEqual(wm.nameStyle.weights.map(\.weight), ws.map { F.d($0[1]) })
        XCTAssertEqual(wm.nameStyle.variants == nil, fx["variants"] is NSNull)
        let names = F.arr(fx["names"])
        XCTAssertGreaterThan(names.count, 300)
        var badNames = 0
        for e in names {
            let v = F.arr(e)
            let cu = F.str(v[1])! == "*" ? "en" : F.str(v[1])!
            let got = SocialNames.decode(F.str(v[0])!, F.i(v[2]), cu, bank: bank, variants: wm.nameStyle.variants,
                                         nativeT: wm.nameStyle.nativeT, kanaP: wm.nameStyle.kanaP)
            if got != F.str(v[3]) { badNames += 1; if badNames < 6 { XCTFail("decode \(v) got \(got ?? "nil")") } }
            SocTally.add(1)
        }
        XCTAssertEqual(badNames, 0, "decode mismatches")
        // SOC1c: the shipped world DRAWS custom nicknames with replacement (names.DRAW / drawn): every style × culture ×
        // 24 player keys pin the head / popularity / uniform picks, the number rounds and the per-player case variants
        if model != "reference" {
            let draw = try XCTUnwrap(wm.nameStyle.draw)
            let dw = F.obj(fx["draw"])
            XCTAssertEqual([draw.twoDigitP, draw.headP, draw.headN], [F.i(dw["twoDigitP"]), F.i(dw["headP"]), F.i(dw["headN"])])
            // v2 (M7): the scaled head and the uniform tail (absent from the calibrated fixture = off)
            XCTAssertEqual(draw.headScaled, (dw["headScaled"] as? NSNumber)?.boolValue ?? false)
            XCTAssertEqual(draw.tailUniformP, dw["tailUniformP"].map { F.i($0) } ?? 0)
            XCTAssertEqual(draw.numberP, F.obj(dw["numberP"]).mapValues { F.i($0) })
            XCTAssertEqual(F.arr(fx["skyLevels"]).map { F.i($0) }, SocialConfig.default.sky.levels)
            // SOC1c: per-cohort style counts by systematic apportionment (population.py STYLE_SYSTEMATIC); the world
            // boards and the 1,500 spread players above pin the counts themselves
            XCTAssertEqual(wm.nameStyle.systematic, (fx["styleSystematic"] as? NSNumber)?.boolValue, "style apportionment")
            XCTAssertTrue(wm.nameStyle.systematic)
            let drawn = F.arr(fx["drawn"])
            XCTAssertGreaterThan(drawn.count, 1000)
            var badDrawn = 0
            for e in drawn {
                let v = F.arr(e)
                let cu = F.str(v[1])! == "*" ? "en" : F.str(v[1])!
                let key = F.u64(v[3])
                XCTAssertEqual(key, SocialHash.h64(SocialWorldModel.worldSeed, SocialLabels.nick, F.i(v[2])), "nick key \(v)")
                let got = SocialNames.drawn(F.str(v[0])!, cu, key: key, bank: bank, variants: wm.nameStyle.variants, draw: draw,
                                            nativeT: wm.nameStyle.nativeT, kanaP: wm.nameStyle.kanaP)
                if got != F.str(v[4]) { badDrawn += 1; if badDrawn < 6 { XCTFail("drawn \(v) got \(got ?? "nil")") } }
                SocTally.add(2)
            }
            XCTAssertEqual(badDrawn, 0, "drawn mismatches")
        } else {
            XCTAssertNil(wm.nameStyle.draw, "the reference keeps its unique first-come slots")
            XCTAssertNil(fx["drawn"])
            XCTAssertFalse(wm.nameStyle.systematic, "the reference keeps its last-style-takes-the-remainder counts")
            XCTAssertNil(fx["styleSystematic"])
        }
    }

    // ------------------------------------------------------------ Weekly / Streak groups, Rocket races, Sky Jump, pace

    func events(_ model: String) throws {
        let ev = try F.ownFixture("soc_\(model)_events.json")
        let W = F.world(model)
        let cfg = model == "reference" ? SocialConfig.reference : SocialConfig.default
        W.extend(to: Double(1_883_000_000))
        for (kind, spec) in [("weekly", cfg.weekly), ("streak", cfg.streak)] {
            let groups = F.arr(ev[kind])
            XCTAssertEqual(groups.count, 4)
            for e in groups {
                let o = F.obj(e)
                let t0 = Double(F.i(o["t0"]))
                let windows = F.arr(o["windows"]).map { F.arr($0).map { Double(F.i($0)) } }
                let g = SocialGroupContest(W: W, installSeed: UInt64(F.i(o["seed"])), spec: spec,
                                           key: SocialGroupKey(instance: F.i(o[kind == "weekly" ? "week" : "day"]), t0: t0,
                                                               ref: F.d(o["ref"]), windows: windows))
                XCTAssertEqual(g.members.map { W.gid($0.0, $0.1) }, F.arr(o["members"]).map { F.i($0) }, "\(kind) members \(t0)")
                XCTAssertEqual(g.arrive.map(\.bitPattern), F.arr(o["arrive"]).map { F.d($0).bitPattern }, "\(kind) arrive \(t0)")
                XCTAssertEqual(g.base, F.arr(o["base"]).map { F.i($0) }, "\(kind) base \(t0)")
                if kind == "streak" {
                    XCTAssertEqual(g.s0, F.arr(o["s0"]).map { F.i($0) })
                    XCTAssertEqual(g.q.map(\.bitPattern), F.arr(o["q"]).map { F.d($0).bitPattern })
                }
                XCTAssertEqual(g.members.count, spec.groupSize - 1)
                for ce in F.arr(o["checks"]) {
                    let c = F.obj(ce)
                    let t = t0 + Double(F.i(c["dt"]))
                    // the fixture passes the user's name 'Hsheh' to the Streak Race (it orders equal scores when tieByName)
                    let st = g.standings(t, userScore: F.i(c["userScore"]), userReached: F.d(c["userReached"]),
                                         userName: kind == "streak" ? "Hsheh" : nil)
                    let want = F.arr(c["rows"]).map { F.arr($0) }
                    XCTAssertEqual(st.map { [$0.member ?? -1, $0.score] }, want.map { [F.i($0[0]), F.i($0[1])] }, "\(kind) \(t0)+\(F.i(c["dt"]))")
                    XCTAssertEqual(st.map(\.reached.bitPattern), want.map { F.d($0[2]).bitPattern }, "\(kind) reached")
                    if let sc = c["scores"] {
                        XCTAssertEqual(g.members.indices.map { g.memberScore($0, t) ?? -1 }, F.arr(sc).map { ($0 is NSNull) ? -1 : F.i($0) })
                    }
                    SocTally.add(want.count * 3)
                }
                SocTally.add(g.members.count * 3)
            }
        }
        let races = F.arr(ev["rocket"])
        XCTAssertEqual(races.count, 24)
        for e in races {
            let o = F.obj(e)
            let t0 = Double(F.i(o["t0"]))
            let rr = SocialRocketRace(W: W, installSeed: UInt64(F.i(o["seed"])), raceId: F.i(o["raceId"]), stage: F.i(o["stage"]),
                                      t0: t0, secondsPerWin: F.d(o["spw"]), spec: cfg.rocket)
            XCTAssertEqual(rr.N, F.i(o["N"]))
            XCTAssertEqual(rr.end, Double(F.i(o["end"])))
            XCTAssertEqual(rr.rivals.map { W.gid($0.0, $0.1) }, F.arr(o["rivals"]).map { F.i($0) }, "rocket \(t0)")
            XCTAssertEqual(rr.base, F.arr(o["base"]).map { F.i($0) })
            XCTAssertEqual(rr.hold.map(\.bitPattern), F.arr(o["hold"]).map { F.d($0).bitPattern })
            XCTAssertEqual(rr.delta.map(\.bitPattern), F.arr(o["delta"]).map { F.d($0).bitPattern })
            XCTAssertEqual(rr.natural.map { $0?.bitPattern }, F.arr(o["natural"]).map { F.dOpt($0)?.bitPattern })
            let user = F.arr(o["userTimes"]).map { Double(F.i($0)) }
            let nm1 = user[rr.N - 2]
            XCTAssertEqual((0..<4).map { rr.finishTime($0, userNminus1: nil)?.bitPattern }, F.arr(o["finish"]).map { F.dOpt($0)?.bitPattern })
            XCTAssertEqual((0..<4).map { rr.finishTime($0, userNminus1: nm1)?.bitPattern }, F.arr(o["finishUser"]).map { F.dOpt($0)?.bitPattern })
            for pe in F.arr(o["progress"]) {
                let v = F.arr(pe)
                let t = t0 + Double(F.i(v[0])) * 60
                XCTAssertEqual((0..<4).map { rr.rivalProgress($0, t, userNminus1: nil) }, F.arr(v[1]).map { F.i($0) })
                XCTAssertEqual((0..<4).map { rr.rivalProgress($0, t, userNminus1: nm1) }, F.arr(v[2]).map { F.i($0) })
                SocTally.add(8)
            }
            let out = rr.outcome(userTimes: user)
            XCTAssertEqual(out.result.rawValue, F.str(F.arr(o["outcome"])[0]))
            XCTAssertTrue(F.same(out.at, F.d(F.arr(o["outcome"])[1])))
            let slow = rr.outcome(userTimes: (1...rr.N).map { t0 + 1800 * Double($0) })
            XCTAssertEqual(slow.result.rawValue, F.str(F.arr(o["outcomeSlow"])[0]))
            XCTAssertTrue(F.same(slow.at, F.d(F.arr(o["outcomeSlow"])[1])))
            SocTally.add(30)
        }
        let sky = F.arr(ev["sky"])
        XCTAssertEqual(sky.count, 40)
        for e in sky {
            let o = F.obj(e)
            let sj = SocialSkyJump(installSeed: UInt64(F.i(o["seed"])), attemptId: F.i(o["attempt"]), stage: F.i(o["stage"]),
                                   spec: cfg.sky)
            XCTAssertEqual(sj.alive, F.arr(o["alive"]).map { F.i($0) })
            XCTAssertEqual(sj.share, F.i(o["share"]))
            SocTally.add(sj.alive.count + 1)
        }
        let pace = F.arr(ev["pace"])
        XCTAssertEqual(pace.count, 6)
        for e in pace {
            let o = F.obj(e)
            let wins = F.arr(o["wins"]).map { (t: Double(F.i($0)), level: 1, firstTry: true) }
            let p = SocialPace.of(wins: wins, at: Double(F.i(o["t"])))
            XCTAssertTrue(F.same(p.daily, F.d(o["daily"])) && F.same(p.secondsPerWin, F.d(o["spw"])) && F.same(p.weekly, F.d(o["weekly"])),
                          "pace \(o["t"]!): \(p)")
            SocTally.add(3)
        }
    }

    /// Runs last (alphabetically): prints how many values agreed bit for bit in this process.
    func testZZTally() {
        print("[SOC1] golden values compared bit for bit in this run: \(SocTally.values)")
    }
}
