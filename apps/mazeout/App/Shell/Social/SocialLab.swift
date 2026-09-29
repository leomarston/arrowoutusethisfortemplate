import SwiftUI
import UIKit
import PathCore

// SOCIAL SOC2 (SPEC-architecture §9.5 SocialLab: "the world at a chosen time: boards, races, Sky Jump fields, name samples;
// scrubbing time; writes social-snapshot.json"; §10.2 the 200-row scroll budget). A debug host (`-pc.go sociallab`), never
// reachable from the game's UI:
//   `-pc.lab overview` (default)  the boards at world time + a scrub offset (+1 h / +1 d / +1 w buttons; with `-pc.clockRate K`
//                                 the numbers move while you watch), recomputed off the main thread every second; each result
//                                 is written to Documents/social-snapshot.json (rows as rank · id · name · value), then
//                                 Documents/lab-ready.json once.
//   `-pc.lab scroll[:world|country]` the real CA list full screen, scrolled programmatically top → bottom → top twice at fling
//                                 speed while every presented frame is timed; Documents/lab-perf.json = {frames, over20,
//                                 max_ms, p95_ms, p99_ms, rows, footprint_mb, publish_ms_max, worker_ms}.
//   `-pc.lab weeks`               B1: the weekly rotation's calendar around now (C3 EventRotation.plan) with what THIS player
//                                 sees each week (segmentation, unlocks, the kill switch, the Release art gate), and each
//                                 week's `-pc.now` to relaunch in it (copied on tap). It never moves the clock itself: the
//                                 rewind-safe high-water mark would carry a jump forward into the save for good.
// Text here is debug output (`Text(verbatim:)`), not game copy.

struct SocialLab: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        let lab = app.args.raw["pc.lab"] ?? "overview"
        if lab.hasPrefix("scroll") {
            SocScrollBench(kind: lab.hasSuffix(":world") ? .world : .country)
        } else if lab == "weeks" {
            SocLabWeeks()
        } else {
            SocLabOverview()
        }
    }
}

// MARK: - the rotation's calendar (B1)

private struct SocLabWeeks: View {
    @Environment(AppModel.self) private var app

    struct Row: Identifiable {
        let id: Int
        let current: Bool
        let text: String
        let iso: String
    }

    private func rows() -> (String, [Row]) {
        let ev = ShellEconomy.rules(app).events
        let s = app.store.state
        let now = EconomyClock.peekSocial(s, wall: app.clock.wallClock())
        let w0 = EventRotation.week(now, ev)
        var head = "Rotation · " + (ev.rotation.enabled ? "ON" : "OFF (every event)") + " · week \(w0) · L\(s.level)"
        if !ev.rotation.unavailable.isEmpty { head += " · unavailable: " + ev.rotation.unavailable.sorted().joined(separator: ",") }
        var out: [Row] = []
        for w in (w0 - 4)...(w0 + 12) {
            let p = EventRotation.plan(week: w, rules: ev)
            let live = EventRotation.live(week: w, level: s.level, rules: ev)
            let iso = ISO8601DateFormatter().string(from: Date(timeIntervalSince1970: Double(p.start.seconds + 5 * 3600)))
            let race = p.race.map(\.rawValue).joined(separator: "&")
            let you = live.featured.map(\.rawValue).joined(separator: ", ")
            let mark = w == w0 ? "▶" : " "
            out.append(Row(id: w, current: w == w0, text: "\(mark) w\(w) \(iso.prefix(10))  \(p.ladder.rawValue) + \(race)  → you: \(you)", iso: iso))
        }
        return (head, out)
    }

