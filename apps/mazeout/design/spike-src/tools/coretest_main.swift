import Foundation
let t0 = Date()
let url = URL(fileURLWithPath: "/Users/yago/Downloads/app-factory/apps/mazeout/build/spike/App/L032rec.json")
let l32 = try! JSONDecoder().decode(LevelSpec.self, from: Data(contentsOf: url))
print("L32 arrows", l32.arrows.count, "cells", l32.cellCount, "problems", BoardState.validate(l32))
let g = BoardState.greedy(l32)
print("L32 greedy stuck", g.stuck, "rounds", g.rounds, "free at start", BoardState(level: l32).freeArrows().count)
for seed: UInt64 in [7, 11, 23] {
  for mean in [3.0, 3.4, 3.8] {
    let t = Date()
    let s = Generator.synthetic(seed: seed, meanLength: mean)
    let gg = BoardState.greedy(s)
    let masked = s.mask!.joined().filter { $0 == "#" }.count
    let lens = s.arrows.map { $0.cells.count }
    print("seed", seed, "mean", mean, "arrows", s.arrows.count, "cells", s.cellCount, "/", masked, "maxLen", lens.max()!, "stuck", gg.stuck.count, "rounds", gg.rounds, "problems", BoardState.validate(s).count, String(format: "%.0f ms", Date().timeIntervalSince(t) * 1000))
  }
}
let s = Generator.synthetic(seed: 7, meanLength: 3.4)
print(s.mask!.joined(separator: "\n"))
// render arrows as ascii
var grid = Array(repeating: Array(repeating: Character(" "), count: s.cols), count: s.rows)
for a in s.arrows { for p in a.cells { grid[p.r][p.c] = "o" }; let h = a.head; grid[h.r][h.c] = ["up": "^", "down": "v", "left": "<", "right": ">"][a.dir.rawValue]! }
print(grid.map { String($0) }.joined(separator: "\n"))
let enc = JSONEncoder(); enc.outputFormatting = [.sortedKeys]
try! enc.encode(s).write(to: URL(fileURLWithPath: "synthetic.json"))
// TravelProfile sanity
let tp = TravelProfile(v: 600, accel: 0.1)
for s in [0, 10, 30, 100, 300] as [CGFloat] { let t = tp.time(toReach: s); print("s", s, "t", t, "back", tp.travel(at: t)) }
print("total ms", Date().timeIntervalSince(t0) * 1000)
