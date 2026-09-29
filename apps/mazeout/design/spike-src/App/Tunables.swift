import UIKit

/// Every tunable of the spike, overridable by launch arguments (`-pc.<key> <value>` lands in UserDefaults'
/// argument domain). Motion values are PLACEHOLDERS until the motion analyst measures the original.
struct Tunables {
    enum TrailStyle: String { case solid, dash, gradient, none }

    // level / scenario
    var level = "synth"                // synth | L032rec | any bundled/tmp JSON name
    var scenario = "none"              // none | exit5 | trail | bump | crisp | tapfirst
    var seed: UInt64 = 7
    var synthMean = 3.0
    var initialZoom: CGFloat = 1

    // zoom (zoomScale 1 = fit; the original shrinks to ~0.75x of fit, research 006)
    var zoomMin: CGFloat = 0.75
    var zoomMax: CGFloat = 3

    // exit (constant speed; v in SCREEN pt/s, board speed = v / zoom) — placeholder until measured
    var exitSpeed: CGFloat = 900
    var exitSpeedIsScreenSpace = true
    var exitAccel: Double = 0

    // bump: forward to the blocker, back; red from contact
    var bumpBackDuration: Double = 0.22
    var bumpRed = UIColor(red: 1, green: 0.23, blue: 0.23, alpha: 1)
    var bumpTintPersists = false
    var bumpTintFade: Double = 0.35

    // trail (store shots 1 + 5): the exiting arrow is painted with a repeating hue gradient along its arc
    // length (period ~5.6 cells, hue rising toward the head), with star confetti shed at the tail
    /// Phone (research/levels.md): the exiting arrow turns solid light blue #10A2EF (shots/010). The rainbow of
    /// store shots 1/5 is a second look (skin/event?) — both are proven here.
    var trail = TrailStyle.solid
    var exitColor = UIColor(red: 16 / 255, green: 162 / 255, blue: 239 / 255, alpha: 1)
    var trailPeriodCells: CGFloat = 5.6
    var trailMoves = false             // false = bands fixed on the path (the body slides through them)
    var dashSteps = 24
    var stars = true
    var starBirthRate: Float = 70
    var starLifetime: Float = 0.9

    // dots
    var dotColor = UIColor(red: 197 / 255, green: 225 / 255, blue: 1, alpha: 1)   // #C5E1FF measured
    var dotFade: Double = 0.12

    // freeze the stage this long after the scenario action (for deterministic screenshots); < 0 = never
    var freezeAfter: Double = -1
    var slowmo: Float = 1

    // measurement
    var measureSeconds: Double = 3
    var waves = 4
    var waveGap: Double = 0.7
    var perWave = 5

    static let shared = Tunables()

    init() {
        let d = UserDefaults.standard
        func s(_ k: String) -> String? { d.string(forKey: "pc." + k) }
        func n(_ k: String) -> Double? { s(k).flatMap(Double.init) }
        if let v = s("level") { level = v }
        if let v = s("scenario") { scenario = v }
        if let v = n("seed") { seed = UInt64(v) }
        if let v = n("mean") { synthMean = v }
        if let v = n("zoom") { initialZoom = CGFloat(v) }
        if let v = n("zoomMin") { zoomMin = CGFloat(v) }
        if let v = n("zoomMax") { zoomMax = CGFloat(v) }
        if let v = n("speed") { exitSpeed = CGFloat(v) }
        if let v = n("speedScreen") { exitSpeedIsScreenSpace = v != 0 }
        if let v = n("accel") { exitAccel = v }
        if let v = n("bumpBack") { bumpBackDuration = v }
        if let v = n("bumpPersist") { bumpTintPersists = v != 0 }
        if let v = s("trail"), let t = TrailStyle(rawValue: v) { trail = t }
        if let v = n("period") { trailPeriodCells = CGFloat(v) }
        if let v = n("trailMoves") { trailMoves = v != 0 }
        if let v = n("dashSteps") { dashSteps = Int(v) }
        if let v = n("stars") { stars = v != 0 }
        if let v = n("freeze") { freezeAfter = v }
        if let v = n("slowmo") { slowmo = Float(v) }
        if let v = n("measure") { measureSeconds = v }
        if let v = n("waves") { waves = Int(v) }
        if let v = n("perWave") { perWave = Int(v) }
        if let v = n("waveGap") { waveGap = v }
    }

    /// Store shot 1 hue walk along the arc toward the head: magenta, red, orange, yellow, green, cyan, blue.
    static let rainbow: [UIColor] = [
        UIColor(red: 1.00, green: 0.20, blue: 0.95, alpha: 1),   // magenta  h≈300
        UIColor(red: 1.00, green: 0.18, blue: 0.10, alpha: 1),   // red      h≈5
        UIColor(red: 1.00, green: 0.55, blue: 0.00, alpha: 1),   // orange   h≈30
        UIColor(red: 1.00, green: 0.88, blue: 0.00, alpha: 1),   // yellow   h≈50
        UIColor(red: 0.10, green: 0.92, blue: 0.10, alpha: 1),   // green    h≈120
        UIColor(red: 0.00, green: 0.85, blue: 1.00, alpha: 1),   // cyan     h≈190
        UIColor(red: 0.10, green: 0.45, blue: 1.00, alpha: 1),   // blue     h≈215
    ]
}

/// Colour of the repeating palette at phase x in [0, 1) (linear RGB interpolation, wraps).
func paletteColor(_ palette: [UIColor], _ x: CGFloat) -> UIColor {
    let n = palette.count
    var f = x.truncatingRemainder(dividingBy: 1)
    if f < 0 { f += 1 }
    let k = f * CGFloat(n)
    let i = Int(k) % n, j = (i + 1) % n
    let t = k - CGFloat(Int(k))
    var r0: CGFloat = 0, g0: CGFloat = 0, b0: CGFloat = 0, a0: CGFloat = 0
    var r1: CGFloat = 0, g1: CGFloat = 0, b1: CGFloat = 0, a1: CGFloat = 0
    palette[i].getRed(&r0, green: &g0, blue: &b0, alpha: &a0)
    palette[j].getRed(&r1, green: &g1, blue: &b1, alpha: &a1)
    return UIColor(red: r0 + (r1 - r0) * t, green: g0 + (g1 - g0) * t, blue: b0 + (b1 - b0) * t, alpha: 1)
}
