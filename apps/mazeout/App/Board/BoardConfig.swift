import UIKit
import PathCore

// B1 (SPEC-architecture §5, §10, §14). BOARD's knobs resolved ONCE per engine from Tuning/board.json (+ `-pc.tune board.*`).
// Every value a content spec still owns (PENDING-motion-audio / -gameplay / -ui) is DATA in board.json; the defaults below
// are only the fallback when a key is missing, and each cites its source. research/motion.md pass 2 (the phone, v552) is
// the stand-in for SPEC-motion-audio until it lands (SPEC.md §4), so its numbers win over the older pass-1 values that
// SPEC-architecture quotes (the differences are listed in the B1 report).

struct BoardConfig {
    // MARK: layout, zoom, pan (§4.2, §5.2)
    /// The play rect on the 393 × 852 reference: HUD bottom 122 pt, booster top 755 pt (VERIFIED spike). Other heights keep
    /// the top offset and the bottom gap (852 − 755 = 97 pt).
    var playTop: CGFloat
    var playBottomGap: CGFloat
    /// Minimum zoom as an ABSOLUTE pitch (motion §6.7 VERIFIED pass 2: 14.04 pt; a board opening at 14.0 cannot zoom out).
    /// ≤ 0 falls back to `zoomMinOfFit` × fit (SPEC-architecture §5.2: 0.786).
    var zoomMinPitch: Double
    var zoomMinOfFit: Double
    var zoomMaxPitch: Double
    var panSlack: CGFloat
    var panBounces: Bool
    // MARK: input (§5.3)
    var slop: CGFloat
    var hitRadius: Double
    var tieRightThenDown: Bool
    var tieTolerance: Double
    var tieTolerancePitch: Double
    // MARK: arrow look (§5.4; motion §2.2)
    var cornerFillet: Double          // centre-line fillet radius, × pitch (motion §2.2: R ≈ 0.125)
    var tailExtend: Double            // the path starts this far behind the tail centre, × pitch (motion §2.2: 0.14 − w/2 = 0.03)
    var strokeSnapPx: Bool            // lineWidth rounded to whole device pixels at fit (motion §2.2)
    /// The head as SEEN (× pitch, from the head cell centre along the direction): base edge, visible tip, base width,
    /// corner radius. nil = PathCore's `Metrics` (sharp apex `headApexPast`, length `headLength`, all corners rounded).
    var head: [Dir: HeadSpec]?
    // MARK: colours
    var ink: CGColor
    var exitColor: CGColor
    var markedColor: CGColor
    var dotColor: CGColor
    var ladder: [String]
    // MARK: exit (§5.5, D5; motion §3.3 pass 2)
    var exitV0: Double
    var exitVmax: Double
    var exitTau: Double
    var colourRamp: Double
    var keyframeStep: Double
    var farOutsetOfScreen: Double
    /// FEEL F3 (build/phone2/latency.md): a tap's motion (exit / bump keyframes, their stars and beats) begins this long
    /// BEFORE the release's run-loop turn, so the first presented frame that shows the ripple already shows the arrow
    /// moving (v552: ripple and first arrow change on the same frame, 8 of 8; ours showed the ripple a frame early in 2 of 13).
    var tapMotionLead: Double
    var leftBoardAtLastCell: Bool
    // MARK: bump (§5.5; motion §4 pass 2, v552)
    var bumpOutBase: Double
    var bumpOutPerCell: Double
    var bumpHold: Double
    var bumpBack: Double
    var bumpRedFrom: Double
    var bumpRedTo: Double
    var blockerRedFrom: Double
    var blockerRedTo: Double
    var blockerBlackAt: Double
    var badgePitch: Double
    var badgeInFrom: Double
    var badgeInTo: Double
    var badgeHoldTo: Double
    var badgeOutTo: Double
    var badgeScaleIn: Double
    var badgeScaleOut: Double
    var badgeFill: CGColor
    var badgeOutline: CGColor
    // MARK: vignette (§5.8; motion §4)
    var vignetteAlpha: Double
    var vignetteDecayPt: Double
    var vignetteHold: Double
    var vignetteTotal: Double
    // MARK: ripple (§5.8; motion §3.1 + research/motion-tools/out/ripple_*.txt)
    var rippleTimes: [Double]
    var rippleRadius: [Double]
    var rippleCoreLum: [Double]
    var rippleRingLum: [Double]
    var rippleCoreRadius: Double
    /// FEEL F2: the core's radius on the release frame (the flat 180 disc), then `rippleCoreRadius`.
    var rippleCoreFirstRadius: Double
    /// B1's soft-edge width. Unused since FEEL F2 (the ripple is two crisp flat discs); kept so the data key still parses.
    var rippleEdgeSoft: Double
    var ripplePool: Int
    // MARK: intro (§5.7; motion §6.1 pass 2)
    var introZoomFrom: Double
    var introZoomDuration: Double
    var introDrawBase: Double
    var introDrawPerCell: Double
    // MARK: warm-up, perf, probe (§5.9, §9.4, §10)
    var stageGap: Double
    var warmupSpeed: Double
    var spriteCacheCapMB: Double
    var hitchMs: Double
    var probeHz: Double