    var body: some View {
        let (head, list) = rows()
        ScrollView {
            VStack(alignment: .leading, spacing: 4) {
                Text(verbatim: head).font(.system(size: 13, weight: .bold, design: .monospaced))
                ForEach(list) { r in
                    Button {
                        UIPasteboard.general.string = "-pc.now \(r.iso)"
                        Log.mark("social", "sociallab weeks: copied -pc.now \(r.iso) (week \(r.id))")
                    } label: {
                        Text(verbatim: r.text).font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(r.current ? Color.red : Color.primary)
                    }
                    .accessibilityIdentifier("sociallab.week.\(r.id)")
                }
            }
            .padding(12)
        }
        .background(Color.white)
        .accessibilityIdentifier("sociallab.weeks")
    }
}

// MARK: - overview

struct SocLabSummary: Sendable, Codable {
    var at: Int64
    var world: [[String]] = []
    var worldRank = 0
    var country: [[String]] = []
    var countryRank = 0
    var countryISO = ""
    var weekly: [[String]] = []
    var streak: [[String]] = []
    var rocket: [[String]] = []
    var sky: [String] = []
    var names: [String] = []
    var computeMs = 0.0
}

private struct SocLabOverview: View {
    @Environment(AppModel.self) private var app
    @State private var offset: Int64 = 0
    @State private var summary: SocLabSummary?
    @State private var wroteReady = false
    private let queue = DispatchQueue(label: "com.manycode.arrowout.sociallab", qos: .userInitiated)

