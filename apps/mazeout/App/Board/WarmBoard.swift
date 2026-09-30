import Foundation
import PathCore

// B2: the board the launch warm-up (Board/WarmUp.swift) plays behind Loading — every obstacle kind, so each layer's first
// use is paid before the first level. Crafted in code (no file). Shipping code: it was `LabBoards.warmEffectsBoard()` in
// BoardLab+Boards.swift until the labs became Debug / Measure only; BoardLab's `warmfx` board forwards here.

enum WarmBoards {
    private static func arrow(_ id: Int, _ cells: [(Int, Int)], _ dir: Dir) -> ArrowSpec {
        ArrowSpec(id: ArrowID(id), cells: cells.map { Cell($0.0, $0.1) }, dir: dir)
    }

    /// 14 × 14: every obstacle kind the warm-up must compile (B2). Arrows (tail → head):
    /// 0/1 a taped pair → right (rows 0, 1); 3 bumps into 4 (row 3); 4 ↑ (column 3); 5 → with the key k0 (row 5);
    /// door d0 (cols 10–13, rows 7–10) hiding 6; pipe p0 (row 12, cols 3–5, 1 pass) for 7; box b0 (cols 0–2, rows 8–10,
    /// counter 1) hiding 9; elevator e0 (cols 5–8, rows 8–10) carrying 8, hiding the layer-2 arrow 11.
    static func effectsBoard() -> LevelSpec {
        var a: [ArrowSpec] = []
        a.append(arrow(0, [(0, 0), (1, 0), (2, 0)], .right))
        a.append(arrow(1, [(0, 1), (1, 1), (2, 1)], .right))
        a.append(arrow(3, [(0, 3), (1, 3)], .right))
        a.append(arrow(4, [(3, 4), (3, 3)], .up))
        a.append(arrow(5, [(0, 5), (1, 5), (2, 5)], .right))
        a.append(ArrowSpec(id: ArrowID(6), cells: [Cell(11, 8), Cell(12, 8)], dir: .right, hiddenBy: "d0"))
        a.append(arrow(7, [(0, 12), (1, 12)], .right))
        a.append(arrow(8, [(6, 10), (6, 9)], .up))
        a.append(ArrowSpec(id: ArrowID(9), cells: [Cell(0, 9), Cell(1, 9)], dir: .right, hiddenBy: "b0"))
        a.append(ArrowSpec(id: ArrowID(11), cells: [Cell(7, 9), Cell(7, 8)], dir: .up, layer: 2, hiddenBy: "e0"))
        func block(_ c0: Int, _ r0: Int, _ c1: Int, _ r1: Int) -> [Cell] {
            var out: [Cell] = []
            for r in r0...r1 { for c in c0...c1 { out.append(Cell(c, r)) } }
            return out
        }
        let obs: [ObstacleSpec] = [
            ObstacleSpec(id: "t0", kind: .tape, cells: [Cell(1, 0), Cell(1, 1)], arrows: [ArrowID(0), ArrowID(1)]),
            ObstacleSpec(id: "k0", kind: .key, cells: [Cell(0, 5), Cell(1, 5)], arrows: [ArrowID(5)]),
            ObstacleSpec(id: "d0", kind: .door, cells: block(10, 7, 13, 10), order: 0, reveals: [ArrowID(6)]),
            ObstacleSpec(id: "p0", kind: .pipe, cells: [Cell(3, 12), Cell(4, 12), Cell(5, 12)],
                         ends: [PipeEnd(cell: Cell(3, 12), out: .left), PipeEnd(cell: Cell(5, 12), out: .right)],
                         counter: 1, counterAt: [4, 12]),
            ObstacleSpec(id: "b0", kind: .box, cells: block(0, 8, 2, 10), counter: 1, reveals: [ArrowID(9)]),
            ObstacleSpec(id: "e0", kind: .elevator, cells: block(5, 8, 8, 10), arrows: [ArrowID(8)], reveals: [ArrowID(11)]),
        ]
        return LevelSpec(level: 9100, source: .designed, capture: "B2 warm-up: every obstacle", cols: 14, rows: 14,
                         timerSeconds: 180, arrows: a, obstacles: obs)
    }
}
