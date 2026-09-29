import XCTest
import SwiftUI
import PathCore
@testable import ArrowOut

/// FIX-2 lane A (perf / feel): the memos and bounded caches that take repeated main-thread work out of view bodies.
///  - B1b-r0: `Tokens.text` / `color` / `colors` resolve each (file, id, default) once and return exactly the uncached read;
///  - V3-10: the GameText raster cache is a BYTE-bounded LRU (it was cleared whole past 400 entries), the layout cache a
///    count-bounded LRU; `BoundedCache` evicts least-recently-used first and never a pinned key;
///  - the social config is decoded once per tuning file (a Leaderboard tab body decoded social.json per evaluation);
///  - the next level's home tag is read off the main thread at the level cut (the arrival frame read the file).
@MainActor final class FixTwoATests: XCTestCase {

    // MARK: B1b-r0 — Tokens memo

    /// Every text style id in ui.json (a node under `text` that carries a style key).
    private func textIDs(_ file: TuningFile) -> [String] {
        var out: [String] = []
        func walk(_ node: Any?, _ path: [String]) {
            guard let d = node as? [String: Any] else { return }
            if !path.isEmpty, ["size", "fill", "outline", "tracking", "drop", "band"].contains(where: { d[$0] != nil }) {
                out.append(path.joined(separator: "."))
            }
            for (k, v) in d where v is [String: Any] { walk(v, path + [k]) }
        }
        walk(file.json["text"], [])
        return out.sorted()
    }

    func testTextStyleIsMemoizedAndEqualToTheUncachedRead() {
        let ui = Tuning.load(bundle: .main).ui
        let t = ui.tokens
        let ids = textIDs(ui.file)
        XCTAssertGreaterThan(ids.count, 30, "ui.json's text styles: \(ids.count)")
        let d = GameTextStyle(size: 17, tracking: -0.3, fill: [Color(hex: 0x123456)], outline: Color(hex: 0x010203))
        for id in ids {
            let memo = t.text(id, d)
            XCTAssertEqual(memo, t.textUncached(id, d), "text.\(id): the memo returns the uncached read")
            XCTAssertEqual(t.text(id, d), memo, "text.\(id): stable")
        }
        let before = Tokens.memoCount
        for id in ids { _ = t.text(id, d) }
        XCTAssertEqual(Tokens.memoCount, before, "a second pass adds no entry: every read hit the memo")
        // a different compiled default is its own entry (a missing key returns ITS default)
        let d2 = GameTextStyle(size: 9)
        XCTAssertEqual(t.text("no.such.style", d2), d2)
        XCTAssertEqual(t.text("no.such.style", d), d)
        // colours: equal to the uncached read, for every colour id in ui.json
        for (k, v) in (ui.file.json["colors"] as? [String: Any]) ?? [:] {
            if v is String { XCTAssertEqual(t.color(k, 0x000000), t.colorUncached(k, 0x000000), "colors.\(k)") }
            if v is [Any] { XCTAssertEqual(t.colors(k, [0]), t.colorsUncached(k, [0]), "colors.\(k)") }
        }
        // an override (`-pc.tune`) loads a NEW file: the memo never serves the bundled value for it
        let tuned = Tuning.load(bundle: .main, tune: ["ui.text.home.level.size": "99"]).ui.tokens
        if ids.contains("home.level") {
            XCTAssertEqual(tuned.text("home.level", d).size, 99)
            XCTAssertNotEqual(t.text("home.level", d).size, 99)
        }
    }

    func testTextStyleMemoIsMuchCheaperThanTheUncachedRead() {
        let t = Tuning.load(bundle: .main).ui.tokens
        let ids = textIDs(t.file)
        let d = GameTextStyle(size: 17)
        for id in ids { _ = t.text(id, d) }                       // memoised
        let n = 10_000
        var t0 = CACurrentMediaTime()
        for i in 0..<n { _ = t.text(ids[i % ids.count], d) }
        let memo = CACurrentMediaTime() - t0
        t0 = CACurrentMediaTime()
        for i in 0..<n { _ = t.textUncached(ids[i % ids.count], d) }
        let raw = CACurrentMediaTime() - t0
        print(String(format: "[FIX2] 10,000 text lookups: memo %.2f ms, uncached %.2f ms", memo * 1000, raw * 1000))
        XCTAssertLessThan(memo * 3, raw, "the memo is at least 3× cheaper than walking the JSON (Debug build)")
    }