    var body: some View {
        let model = SocialModel.install(app)
        TimelineView(.periodic(from: .now, by: 1)) { ctx in
            ScrollView {
                VStack(alignment: .leading, spacing: 6) {
                    Text(verbatim: "SocialLab · world t = \(summary.map { iso($0.at) } ?? "…") (offset \(offset / 3600) h)")
                        .font(.system(size: 13, weight: .bold, design: .monospaced))
                    HStack {
                        let steps: [(Int64, String)] = [(3600, "+1h"), (86_400, "+1d"), (604_800, "+1w")]
                        ForEach(0..<steps.count, id: \.self) { k in
                            Button { offset += steps[k].0 } label: { Text(verbatim: steps[k].1).padding(6).background(Color.yellow.opacity(0.4)) }
                                .accessibilityIdentifier("sociallab.plus\(steps[k].1)")
                        }
                        Button { offset = 0 } label: { Text(verbatim: "now").padding(6).background(Color.yellow.opacity(0.4)) }
                    }
                    if let s = summary {
                        block("World (you #\(s.worldRank))", s.world)
                        block("\(s.countryISO) (you #\(s.countryRank))", s.country)
                        block("Weekly group", s.weekly)
                        block("Hot Streak", s.streak)
                        block("Rocket Rally", s.rocket)
                        Text(verbatim: "Cloud Hop: " + s.sky.joined(separator: " · ")).font(.system(size: 11, design: .monospaced))
                        Text(verbatim: "names: " + s.names.joined(separator: ", ")).font(.system(size: 11, design: .monospaced))
                        Text(verbatim: String(format: "worker %.1f ms · publish p95 %.2f ms", s.computeMs,
                                              model.publishP95())).font(.system(size: 11, design: .monospaced))
                    }
                }
                .padding(.top, 60).padding(.horizontal, 12)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .onChange(of: ctx.date) { _, _ in recompute() }
        }
        .background(Color.white)
        .accessibilityIdentifier("sociallab")
        .onAppear { recompute() }
    }

    private func block(_ title: String, _ rows: [[String]]) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(verbatim: title).font(.system(size: 12, weight: .bold, design: .monospaced))
            ForEach(Array(rows.enumerated()), id: \.offset) { _, r in
                Text(verbatim: r.joined(separator: "  ")).font(.system(size: 11, design: .monospaced))
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("sociallab.\(title.split(separator: " ").first ?? "")")
    }

    private func iso(_ t: Int64) -> String {
        let f = ISO8601DateFormatter()
        return f.string(from: Date(timeIntervalSince1970: Double(t)))
    }

    private func recompute() {
        guard let base = SocialModel.shared?.captureInputs() else { return }
        let off = offset
        let i = SocInputs(world: base.world, state: base.state, now: SocialTime(seconds: base.now.seconds + off), me: base.me,
                          config: base.config, rules: base.rules, scale: base.scale, captionLevel: base.captionLevel,
                          captionScore: base.captionScore)
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        queue.async {
            let s = SocLab.summarise(i)
            if let data = try? JSONEncoder().encode(s) { try? data.write(to: docs.appendingPathComponent("social-snapshot.json"), options: .atomic) }
            DispatchQueue.main.async { MainActor.assumeIsolated {
                summary = s
                if !wroteReady {
                    wroteReady = true
                    Task { @MainActor in
                        await FrameWaiter.frames(2)
                        CaptureReady.mark(screen: "sociallab", app: app, file: "lab-ready.json")
                        Log.mark("lab", "sociallab overview done")
                    }
                }
            } }
        }
    }
}

enum SocLab {
    static func summarise(_ i: SocInputs) -> SocLabSummary {
        let t0 = CACurrentMediaTime()
        var s = SocLabSummary(at: i.now.seconds)
        func rows(_ r: [LeaderboardRow]) -> [[String]] { r.map { ["#\($0.rank)", "\($0.player.id == .max ? "YOU" : String($0.player.id))", $0.player.name, "\($0.value)"] } }
        let w = i.world.page(.world, me: i.me, at: i.now, ranks: 1...5)
        s.world = rows(w.rows); s.worldRank = w.myRank
        if w.myRank > 5 { s.world += rows(i.world.page(.world, me: i.me, at: i.now, around: w.myRank, radius: 2).rows) }
        let iso = i.me.country.uppercased()
        s.countryISO = iso
        let c = i.world.page(.country(iso), me: i.me, at: i.now, ranks: 1...3)
        s.countryRank = c.myRank
        s.country = rows(c.rows) + rows(i.world.page(.country(iso), me: i.me, at: i.now, around: max(1, c.myRank), radius: 3).rows)
        if let wk = SocCompute.weekly(i) { s.weekly = rows(wk.podium) + wk.list.rows.map { ["#\($0.rank)", "\($0.id == .max ? "YOU" : String($0.id))", $0.name, "\($0.value)"] } }
        if let st = SocCompute.streak(i) {
            let all = st.list.rows
            s.streak = all.prefix(5).map { ["#\($0.rank)", $0.name, "\($0.value)", "\($0.prize)"] }
            if let me = all.first(where: \.isMe), me.rank > 5 { s.streak.append(["#\(me.rank)", "YOU", "\(me.value)", "\(me.prize)"]) }
        }
        if let r = SocCompute.rocket(i, memo: nil).0 {
            s.rocket = r.lanes.map { ["#\($0.rank)", $0.isMe ? "YOU" : $0.player.name, "\($0.progress)/\(r.goal)"] }
        }
        if let k = SocCompute.sky(i, memo: nil).0 {
            s.sky = ["stage \(k.stage)", "\(k.progress)/\(k.goal)", "players \(k.playersLeft)/100", "winners \(k.winners)", "share \(k.share)",
                     "curve \(k.alive.map(String.init).joined(separator: ","))"]
        }
        // name samples: the World page around rank 1000, 5000, 20000 (whatever exists)
        for r in [1000, 5000, 20000] {
            let p = i.world.page(.world, me: i.me, at: i.now, ranks: r...(r + 3))
            s.names += p.rows.map(\.player.name)
        }
        s.computeMs = (CACurrentMediaTime() - t0) * 1000
        return s
    }
}

extension SocialModel {
    func publishP95() -> Double {
        let v = mainPublishMs.sorted()
        guard !v.isEmpty else { return 0 }
        return v[min(v.count - 1, Int(Double(v.count - 1) * 0.95))]
    }
}

// MARK: - the scroll bench

private struct SocScrollBench: View {
    let kind: SocListKind
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let model = SocialModel.install(app)
        let host = model.listHost(kind)
        ZStack(alignment: .topLeading) {
            Color(hex: 0x0A2176)
            SocListRepresentable(host: host, k: m.s).frame(width: m.size.width, height: m.size.height - 120).offset(y: 120)
            Text(verbatim: "SocialLab scroll \(kind.rawValue): \(SocLabState.shared.result)")
                .font(.system(size: 12, weight: .bold, design: .monospaced)).foregroundStyle(.white).padding(.top, 64).padding(.leading, 12)
                .accessibilityIdentifier("sociallab.result")
                .accessibilityValue(Text(verbatim: SocLabState.shared.result))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .onAppear {
            model.appear(kind == .world ? .world : .country)
            SocScrollDriver.shared.run(app: app, model: model, kind: kind)
        }
        .onDisappear { model.disappear(kind == .world ? .world : .country) }
    }
}

/// The bench's outcome as the UI tests read it ("running" → "done frames=… over20=… max=… rows=…").
@MainActor @Observable final class SocLabState {
    static let shared = SocLabState()
    var result = "running"
}

/// Scrolls the list programmatically (a display link moving contentOffset at a fling's speed) and times every frame.
@MainActor final class SocScrollDriver: NSObject {
    static let shared = SocScrollDriver()
    private var link: CADisplayLink?
    private var last: CFTimeInterval = 0
    private var intervals: [Double] = []
    private weak var list: SocListView?
    private var dir: CGFloat = 1
    private var legs = 0
    private var app: AppModel?
    private var model: SocialModel?
    private var kind: SocListKind = .country
    private var t0: CFTimeInterval = 0

