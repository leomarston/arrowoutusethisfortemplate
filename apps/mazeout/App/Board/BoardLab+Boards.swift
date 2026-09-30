// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import Foundation
import PathCore

// B1 (SPEC-architecture §5.12 `-pc.labBoard`, §10.4 soak boards). The boards BoardLab and the warm-up load:
//  - `L0NN`: the bundle's level (CONTENT's Levels/level_00NN.json, bundle schema) when it exists, else B1's lab fixture
//    `lab_L0NN.json` — a verbatim copy of the phone reading research/levels/L0NN.json (phone schema; arrows + tapes are
//    used, the other obstacles are carried for B2);
//  - `synth40`: the spike's synthetic 40 × 40 heart (reverse construction, SplitMix64 seed 7, mean length 3.0): the
//    §10.4 soak's 304-arrow board;
//  - `hit`: a small board for the input tests (two parallel arrows two columns apart for the midpoint tie, an isolated
//    horizontal arrow for the 15 pt off-stroke tap, a short arrow for head taps);
//  - `warm`: B1's warm-up board (a turning snake, a 4-lane taped bundle, a bump pair; BoardEngineTests use it);
//  - `warmfx` (B2): the warm-up board with EVERY obstacle kind (tape, box, door + key, pipe, elevator + layer 2, bump);
//  - `corner` (B2): a corner wedge the ray turns at (no shipped level uses one, GP §3.9);
//  - `labb_L0NN.json` (B2): verbatim copies of design/levels.json entries (bundle schema: counters, reveals, pipes'
//    ends, the elevator layers) for the obstacle scenarios and the soak until CONTENT bundles Levels/level_NNNN.json.
// Lab data only: nothing here reaches the game's level flow (GAME reads LevelLibrary, C1/C4).

enum LabBoards {
    static let names = ["L001", "L002", "L003", "L004", "L007", "L011", "L021", "L031", "L032", "L033", "L035", "L039", "L044",
                        "L047", "L049", "L050", "L052", "L054", "synth40", "synth12", "hit", "warm", "warmfx", "corner"]

    static func level(_ name: String, bundle: Bundle) -> LevelSpec? {
        switch name {
        case "synth40": return synthetic(cols: 40, rows: 40, seed: 7, meanLength: 3.0, id: 9040)
        case "synth12": return synthetic(cols: 12, rows: 12, seed: 3, meanLength: 3.0, id: 9012)
        case "hit": return hitBoard()
        case "warm": return warmBoard()
        case "warmfx": return warmEffectsBoard()
        case "corner": return cornerBoard()
        default: break
        }
        let digits = name.filter(\.isNumber)
        guard let n = Int(digits) else { return nil }
        let file = String(format: "level_%04d", n)
        if let u = bundle.url(forResource: file, withExtension: "json", subdirectory: "Levels"),
           let d = try? Data(contentsOf: u), let l = try? JSONDecoder().decode(LevelSpec.self, from: d) {
            return l
        }
        // FIX-2 lane B (N-01): the lab fixtures (labb_ / lab_, research readings) are Debug-only files since L29, so their
        // readers are Debug-only code too — the Release binary carries no research-schema reader or its vocabulary
        #if DEBUG
        let labb = String(format: "labb_L%03d", n)
        if let u = bundle.url(forResource: labb, withExtension: "json"), let d = try? Data(contentsOf: u) {
            do { return try LevelJSON.decodeBundle(labWithoutSource(d)) } catch { Log.error("boardlab", "\(labb).json does not decode: \(error)") }
        }
        let lab = String(format: "lab_L%03d", n)
        guard let u = bundle.url(forResource: lab, withExtension: "json"), let d = try? Data(contentsOf: u) else { return nil }
        do { return try decodePhone(d) } catch {
            Log.error("boardlab", "\(lab).json does not decode: \(error)")
            return nil
        }
        #else
        return nil
        #endif
    }

    #if DEBUG
    // MARK: the phone schema (research/levels/Lnnn.json), minimal reader for the lab (Debug only, FIX-2 B N-01)

    private struct PhoneLevel: Decodable {
        struct Arrow: Decodable { let id: Int; let cells: [Cell]; let dir: Dir }
        struct Obstacle: Decodable { let kind: String; let cells: [Cell] }
        let level: Int
        let cols: Int
        let rows: Int
        let mask: [String]?
        let timer_s: Int?
        let hearts: Int?
        let tag: String?
        let shot: String?
        let arrows: [Arrow]
        let obstacles: [Obstacle]?
    }