    // MARK: V3-10 — bounded caches

    func testBoundedCacheEvictsLeastRecentlyUsedAndKeepsPinned() {
        let c = BoundedCache<Int, String>(limit: 100, trimTo: 0.5)
        for i in 0..<10 { c.set(i, "v\(i)", cost: 10) }             // 100: at the limit
        XCTAssertEqual(c.totalCost, 100)
        XCTAssertEqual(c.count, 10)
        _ = c.get(0)                                                 // 0 is now the most recent
        c.pin(1)                                                     // 1 is pinned
        c.set(10, "v10", cost: 10)                                   // 110 > 100 → trim to 50
        XCTAssertLessThanOrEqual(c.totalCost, 50)
        XCTAssertTrue(c.contains(0), "recently read: kept")
        XCTAssertTrue(c.contains(1), "pinned: never evicted")
        XCTAssertTrue(c.contains(10), "just inserted: kept")
        XCTAssertFalse(c.contains(2), "least recently used: evicted first")
        c.unpin(1)
        c.removeAll { $0 >= 10 }
        XCTAssertFalse(c.contains(10))
        XCTAssertEqual(c.totalCost, c.count * 10)
        // replacing a key replaces its cost
        c.set(0, "w", cost: 30)
        XCTAssertEqual(c.get(0), "w")
        XCTAssertEqual(c.totalCost, (c.count - 1) * 10 + 30)
    }

    func testGameTextRasterCacheIsByteBoundedAndKeepsTheRecentOnes() throws {
        let style = GameTextStyle(size: 22, fill: [Color(hex: 0xFFFFFF)], outline: Color(hex: 0x223344), outlineWidth: 2)
        var recent: [(GameTextLayout, CGSize, CGPoint)] = []
        let n = 2_000
        for i in 0..<n {
            let l = GameTextLayout.make("FIX2 \(i) raster", postScriptName: GameText.blackPostScript, size: style.size,
                                        tracking: 0)
            let size = CGSize(width: l.advance + 8, height: 40), origin = CGPoint(x: 4, y: 30)
            XCTAssertNotNil(GameTextRaster.image(l, style: style, size: size, origin: origin, scale: 3))
            if i >= n - 50 { recent.append((l, size, origin)) }
            XCTAssertLessThanOrEqual(GameTextRaster.bytes, GameTextRaster.byteLimit, "bytes stay under the cap (insert \(i))")
        }
        XCTAssertGreaterThan(GameTextRaster.cache.evictions, 0, "2,000 labels do not fit in the byte cap: the LRU evicted")
        XCTAssertGreaterThan(GameTextRaster.count, 50, "an LRU trims, it never empties the cache")
        let misses0 = GameTextRaster.cache.evictions
        for (l, size, origin) in recent {
            let key = GameTextRaster.Key(text: l.text, font: style.postScriptName, size: l.fontSize, tracking: l.tracking,
                                         style: style, w: size.width, h: size.height, ox: origin.x, oy: origin.y, scale: 3)
            XCTAssertTrue(GameTextRaster.cache.contains(key), "one of the 50 most recent labels is still cached")
        }
        XCTAssertEqual(GameTextRaster.cache.evictions, misses0)
        // the layout cache is a count LRU of 800 (was cleared whole past 800)
        XCTAssertLessThanOrEqual(GameTextLayout.cache.count, 800)
        XCTAssertGreaterThan(GameTextLayout.cache.count, 400, "trimmed to 3/4, not emptied")
    }

    // MARK: decoded once / read off the main thread

    func testSocialConfigIsDecodedOncePerFile() {
        let social = Tuning.load(bundle: .main).social
        XCTAssertEqual(social.config, social.file.decode(SocialConfig.self), "the stored config is the file's decode")
        let t0 = CACurrentMediaTime()
        for _ in 0..<1_000 { _ = social.config.model }
        XCTAssertLessThan(CACurrentMediaTime() - t0, 0.05, "1,000 reads cost no decode")
    }

    func testNextLevelTagIsPrefetchedOffTheMainThread() {
        let args = LaunchArgs(pairs: [:])
        let level = 137                                            // a bundled level no other test reads
        XCTAssertFalse(HomeLevelInfo.isCached(level))
        HomeLevelInfo.prefetch(level, args: args)
        let end = Date().addingTimeInterval(3)
        while !HomeLevelInfo.isCached(level) && Date() < end { RunLoop.main.run(until: Date().addingTimeInterval(0.01)) }
        XCTAssertTrue(HomeLevelInfo.isCached(level), "read on a background queue")
        XCTAssertEqual(HomeLevelInfo.tag(for: level, args: args), HomeLevelInfo.tag(for: level, args: args))
    }

