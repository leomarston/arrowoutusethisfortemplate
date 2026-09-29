import Foundation
import PathCore

// pclevels: the content CLI over PathCore (SPEC-architecture §4.14). C4 owns this file.
// Exit codes: 0 ok, 1 findings / failures, 64 usage, 66 unreadable input.

let usage = """
usage: pclevels <command> [args]
  import <research json> [--reveal <file> …]      phone / video schema -> one bundle v1 line on stdout, report on stderr
  bundle <design/levels.json> <out dir> [--encoded | --publish]
                                                  write level_NNNN.json (each level object as it is; --encoded: C1's
                                                  LevelJSON.encodeBundle form, as tools/levels/lvtool writes it;
                                                  --publish: the shipped form, encoded without capture / source / metrics / "_" notes),
                                                  sessions.json, unlocks.json, tutorials.json, curve.json
  validate <dir | levels.json> [--sprites <dir>] [--no-game-rules] [--publish] [--report <json>]
                                                  the validator (structure, obstacles, values, provenance, sprites,
                                                  solvable, metrics, the game's rules); exit 1 on any error;
                                                  --publish: the shipped form (no capture / source / metrics / "_" note may remain)
  solve <file>                                    greedy + search on one level file
  bot <dir | levels.json> [--rate 0.6] [--mistakes p] [--seed n]
                                                  HeadlessDriver over every level
  gen <from> <to> [--curve <json>] [--out <file>] [--infos <file>] [--provider]
                                                  generated levels (canonical lines); --provider = as served
                                                  (validated, in band or re-rolled: exit 1 on nearest / fallback)
  stats <dir | levels.json>                       the curve table (tag, timer, grid, arrows, units, waves, free, kinds)
  needs <dir | levels.json>                       door / box sizes and sprite ids the content uses
  version                                         the bundle schema this build reads
"""

func fail(_ msg: String, _ code: Int32 = 1) -> Never {
    FileHandle.standardError.write(Data((msg + "\n").utf8))
    exit(code)
}

func err(_ s: String) { FileHandle.standardError.write(Data((s + "\n").utf8)) }

func read(_ path: String) -> Data {
    guard let d = FileManager.default.contents(atPath: path) else { fail("pclevels: cannot read \(path)", 66) }
    return d
}

func option(_ args: [String], _ name: String) -> String? {
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}

func isDir(_ path: String) -> Bool {
    var d: ObjCBool = false
    return FileManager.default.fileExists(atPath: path, isDirectory: &d) && d.boolValue
}

/// Levels from a bundle folder or a levels.json document.
func loadLevels(_ path: String) -> [LevelSpec] {
    if isDir(path) {
        let url = URL(fileURLWithPath: path)
        let names = ((try? FileManager.default.contentsOfDirectory(atPath: path)) ?? []).compactMap { n -> (Int, String)? in
            LevelLibrary.levelNumber(fileName: n).map { ($0, n) }
        }.sorted { $0.0 < $1.0 }
        return names.map { n, name in
            do { return try LevelJSON.decodeBundle(read(url.appendingPathComponent(name).path)) } catch { fail("pclevels: \(name): \(error)") }
        }
    }
    let doc: JSONValue
    do { doc = try ContentJSON.parse(read(path)) } catch { fail("pclevels: \(path): \(error)") }
    if let levels = doc["levels"]?.arrayValue {
        return levels.map { v in
            do { return try JSONDecoder().decode(LevelSpec.self, from: ContentJSON.data(v)) } catch { fail("pclevels: level \(v["level"].map(ContentJSON.write) ?? "?"): \(error)") }
        }
    }
    do { return [try LevelJSON.decodeBundle(read(path))] } catch { fail("pclevels: \(path): \(error)") }
}

func ms(_ a: UInt64, _ b: UInt64) -> Double { Double(b &- a) / 1_000_000 }