    /// FIX-3 B (SPEC.md ruling 55(c)): the labb_ fixtures spell `source` the content pipeline's way, which is a raw value of
    /// the macOS tools' PathCore only — the iOS build's LevelSource raw values are neutral — so the lab drops the key before
    /// decoding (the lab plays the board; where it came from is not used). Anything that is not a JSON object is passed on
    /// unchanged, so a broken fixture still fails in decodeBundle and is logged as before.
    static func labWithoutSource(_ data: Data) -> Data {
        guard var o = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any], o["source"] != nil else { return data }
        o["source"] = nil
        return (try? JSONSerialization.data(withJSONObject: o)) ?? data
    }

    static func decodePhone(_ data: Data) throws -> LevelSpec {
        let p = try JSONDecoder().decode(PhoneLevel.self, from: data)
        let arrows = p.arrows.map { ArrowSpec(id: ArrowID($0.id), cells: $0.cells, dir: $0.dir) }
        var obstacles: [ObstacleSpec] = []
        var counters: [String: Int] = [:]
        for o in p.obstacles ?? [] {
            let kind: ObstacleKind
            switch o.kind {
            case let k where k.hasPrefix("tape"): kind = .tape
            case "door": kind = .door
            case "key": kind = .key
            case "pipe": kind = .pipe
            case "box": kind = .box
            default: continue                                   // box_part and research-only blobs
            }
            let prefix = String(kind.rawValue.prefix(1))
            let k = counters[prefix, default: 0]
            counters[prefix] = k + 1
            let cellSet = Set(o.cells)
            let members = kind == .tape ? arrows.filter { !cellSet.isDisjoint(with: $0.cells) }.map(\.id) : []
            obstacles.append(ObstacleSpec(id: ObstacleID("\(prefix)\(k)"), kind: kind, cells: o.cells, arrows: members))
        }
        return LevelSpec(level: p.level, source: .authored, capture: p.shot, cols: p.cols, rows: p.rows, mask: p.mask,
                         timerSeconds: p.timer_s ?? 180, hearts: p.hearts ?? 3, tag: LevelTag(label: p.tag) ?? .normal,
                         arrows: arrows, obstacles: obstacles)
    }
    #endif

    // MARK: crafted boards

    private static func arrow(_ id: Int, _ cells: [(Int, Int)], _ dir: Dir) -> ArrowSpec {
        ArrowSpec(id: ArrowID(id), cells: cells.map { Cell($0.0, $0.1) }, dir: dir)
    }

    /// 7 × 9, opens at the 28.07 pt cap.
    static func hitBoard() -> LevelSpec {
        let arrows = [
            arrow(0, [(1, 4), (1, 3), (1, 2)], .up),            // left of the tie pair
            arrow(1, [(2, 4), (2, 3), (2, 2)], .up),            // right of the tie pair (the adjacent column: the
                                                                // midpoint is their cell boundary, 14 pt from each)
            arrow(2, [(1, 7), (2, 7), (3, 7)], .right),         // isolated horizontal (rows 6 and 8 empty)
            arrow(3, [(5, 4), (5, 3)], .up),                    // short: head taps
            arrow(4, [(5, 6), (6, 6)], .right),                 // spare
        ]
        return LevelSpec(level: 9001, source: .designed, cols: 7, rows: 9, timerSeconds: 180, arrows: arrows)
    }

    /// 10 × 10: a taped 4-lane bundle, a turning snake, a vertical pair and a bump (arrow 8 is blocked by arrow 9).
    static func warmBoard() -> LevelSpec {
        var arrows: [ArrowSpec] = []
        for r in 0..<4 { arrows.append(arrow(r, [(0, r), (1, r), (2, r)], .right)) }
        arrows.append(arrow(4, [(5, 9), (5, 8), (5, 7), (6, 7), (7, 7)], .right))
        arrows.append(arrow(5, [(9, 9), (9, 8)], .up))
        arrows.append(arrow(6, [(8, 5), (8, 4)], .up))
        arrows.append(arrow(7, [(7, 9), (8, 9)], .right))
        arrows.append(arrow(8, [(0, 6), (1, 6)], .right))
        arrows.append(arrow(9, [(4, 6), (4, 5)], .up))
        let tape = ObstacleSpec(id: "t0", kind: .tape, cells: (0..<4).map { Cell(1, $0) }, arrows: (0..<4).map { ArrowID($0) })
        return LevelSpec(level: 9000, source: .designed, cols: 10, rows: 10, timerSeconds: 180, arrows: arrows,
                         obstacles: [tape])
    }

    /// 14 × 14: every obstacle kind (B2) — the shipping warm-up's board, `WarmBoards.effectsBoard()` (Board/WarmBoard.swift).
    static func warmEffectsBoard() -> LevelSpec { WarmBoards.effectsBoard() }

    /// 8 × 8: arrow 0 moves LEFT along row 2 into the corner c0 at (3, 2) (`upRight` accepts up → right and, reversed,
    /// left → down), turns down column 3 and leaves at the bottom; arrow 1 is a plain second exit.
    static func cornerBoard() -> LevelSpec {
        let arrows = [arrow(0, [(7, 2), (6, 2)], .left),
                      arrow(1, [(1, 6), (2, 6)], .right)]
        let obs = [ObstacleSpec(id: "c0", kind: .corner, cells: [Cell(3, 2)], turn: .upRight)]
        return LevelSpec(level: 9101, source: .designed, capture: "B2 corner lab", cols: 8, rows: 8, timerSeconds: 180,
                         arrows: arrows, obstacles: obs)
    }

    // MARK: the spike's synthetic heart (design/spike-src/App/Core/Generator.swift, verbatim logic)

    private struct SplitMix64: RandomNumberGenerator {
        private var state: UInt64
        init(seed: UInt64) { state = seed }
        mutating func next() -> UInt64 {
            state &+= 0x9E37_79B9_7F4A_7C15
            var z = state
            z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
            z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
            return z ^ (z >> 31)
        }
    }

    static func heartMask(cols: Int, rows: Int) -> [String] {
        var out: [String] = []
        for r in 0..<rows {
            var line = ""
            for c in 0..<cols {
                let x: Double = (Double(c) + 0.5) / Double(cols) * 2.44 - 1.22
                let y: Double = 1.28 - (Double(r) + 0.5) / Double(rows) * 2.36
                let a: Double = x * x + y * y - 1
                let x2y3: Double = x * x * y * y * y
                let v: Double = a * a * a - x2y3
                line.append(v <= 0 ? "#" : ".")
            }
            out.append(line)
        }
        return out
    }

    static func synthetic(cols: Int, rows: Int, seed: UInt64, meanLength: Double, id: Int) -> LevelSpec {
        var rng = SplitMix64(seed: seed)
        let mask = heartMask(cols: cols, rows: rows)
        let bits: [[Bool]] = mask.map { $0.map { $0 == "#" } }
        func inMask(_ p: Cell) -> Bool { p.c >= 0 && p.r >= 0 && p.c < cols && p.r < rows && bits[p.r][p.c] }
        var used = [[Bool]](repeating: [Bool](repeating: false, count: cols), count: rows)
        var placed: [(cells: [Cell], dir: Dir)] = []
        var order: [(Cell, Double)] = []
        let cx = Double(cols - 1) / 2, cy = Double(rows - 1) / 2
        for r in 0..<rows {
            for c in 0..<cols where bits[r][c] {
                let base: Double = hypot(Double(c) - cx, Double(r) - cy)
                let d: Double = base + Double.random(in: 0..<2.5, using: &rng)
                order.append((Cell(c, r), d))
            }
        }
        order.sort { $0.1 < $1.1 }
        func rayClear(_ cells: [Cell], _ dir: Dir) -> Bool {
            let own = Set(cells)
            var p = cells[cells.count - 1] + dir
            while p.c >= 0 && p.r >= 0 && p.c < cols && p.r < rows {
                if own.contains(p) || used[p.r][p.c] { return false }
                p = p + dir
            }
            return true
        }
        func place(_ path: [Cell]) -> (cells: [Cell], dir: Dir)? {
            guard let fwd = Dir(from: path[path.count - 2], to: path[path.count - 1]) else { return nil }
            let rev = Array(path.reversed())
            guard let back = Dir(from: rev[rev.count - 2], to: rev[rev.count - 1]) else { return nil }
            let a = rayClear(path, fwd), b = rayClear(rev, back)
            if a && b { return Bool.random(using: &rng) ? (path, fwd) : (rev, back) }
            if a { return (path, fwd) }
            if b { return (rev, back) }
            return nil
        }
        for (start, _) in order where !used[start.r][start.c] {
            var target = 2
            while target < 30 && Double.random(in: 0..<1, using: &rng) < 1 - 1 / (meanLength - 1) { target += 1 }
            var path = [start]
            var taken = Set([start])
            var dir = Dir.allCases.randomElement(using: &rng)!
            while path.count < target {
                let turn: [Dir] = (dir == .up || dir == .down) ? [.left, .right] : [.up, .down]
                let options: [Dir] = Double.random(in: 0..<1, using: &rng) < 0.6
                    ? [dir] + turn.shuffled(using: &rng) : turn.shuffled(using: &rng) + [dir]
                guard let next = options.first(where: { d in
                    let q = path[path.count - 1] + d
                    return inMask(q) && !used[q.r][q.c] && !taken.contains(q)
                }) else { break }
                let q = path[path.count - 1] + next
                path.append(q)
                taken.insert(q)
                dir = next
            }
            var result: (cells: [Cell], dir: Dir)?
            while path.count >= 2 {
                if let a = place(path) { result = a; break }
                path.removeLast()
            }
            if let a = result {
                placed.append(a)
                for p in a.cells { used[p.r][p.c] = true }
            }
        }
        let arrows = placed.enumerated().map { ArrowSpec(id: ArrowID($0.offset), cells: $0.element.cells, dir: $0.element.dir) }
        return LevelSpec(level: id, source: .generated, capture: "synthetic heart seed \(seed) mean \(meanLength)", cols: cols,
                         rows: rows, mask: mask, timerSeconds: 180, arrows: arrows, seed: seed)
    }
}
#endif
