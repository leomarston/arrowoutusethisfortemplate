import Foundation
import GameCore

// C4 (SPEC-gameplay §14.3 step 3; design/tools/gen_levels.py `mask_for`). The generator's silhouettes: integer-exact
// shapes (the heart uses only correctly rounded IEEE products and sums, written out one operation at a time so that the
// Swift and Python results are the same bits). A silhouette decides which cells the tiler fills; the level's JSON keeps
// `mask: null` (the silhouette is the arrow cells, VERIFIED vlev-A §6).

public enum Silhouettes {
    /// Names the curve may list (`curve.silhouette.shapes`).
    public static let names = ["oval", "octagon", "notch", "blocks", "cross", "heart", "diamond", "arch"]

    /// The playable cells of `shape` on a W × H grid (row-major flags); nil for an unknown shape (= the full rectangle).
    public static func mask(_ shape: String, cols W: Int, rows H: Int) -> [Bool] {
        var out = [Bool](repeating: false, count: W * H)
        for r in 0..<H {
            for c in 0..<W {
                let dx = 2 * c - (W - 1), dy = 2 * r - (H - 1)          // doubled offsets from the centre
                let ok: Bool
                switch shape {
                case "oval":
                    ok = dx * dx * H * H + dy * dy * W * W <= W * W * H * H
                case "octagon":
                    ok = abs(dx) + abs(dy) <= floorDiv((W + H) * 5, 6)
                case "diamond":
                    ok = abs(dx) * H + abs(dy) * W <= floorDiv(W * H * 4, 3)
                case "notch":
                    ok = !(c >= floorDiv(W, 2) && abs(dy) < floorDiv(H, 3))
                case "blocks":
                    let top = r < floorDiv(H * 2, 5)
                    ok = top || (r != floorDiv(H * 2, 5) && abs(dx) > 1)
                case "cross":
                    ok = abs(dx) <= floorDiv(W * 2, 3) || abs(dy) <= floorDiv(H * 2, 3)
                case "heart":
                    // x = (c + 0.5) / W * 2.44 - 1.22 ; y = 1.28 - (r + 0.5) / H * 2.36 ; left to right, no fusion
                    let x0 = (Double(c) + 0.5) / Double(W)
                    let x1 = x0 * 2.44
                    let x = x1 - 1.22
                    let y0 = (Double(r) + 0.5) / Double(H)
                    let y1 = y0 * 2.36
                    let y = 1.28 - y1
                    let xx = x * x
                    let yy = y * y
                    let a = (xx + yy) - 1
                    let aaa = (a * a) * a
                    let xxyyy = (((xx * y) * y) * y)
                    ok = aaa - xxyyy <= 0
                case "arch":
                    ok = dy >= 0 || dx * dx * H * H + dy * dy * W * W <= W * W * H * H
                default:
                    ok = true
                }
                if ok { out[r * W + c] = true }
            }
        }
        return out
    }

    /// Python's `//` (floor division) for the generator's integer maths.
    @inline(__always) static func floorDiv(_ a: Int, _ b: Int) -> Int {
        let q = a / b
        return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q
    }
}