    init(_ t: BoardTuning) {
        let f = t.file
        playTop = CGFloat(f.double("layout.playTop", 122))
        playBottomGap = CGFloat(f.double("layout.playBottomGap", 97))
        zoomMinPitch = f.double("zoom.minPitch", 14.036)
        zoomMinOfFit = t.zoomMin
        zoomMaxPitch = t.zoomMaxPitch
        panSlack = CGFloat(t.panSlackPt)
        panBounces = t.panBounces
        slop = CGFloat(t.slopPt)
        hitRadius = t.hitRadiusPt
        tieRightThenDown = t.tieBreak != "leftThenUp"
        tieTolerance = f.double("input.tieTolerancePt", 1.0)
        tieTolerancePitch = f.double("input.tieTolerancePitch", 0.03)
        cornerFillet = f.double("arrow.cornerFillet", 0.125)
        tailExtend = f.double("arrow.tailExtend", 0.03)
        strokeSnapPx = f.bool("arrow.strokeSnapPx", true)
        if f.has("arrow.head.width") {
            let w = f.double("arrow.head.width", Metrics.headBase)
            let r = f.double("arrow.head.corner", Metrics.headCornerRadius)
            func spec(_ k: String, _ d: Dir) -> HeadSpec {
                let tipFallback = Metrics.headApexPast(d)
                return HeadSpec(base: f.double("arrow.head.\(k).base", tipFallback - Metrics.headLength),
                                tip: f.double("arrow.head.\(k).tip", tipFallback), width: w, corner: r)
            }
            let h = spec("horizontal", .right)
            head = [.right: h, .left: h, .up: spec("up", .up), .down: spec("down", .down)]
        } else {
            head = nil
        }
        ink = Self.color(t.inkColor)
        exitColor = Self.color(t.exitColor)
        markedColor = Self.color(t.markedColor)
        dotColor = Self.color(t.dotColor)
        ladder = t.comboLadder
        exitV0 = f.double("exit.v0", 7.67)
        exitVmax = f.double("exit.vmax", 73.86)
        exitTau = f.double("exit.tau", 0.353)
        colourRamp = t.exitColourRamp
        keyframeStep = f.double("exit.keyframeStep", 1.0 / 60)
        farOutsetOfScreen = f.double("exit.farOutsetOfScreen", 0.25)
        tapMotionLead = max(0, f.double("exit.tapMotionLead", 1.0 / 60))
        leftBoardAtLastCell = f.string("exit.leftBoardAt", "lastCell") == "lastCell"
        bumpOutBase = f.double("bump.outBase", 0.075)
        bumpOutPerCell = f.double("bump.outPerCell", 0.025)
        bumpHold = t.bumpHold
        bumpBack = t.bumpBack
        bumpRedFrom = f.double("bump.redFrom", 0.017)
        bumpRedTo = f.double("bump.redTo", 0.12)
        blockerRedFrom = f.double("bump.blockerRedFrom", 0.02)
        blockerRedTo = f.double("bump.blockerRedTo", 0.12)
        blockerBlackAt = f.double("bump.blockerBlackAt", 0.33)
        badgePitch = f.double("bump.badgePitch", 1.0)
        badgeInFrom = f.double("bump.badgeInFrom", 0.017)
        badgeInTo = f.double("bump.badgeInTo", 0.12)
        badgeHoldTo = f.double("bump.badgeHoldTo", 0.33)
        badgeOutTo = f.double("bump.badgeOutTo", 0.43)
        badgeScaleIn = f.double("bump.badgeScaleIn", 1.4)
        badgeScaleOut = f.double("bump.badgeScaleOut", 0.5)
        badgeFill = Self.color(f.string("bump.badgeFill", "#F62631"))
        badgeOutline = Self.color(f.string("bump.badgeOutline", "#7A0A10"))
        vignetteAlpha = f.double("vignette.alpha", 0.42)
        vignetteDecayPt = f.double("vignette.decayPt", 27)
        vignetteHold = f.double("vignette.hold", 0.035)
        vignetteTotal = f.double("vignette.total", 0.33)
        rippleTimes = f.doubles("ripple.times", [0, 0.05, 0.1, 0.15, 0.2, 0.233])
        rippleRadius = f.doubles("ripple.radiusPt", [11, 14.5, 18, 20.5, 22, 22.5])
        rippleCoreLum = f.doubles("ripple.coreLum", [180, 199, 220, 237, 248, 250])
        rippleRingLum = f.doubles("ripple.ringLum", [232, 233, 236, 243, 248, 250])
        rippleCoreRadius = f.double("ripple.coreRadiusPt", 8)
        rippleCoreFirstRadius = f.double("ripple.coreFirstRadiusPt", 9.5)
        rippleEdgeSoft = f.double("ripple.edgeSoftPt", 3)
        ripplePool = max(1, t.ripplePool)
        introZoomFrom = f.double("intro.zoomFrom", 1.49)
        introZoomDuration = f.double("intro.zoomDuration", 1.35)
        introDrawBase = f.double("intro.drawBase", 0.32)
        introDrawPerCell = f.double("intro.drawPerCell", 0.0216)
        stageGap = t.stageGap
        warmupSpeed = t.warmupSpeed
        spriteCacheCapMB = t.spriteCacheCapMB
        hitchMs = t.hitchMs
        probeHz = f.double("probe.hz", 4)
    }