let args = Array(CommandLine.arguments.dropFirst())
switch args.first {

case "version"?:
    print("pclevels — bundle schema \(LevelJSON.bundleSchema)")

case "import"?:
    guard args.count >= 2 else { fail(usage, 64) }
    var reveals: [Data] = []
    var i = 2
    while i < args.count {
        if args[i] == "--reveal", i + 1 < args.count { reveals.append(read(args[i + 1])); i += 2 } else { i += 1 }
    }
    do {
        let r = try LevelJSON.load(read(args[1]), reveals: reveals)
        print(ContentJSON.line(r.level, schema: true))
        err("pclevels import: \(r.report)")
    } catch { fail("pclevels import: \(error)") }

case "bundle"?:
    guard args.count >= 3 else { fail(usage, 64) }
    do {
        let doc = try ContentJSON.parse(read(args[1]))
        let out = URL(fileURLWithPath: args[2])
        let s = try ContentBundle.write(doc, to: out, form: args.contains("--publish") ? .publish : args.contains("--encoded") ? .encoded : .asIs)
        print("pclevels bundle: \(s.levels) levels (authored end \(s.authoredEnd)), \(s.files.count) files -> \(out.path)")
    } catch { fail("pclevels bundle: \(error)") }

case "validate"?:
    guard args.count >= 2 else { fail(usage, 64) }
    let sprites: SpriteCatalog? = option(args, "--sprites").map { p in
        do { return try SpriteCatalog.load(folder: URL(fileURLWithPath: p)) } catch { fail("pclevels validate: sprites \(p): \(error)") }
    }
    var opts = Validator.Options()
    if args.contains("--no-game-rules") { opts.gameRules = false }
    if args.contains("--publish") { opts.provenance = .publish }         // PUBLISH B0: App/Resources/Levels ships stripped
    let t0 = DispatchTime.now().uptimeNanoseconds
    let rep: Validator.Report
    if isDir(args[1]) {
        do { rep = try Validator.checkFolder(URL(fileURLWithPath: args[1]), sprites: sprites, options: opts) } catch { fail("pclevels validate: \(error)") }
    } else {
        do { rep = Validator.checkDocument(try ContentJSON.parse(read(args[1])), sprites: sprites, options: opts) } catch { fail("pclevels validate: \(error)") }
    }
    let first = rep.firstAppearance.sorted { $0.value < $1.value }.map { "\($0.key) L\($0.value)" }.joined(separator: ", ")
    print("validated \(rep.levels.count) levels: \(rep.errors.count) error(s), \(rep.warnings.count) warning(s); first appearances \(first); \(String(format: "%.1f", ms(t0, DispatchTime.now().uptimeNanoseconds) / 1000)) s")
    for e in rep.errors.prefix(80) { print("ERROR", e) }
    for w in rep.warnings.prefix(20) { print("WARN", w) }
    if let path = option(args, "--report") {
        let v: JSONValue = .object([
            ("levels", .int(rep.levels.count)),
            ("errors", .array(rep.errors.map { .string($0.description) })),
            ("warnings", .array(rep.warnings.map { .string($0.description) })),
            ("error_areas", .array(rep.errors.map { .string($0.area.rawValue) })),
            ("first_appearance", .object(rep.firstAppearance.map { ($0.key, .int($0.value)) })),
            ("table", .array(rep.levels.map { r in
                guard let m = r.measured else { return .object([("level", .int(r.level)), ("failed", .bool(true))]) }
                return .object([("level", .int(r.level)), ("rounds", .int(m.rounds)), ("free", .int(m.freeAtStart)),
                                ("units", .int(m.units)), ("arrows", .int(m.arrows)), ("bot_time_left", .double(m.botTimeLeft))])
            })),
        ])
        do { try ContentJSON.data(v, newline: true).write(to: URL(fileURLWithPath: path)) } catch { fail("pclevels validate: \(error)") }
    }
    exit(rep.errors.isEmpty ? 0 : 1)

case "solve"?:
    guard args.count >= 2 else { fail(usage, 64) }
    for l in loadLevels(args[1]) {
        let g = Solver.greedy(l)
        let s = Solver.solve(l)
        let cg = ContentRules.greedy(l)
        let verdict: String
        switch s {
        case .solved(let o): verdict = "solved (\(o.count) taps)"
        case .unsolvable: verdict = "UNSOLVABLE"
        case .undecided(let n): verdict = "undecided after \(n) states"
        }
        print("L\(l.level): game greedy \(g.solved ? "solved" : "stuck (\(g.stuck.count) left)") in \(g.rounds) rounds, free at start \(g.freeAtStart); search \(verdict); content greedy \(cg.ok ? "solved" : "stuck")")
    }

case "bot"?:
    guard args.count >= 2 else { fail(usage, 64) }
    let rate = Double(option(args, "--rate") ?? "0.6") ?? 0.6
    let mistakes = Double(option(args, "--mistakes") ?? "0") ?? 0
    let seed = UInt64(option(args, "--seed") ?? "1") ?? 1
    var lost = 0
    for l in loadLevels(args[1]) {
        var c = DriverConfig(tapInterval: rate, mistakes: mistakes, seed: seed)
        c.recordEvents = false
        let r = HeadlessDriver.play(level: l, config: c)
        if !r.won { lost += 1 }
        print(String(format: "L%-4d %@  time left %5.1f / %d s (%3.0f%%)  hearts %d  taps %3d  bumps %d%@", l.level, r.won ? "WON " : "LOST",
                     r.remaining, l.timerSeconds, 100 * r.timeLeftFraction, r.heartsLeft, r.taps, r.bumps,
                     r.won ? "" : "  (\(r.loss.map { "\($0)" } ?? "stuck \(r.stuck.count)"))"))
    }
    print("pclevels bot: \(lost) level(s) not won")
    exit(lost == 0 || mistakes > 0 ? 0 : 1)

case "gen"?:
    guard args.count >= 3, let a = Int(args[1]), let b = Int(args[2]), a <= b else { fail(usage, 64) }
    let curve: CurveSpec
    if let p = option(args, "--curve") {
        do {
            let v = try ContentJSON.parse(read(p))
            curve = try CurveSpec(json: v["curve"] ?? v)
        } catch { fail("pclevels gen: curve \(p): \(error)") }
    } else { curve = .default }
    let provider = args.contains("--provider")
    var lines: [String] = [], infos: [String] = []
    var failures = 0
    for n in a...b {
        let t0 = DispatchTime.now().uptimeNanoseconds
        if provider {
            let (l, rec) = LevelProvider.produce(n, curve: curve, library: nil, options: Validator.Options())
            lines.append(ContentJSON.line(l, schema: true))
            // served in band (its own seed, or a re-roll: SPEC.md §5.27) is fine; nearest / fallback are findings
            if rec.route == .nearest || rec.route == .fallback { failures += 1 }
            err(String(format: "L%d %@ gen %.1f ms  validate %.1f ms  total %.1f ms  seeds %d  roll %d%@", n, rec.route.rawValue, rec.generateMs,
                       rec.validateMs, rec.totalMs, rec.seedsTried, rec.roll,
                       rec.bandViolations.isEmpty ? "" : "  OUT OF BAND: " + rec.bandViolations.joined(separator: "; ")))
            for r in rec.refused where r.contains("out of band") { err("  re-rolled: " + r) }
        } else {
            do {
                let o = try Generator.generate(level: n, curve: curve)
                let t1 = DispatchTime.now().uptimeNanoseconds
                lines.append(ContentJSON.line(o.level, schema: false))
                infos.append(ContentJSON.write(ContentJSON.value(o.info)))
                err(String(format: "L%d %.1f ms  %@ units %d/%d waves %d/%d free %d/%d %dx%d t%d a%@ rej %d", n, ms(t0, t1), o.info.target.tag.rawValue,
                           o.info.units, o.info.target.units, o.info.rounds, o.info.target.rounds, o.info.free, o.info.target.free,
                           o.info.cols, o.info.rows, o.info.timer, o.info.attempt, o.info.rejected.count))
            } catch {
                failures += 1
                err("L\(n) FAILED: \(error)")
            }
        }
    }
    let text = lines.joined(separator: "\n") + "\n"
    if let p = option(args, "--out") { FileManager.default.createFile(atPath: p, contents: Data(text.utf8)) } else { print(text, terminator: "") }
    if let p = option(args, "--infos") { FileManager.default.createFile(atPath: p, contents: Data((infos.joined(separator: "\n") + "\n").utf8)) }
    exit(failures == 0 ? 0 : 1)

case "stats"?:
    guard args.count >= 2 else { fail(usage, 64) }
    print("level  tag        timer  grid    arrows units waves free  cells  mean  bot_left  kinds")
    for l in loadLevels(args[1]) {
        let m = ContentRules.metrics(l)
        let kinds = Dictionary(grouping: l.obstacles.filter { $0.kind != .key }, by: \.kind).map { "\($0.key.rawValue)×\($0.value.count)" }.sorted()
        print(String(format: "L%-4d  %-9@  %5d  %2dx%-3d  %6d %5d %5d %4d  %5d  %4.1f  %8.1f  %@", l.level, l.tag.rawValue, l.timerSeconds, l.cols, l.rows,
                     m.arrows, m.units, m.rounds, m.freeAtStart, m.cells, m.meanLength, m.botTimeLeft, kinds.joined(separator: " ")))
    }

case "needs"?:
    guard args.count >= 2 else { fail(usage, 64) }
    var doors: [String: [Int]] = [:], boxes: [String: [Int]] = [:], sprites: [String: [Int]] = [:]
    for l in loadLevels(args[1]) {
        for o in l.obstacles {
            let xs = o.cells.map(\.c), ys = o.cells.map(\.r)
            if !xs.isEmpty, o.kind == .door || o.kind == .box || o.kind == .curtain {
                let k = "W\(xs.max()! - xs.min()! + 1)H\(ys.max()! - ys.min()! + 1)"
                if o.kind == .door { doors[k, default: []].append(l.level) } else { boxes[k, default: []].append(l.level) }
            }
            for s in Validator.spriteIDs(o) { sprites[s, default: []].append(l.level) }
        }
    }
    func show(_ title: String, _ d: [String: [Int]]) {
        print("\(title) (\(d.count)):")
        for (k, v) in d.sorted(by: { $0.key < $1.key }) { print("  \(k)  \(Array(Set(v)).sorted().map { "L\($0)" }.joined(separator: " "))") }
    }
    show("door sizes (drawn in code: CONSISTENCY O-23)", doors)
    show("box sizes (drawn in code: CONSISTENCY O-21)", boxes)
    show("sprite ids", sprites)

case nil, "-h"?, "--help"?, "help"?:
    print(usage)

default:
    fail("pclevels: unknown command '\(args[0])'\n\(usage)", 64)
}