    // MARK: L27 — the confetti burst matches v552's coverage

    /// The y of a layer's "fall" position track at `t` s after its begin (linear between keys; the app interpolates cubically).
    private func y(_ layer: CALayer, at t: Double) -> CGFloat? {
        guard let g = layer.animation(forKey: "fall") as? CAAnimationGroup,
              let pos = g.animations?.first(where: { ($0 as? CAKeyframeAnimation)?.keyPath == "position" }) as? CAKeyframeAnimation,
              let vals = pos.values as? [NSValue], let keys = pos.keyTimes?.map(\.doubleValue) else { return nil }
        let u = (t - g.beginTime) / g.duration
        guard u >= 0, u <= 1 else { return nil }
        for i in 1..<keys.count where u <= keys[i] {
            let f = (u - keys[i - 1]) / max(1e-9, keys[i] - keys[i - 1])
            return vals[i - 1].cgPointValue.y + CGFloat(f) * (vals[i].cgPointValue.y - vals[i - 1].cgPointValue.y)
        }
        return vals.last?.cgPointValue.y
    }

    /// FIX-2 A-R: the confetti as Core Animation DRAWS it at `t` (host time; the burst begins at its `begin`): every piece's
    /// rounded quad at its keyframed position, with its size, colour, the flip's scale-y and the spin at that moment (a piece
    /// not yet launched is invisible: model opacity 0), filled into a 393 × 852 1x bitmap on black, then measured exactly like
    /// build/p/FIX2/A/confetti/conf_measure.py measures the simulator captures and v552's frames: saturated bright pixels
    /// (saturation > 0.45, max > 0.35 — the cream pieces drop out, as on the real screen), outside the HUD (y < 115) and the
    /// logo box (y 280-540); `n` pixels, the share above y 426 and the 10th-percentile y.
    private func renderedCoverage(_ layers: [CALayer], at t: Double) -> (n: Int, above: Double, top10: Double) {
        let w = 393, h = 852
        var px = [UInt8](repeating: 0, count: w * h * 4)
        px.withUnsafeMutableBytes { buf in
            guard let ctx = CGContext(data: buf.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                                      space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
            else { return }
            ctx.setFillColor(UIColor.black.cgColor)
            ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
            ctx.translateBy(x: 0, y: CGFloat(h))              // UIKit's top-left origin: memory row y = screen y
            ctx.scaleBy(x: 1, y: -1)
            for l in layers {
                guard let g = l.animation(forKey: "fall") as? CAAnimationGroup, let anims = g.animations,
                      let pos = anims.first(where: { ($0 as? CAKeyframeAnimation)?.keyPath == "position" }) as? CAKeyframeAnimation,
                      let vals = pos.values as? [NSValue], let keys = pos.keyTimes?.map(\.doubleValue), let color = l.backgroundColor
                else { continue }
                let local = t - g.beginTime
                guard local >= 0 else { continue }
                let lt = min(local, g.duration)                // fillMode forwards: the last frame is held
                let u = lt / g.duration
                var p = vals.last?.cgPointValue ?? .zero
                for i in 1..<keys.count where u <= keys[i] {
                    let f = CGFloat((u - keys[i - 1]) / max(1e-9, keys[i] - keys[i - 1]))
                    let a = vals[i - 1].cgPointValue, b = vals[i].cgPointValue
                    p = CGPoint(x: a.x + f * (b.x - a.x), y: a.y + f * (b.y - a.y))
                    break
                }
                var sy: CGFloat = .nan
                if let flip = anims.first(where: { ($0 as? CAKeyframeAnimation)?.keyPath == "transform.scale.y" }) as? CAKeyframeAnimation,
                   // the values literal mixes Int and Double ([1, 0.15, -1, …]): read each as an NSNumber (`as? [Double]` fails)
                   let fv = flip.values?.compactMap({ ($0 as? NSNumber)?.doubleValue }), fv.count == flip.values?.count,
                   let fk = flip.keyTimes?.map(\.doubleValue), flip.duration > 0 {
                    let ph = (lt + flip.timeOffset).truncatingRemainder(dividingBy: flip.duration) / flip.duration
                    for i in 1..<fk.count where ph <= fk[i] {
                        sy = CGFloat(fv[i - 1] + (ph - fk[i - 1]) / max(1e-9, fk[i] - fk[i - 1]) * (fv[i] - fv[i - 1]))
                        break
                    }
                }
                XCTAssertFalse(sy.isNaN, "every piece carries its flip (scale-y) track")
                if sy.isNaN { sy = 1 }
                var rot: CGFloat = 0
                if let spin = anims.first(where: { ($0 as? CABasicAnimation)?.keyPath == "transform.rotation.z" }) as? CABasicAnimation,
                   let from = (spin.fromValue as? NSNumber)?.doubleValue, let to = (spin.toValue as? NSNumber)?.doubleValue {
                    rot = CGFloat(from + (to - from) * min(1, lt / max(1e-9, spin.duration)))
                }
                ctx.saveGState()
                ctx.translateBy(x: p.x, y: p.y)
                ctx.rotate(by: rot)
                ctx.scaleBy(x: 1, y: sy)
                let r = CGRect(x: -l.bounds.width / 2, y: -l.bounds.height / 2, width: l.bounds.width, height: l.bounds.height)
                ctx.addPath(CGPath(roundedRect: r, cornerWidth: l.cornerRadius, cornerHeight: l.cornerRadius, transform: nil))
                ctx.setFillColor(color)
                ctx.fillPath()
                ctx.restoreGState()
            }
        }
        var ys: [Int] = []
        for yy in 115..<h where !(yy >= 280 && yy < 540) {
            for xx in 0..<w {
                let i = (yy * w + xx) * 4
                let r = Double(px[i]) / 255, g = Double(px[i + 1]) / 255, b = Double(px[i + 2]) / 255
                let mx = max(r, g, b), mn = min(r, g, b)
                if mx > 0.35 && (mx - mn) / max(mx, 1e-3) > 0.45 { ys.append(yy) }
            }
        }
        guard ys.count >= 50 else { return (ys.count, 0, 0) }
        ys.sort()
        return (ys.count, Double(ys.filter { $0 < 426 }.count) / Double(ys.count), Double(ys[ys.count / 10]))
    }

    /// v552, measured on S1-L50 and S3-L089 (build/p/FIX2/A/confetti/v552-coverage.json, both clips averaged, the frame nearest
    /// each time): at W+t, the confetti PIXELS outside the HUD (above y 115) and the logo box (280-540) — how many, the share
    /// above y 426, and the y above which the top 10 % sit. The old ballistic burst (900-1500 pt/s, g 900) had NO piece above
    /// the logo before W+2.1.
    /// FIX-2 A-R (review-A): this was measured on the pieces' modelled POSITIONS, which the real screen did not follow (the
    /// simulator at W+1.90: share 0.326 vs v552's 0.20 — every piece rose at least 200 pt, so the bottom 150 pt that is v552's
    /// densest part stayed empty, 5069 px vs ≈ 8100). Now on the drawn pixels (`renderedCoverage`), the count included; the
    /// same metric on the simulator's frozen frames is in build/p/FIX2/A-R/conf.
    func testConfettiBurstCoversTheScreenLikeV552() {
        let spec = ConfettiSpec(Tuning.load(bundle: .main).ui.tokens)
        let bounds = CGRect(x: 0, y: 0, width: 393, height: 852)
        let confettiAt = 1.655
        // one celebration = the burst + the rain; averaged over 8 celebrations (seeds), as a player sees many — one draw
        // scatters ±0.03-0.05 in the share
        var runs: [[CALayer]] = []
        for seed in 1...8 {
            var rng = PathRandom(seed: UInt64(seed))
            var layers: [CALayer] = []
            for _ in 0..<spec.burst { layers.append(Confetti.burstPiece(&rng, spec: spec, bounds: bounds, begin: confettiAt)) }
            for k in 0..<Int(3 * spec.rainPerS) {
                layers.append(Confetti.rainPiece(&rng, spec: spec, bounds: bounds, begin: confettiAt + Double(k) / spec.rainPerS))
            }
            runs.append(layers)
        }
        let v552: [(t: Double, n: Double, above: Double, top10: Double)] = [
            (1.90, 8095, 0.201, 220), (1.95, 7872, 0.286, 189), (2.00, 7640, 0.325, 158), (2.10, 7002, 0.345, 162),
            (2.20, 8357, 0.273, 182)]
        for r in v552 {
            var n = 0.0, above = 0.0, top10 = 0.0
            for layers in runs {
                let c = renderedCoverage(layers, at: r.t)
                XCTAssertGreaterThan(c.n, 1000, "W+\(r.t)")
                n += Double(c.n) / Double(runs.count)
                above += c.above / Double(runs.count)
                top10 += c.top10 / Double(runs.count)
            }
            print(String(format: "[FixTwoA] confetti W+%.2f drawn n %.0f above %.3f top10 %.0f | v552 n %.0f above %.3f top10 %.0f",
                         r.t, n, above, top10, r.n, r.above, r.top10))
            XCTAssertEqual(above, r.above, accuracy: 0.07, "W+\(r.t): share of the drawn confetti above y 426 (v552 \(r.above))")
            XCTAssertEqual(n, r.n, accuracy: r.n * 0.25, "W+\(r.t): drawn confetti pixels (v552 \(r.n))")
            XCTAssertEqual(top10, r.top10, accuracy: r.top10 * 0.18, "W+\(r.t): the top 10 % (v552 y \(r.top10))")
        }
        // the burst's cloud is low for its first frames (v552: nothing above the logo before W+1.80)
        for layers in runs {
            XCTAssertEqual(layers.compactMap { y($0, at: 1.75) }.filter { $0 > 115 && $0 < 280 }.count, 0, "no piece above the logo at W+1.75")
            XCTAssertEqual(renderedCoverage(layers, at: 1.75).above, 0, "no drawn pixel above y 426 at W+1.75")
        }
    }

    // MARK: V3-09 — decoded art released when nothing shows it

    func testArtStorePurgeByPathFreesThoseEntriesOnly() {
        let a = UIArt.loadingBackdrop.path, b = UIArt.iconCoin.path
        XCTAssertNotNil(ArtStore.image(path: a))
        XCTAssertNotNil(ArtStore.image(path: a, maxPixel: 256))
        XCTAssertNotNil(ArtStore.image(path: b))
        XCTAssertTrue(ArtStore.isCached(path: a))
        let freed = ArtStore.purge(paths: [a])
        XCTAssertGreaterThan(freed, 10_000_000, "the full-bleed backdrop (1179 × 2556 × 4) and its thumbnail")
        XCTAssertFalse(ArtStore.isCached(path: a), "every size of that path is gone")
        XCTAssertTrue(ArtStore.isCached(path: b), "other art stays")
        XCTAssertNotNil(ArtStore.image(path: a), "a later read decodes it again")
    }

    func testEventArtListsNameOnlyPageArtNeverHomeArt() {
        let home = Set(HomeView.art + ShopView.art)
        for e in EventArtPolicy.managed {
            let arts = EventArtPolicy.art(e)
            XCTAssertFalse(arts.isEmpty, "\(e)")
            XCTAssertTrue(Set(arts).isDisjoint(with: home), "\(e): never art home or the Shop tab draws")
            XCTAssertFalse(arts.contains(.treasureToken), "the payout's token is home art")
            XCTAssertFalse(arts.contains(.eventBadgeBalloon), "the home bar's badge stays")
        }
        for sc in EventScreen.allCases { XCTAssertFalse(EventArtPolicy.art(sc).isEmpty, "\(sc)") }
    }

    /// FIX-2 A-R (review-A): art another screen draws is never released — for EVERY combination of openable events, the release
    /// set holds no art of an openable event and nothing home, the Shop tab or Profile draws. It released the stage chests
    /// (listed under Rocket Rally only, drawn by Up & Away and Cloud Hop too) and Profile's Rocket Rally Wins rocket.
    func testEventArtReleaseNeverTakesArtAnOpenEventOrAnotherScreenDraws() {
        let managed = EventArtPolicy.managed
        let kept = EventArtPolicy.kept
        XCTAssertTrue(kept.isSuperset(of: ProfileView.art), "Profile's stat icons are kept")
        for mask in 0..<(1 << managed.count) {
            let open = Set(managed.enumerated().filter { mask & (1 << $0.offset) != 0 }.map(\.element))
            let rel = Set(EventArtPolicy.releasable(openable: open))
            XCTAssertTrue(rel.isDisjoint(with: kept), "\(open): never kept art")
            for e in open { XCTAssertTrue(rel.isDisjoint(with: EventArtPolicy.art(e)), "\(open): never art of \(e), which can be opened") }
            for e in managed where !open.contains(e) {
                for a in EventArtPolicy.art(e) where !kept.contains(a) && !open.contains(where: { EventArtPolicy.art($0).contains(a) }) {
                    XCTAssertTrue(rel.contains(a), "\(open): \(a) (only \(e) draws it) is released")
                }
            }
        }
        let onlyUpAway = Set(EventArtPolicy.releasable(openable: [.balloonRise]))
        for chest in [UIArt.stageChestGreen, .stageChestBlue, .stageChestPink] {
            XCTAssertFalse(onlyUpAway.contains(chest), "Up & Away's page draws \(chest)")
            XCTAssertFalse(Set(EventArtPolicy.releasable(openable: [.skyJump])).contains(chest), "Cloud Hop's page draws \(chest)")
        }
        XCTAssertTrue(onlyUpAway.contains(.rallyBackdrop), "Rocket Rally's own backdrop goes")
        XCTAssertFalse(Set(EventArtPolicy.releasable(openable: [])).contains(.rallyRocketMine), "Profile draws the rally rocket")
    }

    /// FIX-2 A-R: every place in App/ that draws a managed event's art (a `.<id>` of UIArt, or Up & Away's `UpAwayArt.<name>`),
    /// read from the sources: in an event's own view file the id is in THAT event's list (decoded before its page, kept while
    /// it can be opened); anywhere else the id is `kept`. The listing that let the chests and the rally rocket be released
    /// while drawn fails this test.
    func testEveryDrawOfManagedEventArtIsCoveredByThePolicy() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("App")
        let owners: [String: EventID] = ["RocketRaceViews.swift": .rocketRace, "SkyJumpViews.swift": .skyJump,
                                         "BalloonViews.swift": .balloonRise, "ClawScreen.swift": .clawChallenge,
                                         "StreakRaceViews.swift": .streakRace]
        // not draw sites: the generated table, the policy itself, the social bundle list, Up & Away's id table
        let skip: Set<String> = ["UIArt.swift", "RootView.swift", "SocialModel.swift", "EventRotationPolicy.swift"]
        let upAway: [String: String] = ["hero": UpAwayArt.hero, "towerTop": UpAwayArt.towerTop, "towerShaft": UpAwayArt.towerShaft,
                                        "towerFoot": UpAwayArt.towerFoot, "ledge": UpAwayArt.ledge, "badge": UpAwayArt.badge]
        let managedArt = Set(EventArtPolicy.managed.flatMap { EventArtPolicy.art($0) })
        let byName = Dictionary(uniqueKeysWithValues: managedArt.map { ($0.rawValue, $0) })
        let enumRef = try NSRegularExpression(pattern: #"\.([A-Za-z][A-Za-z0-9]*)\b"#)
        let upAwayRef = try NSRegularExpression(pattern: #"UpAwayArt\.([A-Za-z]+)\b"#)
        var sites = 0
        guard let e = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil) else { return XCTFail("no App/") }
        for case let url as URL in e where url.pathExtension == "swift" && !skip.contains(url.lastPathComponent) {
            let text = try String(contentsOf: url, encoding: .utf8)
            let code = text.split(separator: "\n", omittingEmptySubsequences: false).map { line -> Substring in
                guard let r = line.range(of: "//") else { return line }
                return line[line.startIndex..<r.lowerBound]
            }.joined(separator: "\n")
            let ns = code as NSString
            var found: Set<UIArt> = []
            for m in enumRef.matches(in: code, range: NSRange(location: 0, length: ns.length)) {
                if let a = byName[ns.substring(with: m.range(at: 1))] { found.insert(a) }
            }
            for m in upAwayRef.matches(in: code, range: NSRange(location: 0, length: ns.length)) {
                if let id = upAway[ns.substring(with: m.range(at: 1))], let a = byName[id] { found.insert(a) }
            }
            for a in found {
                sites += 1
                if let owner = owners[url.lastPathComponent] {
                    XCTAssertTrue(EventArtPolicy.art(owner).contains(a) || EventArtPolicy.kept.contains(a),
                                  "\(url.lastPathComponent) (\(owner)) draws \(a): list it under \(owner)")
                } else {
                    XCTAssertTrue(EventArtPolicy.kept.contains(a), "\(url.lastPathComponent) draws \(a) outside the event pages: it must be kept")
                }
            }
        }
        XCTAssertGreaterThan(sites, 25, "the scan found the event pages' art (\(sites) file/id pairs)")
    }
}