    /// The play rect (between the HUD and the booster bar) on a screen of this size.
    func playRect(in size: CGSize) -> CGRect {
        let h = max(1, size.height - playTop - playBottomGap)
        return CGRect(x: 0, y: playTop, width: size.width, height: h)
    }

    /// The fit layout of a level on a screen of this size (PathCore's §4.2 rule, C1's `BoardLayout.fit`).
    func layout(for level: LevelSpec, screen: CGSize) -> BoardLayout {
        BoardLayout.fit(grid: level.grid, play: playRect(in: screen), maxPitch: zoomMaxPitch)
    }

    /// C1's `ArrowMetrics` with the board's look overrides (the measured visible head tips, the fillet): what PathCore's
    /// HitGeometry uses for the head-apex segment.
    var arrowMetrics: ArrowMetrics {
        var m = ArrowMetrics.default
        if let h = head {
            m.apexRight = h[.right]?.tip ?? m.apexRight
            m.apexLeft = h[.left]?.tip ?? m.apexLeft
            m.apexUp = h[.up]?.tip ?? m.apexUp
            m.apexDown = h[.down]?.tip ?? m.apexDown
            m.headBase = h[.right]?.width ?? m.headBase
        }
        m.cornerFillet = cornerFillet
        return m
    }

    /// Zoom limits relative to fit for a layout.
    func zoomLimits(_ layout: BoardLayout) -> (min: CGFloat, max: CGFloat) {
        let p = layout.pitch
        let maxZ = max(1, zoomMaxPitch / p)
        let minZ: Double = zoomMinPitch > 0 ? min(1, zoomMinPitch / p) : zoomMinOfFit
        return (CGFloat(minZ), CGFloat(maxZ))
    }

    /// `#RRGGBB` → sRGB CGColor (black on a malformed value, logged).
    static func color(_ hex: String) -> CGColor {
        var s = hex.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6, let v = UInt32(s, radix: 16) else {
            Log.error("board", "bad colour \(hex) in board.json: black")
            return UIColor.black.cgColor
        }
        let r = CGFloat((v >> 16) & 0xFF) / 255
        let g = CGFloat((v >> 8) & 0xFF) / 255
        let b = CGFloat(v & 0xFF) / 255
        return UIColor(red: r, green: g, blue: b, alpha: 1).cgColor
    }

    /// A grey of luminance `lum` (0…255) on white expressed as black at an alpha: 255 − 255·α = lum.
    static func alphaForLuminance(_ lum: Double) -> Double { max(0, min(1, (255 - lum) / 255)) }
}

/// A head measured as it LOOKS: `tip` is where the rounded apex ends, so the sharp apex the path is built on lies
/// r·(1/sin θ − 1) further out (θ = the half-angle at the apex).
struct HeadSpec: Equatable {
    var base: Double
    var tip: Double
    var width: Double
    var corner: Double

    /// The sharp apex (× pitch) whose rounding ends at `tip`.
    var sharpApex: Double {
        var a = tip
        for _ in 0..<8 {
            let theta = atan((width / 2) / max(a - base, 0.01))
            a = tip + corner * (1 / max(sin(theta), 0.05) - 1)
        }
        return a
    }
}

extension StageSetup {
    /// The stage a caller (GAME, BoardLab) builds for a level on this screen with the board's own play rect and caps.
    @MainActor init(level: LevelSpec, stage: Int = 0, stages: Int = 1, seed: UInt64 = 0, screen: CGSize, config: BoardConfig) {
        self.init(level: level, layout: config.layout(for: level, screen: screen), stage: stage, stages: stages, seed: seed)
    }
}