    func run(app: AppModel, model: SocialModel, kind: SocListKind) {
        self.app = app; self.model = model; self.kind = kind
        Task { @MainActor in
            // wait for the snapshot (the world, then the rows)
            for _ in 0..<200 where (model.listVersion[kind] ?? 0) == 0 { try? await Task.sleep(nanoseconds: 50_000_000) }
            try? await Task.sleep(nanoseconds: 700_000_000)
            await FrameWaiter.frames(10)
            let l = model.listHost(kind).list
            list = l
            l.scroll.setContentOffset(.zero, animated: false)
            intervals = []; last = 0; legs = 0; dir = 1; t0 = CACurrentMediaTime()
            Log.mark("lab", "scroll \(kind.rawValue) start rows \(l.data.items.count)")
            let link = CADisplayLink(target: self, selector: #selector(tick(_:)))
            link.add(to: .main, forMode: .common)
            self.link = link
        }
    }

    @objc private func tick(_ l: CADisplayLink) {
        if last > 0 {
            let ms = (l.timestamp - last) * 1000
            intervals.append(ms)
            if ms > 20 {
                let since = CACurrentMediaTime() - (model?.lastPublishAt ?? 0)
                Log.mark("lab", String(format: "slow frame %.1f ms at %.2f s offset %.0f (last publish %.2f s ago)", ms,
                                       l.timestamp - t0, list?.scroll.contentOffset.y ?? -1, since))
            }
        }
        last = l.timestamp
        guard let list else { return }
        let maxY = max(0, list.scroll.contentSize.height - list.bounds.height)
        let speed: CGFloat = 2400 / 60                         // pt per frame (a brisk fling, ~33 rows a second)
        var y = list.scroll.contentOffset.y + dir * speed
        if y >= maxY { y = maxY; dir = -1; legs += 1 }
        if y <= 0 && dir < 0 { y = 0; dir = 1; legs += 1 }
        list.scroll.contentOffset = CGPoint(x: 0, y: y)
        if legs >= 4 { finish() }
    }

    private func finish() {
        link?.invalidate(); link = nil
        let v = intervals.sorted()
        func pct(_ p: Double) -> Double { v.isEmpty ? 0 : v[min(v.count - 1, Int(Double(v.count - 1) * p))] }
        let over = intervals.filter { $0 > 20 }.count
        let rows = list?.data.items.count ?? 0
        let publishMax: Double = model?.mainPublishMs.max() ?? 0
        let maxMs: Double = v.last ?? 0
        let payload: [String: Any] = [
            "lab": "scroll", "kind": kind.rawValue, "frames": intervals.count, "over20": over, "max_ms": maxMs,
            "p50_ms": pct(0.5), "p95_ms": pct(0.95), "p99_ms": pct(0.99), "rows": rows,
            "seconds": CACurrentMediaTime() - t0, "footprint_mb": PerfMonitor.footprintMB(),
            "publish_ms_max": publishMax,
            "worker_ms": (model?.workerMs ?? [:]).reduce(into: [String: Double]()) { $0[$1.key.rawValue] = $1.value },
        ]
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]) {
            try? data.write(to: docs.appendingPathComponent("lab-perf.json"), options: .atomic)
        }
        Log.mark("lab", "scroll done frames \(intervals.count) over20 \(over) max \(String(format: "%.1f", v.last ?? 0)) ms rows \(rows)")
        SocLabState.shared.result = "done frames=\(intervals.count) over20=\(over) max=\(String(format: "%.1f", v.last ?? 0)) "
            + "p99=\(String(format: "%.1f", pct(0.99))) rows=\(rows)"
        if let app { CaptureReady.mark(screen: "sociallab:scroll", app: app, file: "lab-ready.json") }
    }
}

