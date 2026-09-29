import Foundation

/// Spike generator: dense solvable snakes inside a silhouette (perf/density test board). The real generator
/// (difficulty = dependency depth, obstacles, curve) is PathCore work, see tech-spike.md.
enum Generator {
    /// Classic heart curve, sampled at cell centres; '#' = playable.
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

    /// Reverse construction, centre outwards: each new arrow's head ray must miss every arrow placed before
    /// it, so removing arrows in reverse placement order always works (solvable by construction). Placing
    /// from the centre out keeps the outward rays clear, which is what makes a dense fill possible.
    static func synthetic(cols: Int = 40, rows: Int = 40, seed: UInt64 = 7, meanLength: Double = 3.4) -> LevelSpec {
        var rng = SplitMix64(seed: seed)
        let mask = heartMask(cols: cols, rows: rows)
        let maskBits: [[Bool]] = mask.map { $0.map { $0 == "#" } }
        func inMask(_ p: Cell) -> Bool { p.c >= 0 && p.r >= 0 && p.c < cols && p.r < rows && maskBits[p.r][p.c] }
        var used = [[Bool]](repeating: [Bool](repeating: false, count: cols), count: rows)
        var arrows: [ArrowSpec] = []
        var order: [(Cell, Double)] = []
        let cx = Double(cols - 1) / 2, cy = Double(rows - 1) / 2
        for r in 0..<rows {
            for c in 0..<cols where maskBits[r][c] {
                let d: Double = hypot(Double(c) - cx, Double(r) - cy) + Double.random(in: 0..<2.5, using: &rng)
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
        func place(_ path: [Cell]) -> ArrowSpec? {
            let fwd = Dir(from: path[path.count - 2], to: path[path.count - 1])!
            let rev = Array(path.reversed())
            let back = Dir(from: rev[rev.count - 2], to: rev[rev.count - 1])!
            let a = rayClear(path, fwd), b = rayClear(rev, back)
            if a && b { return Bool.random(using: &rng) ? ArrowSpec(cells: path, dir: fwd) : ArrowSpec(cells: rev, dir: back) }
            if a { return ArrowSpec(cells: path, dir: fwd) }
            if b { return ArrowSpec(cells: rev, dir: back) }
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
            var placed: ArrowSpec?
            while path.count >= 2 {
                if let a = place(path) { placed = a; break }
                path.removeLast()
            }
            if let a = placed {
                arrows.append(a)
                for p in a.cells { used[p.r][p.c] = true }
            }
        }
        return LevelSpec(id: 9001, cols: cols, rows: rows, arrows: arrows, tapes: nil, mask: mask,
                         timeLimit: 180, hearts: 3, source: "synthetic heart seed \(seed) mean \(meanLength)")
    }
}