/// `-pc.lab open` (with `-pc.go home`): the FIRST presentation of each social surface from a settled home, through the routes a
/// tap takes (the trophy tab on its World / Country / Weekly sub-tab, then each event page from home), unobserved (no test
/// queries). Each step runs a probe started just before the route change — like a tap handler — so the body build before
/// the page's onAppear is counted too; the pages' own open probes run as well. Lines → Documents/lab-open.json, then
/// lab-ready.json. The evidence for "no first-presentation stall" (SPEC-architecture §10.2, the owner's feel requirement).
@MainActor enum SocOpenBench {
    static func run(_ app: AppModel) {
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 4_000_000_000)        // Loading gone, the launch warm-ups done, home idle
            let shell = LeaderboardShellState.shared
            shell.tab = .world
            await step("leaderboard world") { app.router.go(.home(.normal, tab: .leaderboard)) }
            await step("country tab") { shell.tab = .country }
            await step("weekly tab") { shell.tab = .weekly }
            await step("home") { app.router.go(.home(.normal, tab: .home)) }
            // each page twice: the first open (cold) and a second one (what stays once the first-time costs are paid)
            for round in 1...2 {
                for e in [EventScreen.streakRace, .rocketRace, .skyJump, .claw] {
                    await step("event \(e.rawValue) #\(round)") { app.router.go(.event(e)) }
                    await step("home from \(e.rawValue) #\(round)") { app.router.go(.home(.normal, tab: .home)) }
                }
            }
            let lines = SocOpenProbe.results
            Log.mark("social", "open bench done: \(lines.filter { $0.hasPrefix("bench:") }.count) steps")
            guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
            if let d = try? JSONSerialization.data(withJSONObject: ["lines": lines], options: [.prettyPrinted]) {
                try? d.write(to: docs.appendingPathComponent("lab-open.json"), options: .atomic)
            }
            CaptureReady.mark(screen: "sociallab:open", app: app, file: "lab-ready.json")
        }
    }

    /// One route change under a probe started just before it (a tap handler's moment), 1.6 s of frames.
    private static func step(_ name: String, _ go: () -> Void) async {
        let p = SocOpenProbe("bench:\(name) tap")
        p.begin()
        go()
        try? await Task.sleep(nanoseconds: 1_600_000_000)
        p.end()
        try? await Task.sleep(nanoseconds: 300_000_000)
    }
}
