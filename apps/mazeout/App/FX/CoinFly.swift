import UIKit
import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §3.2 "FX/CoinFly", §6.4 item 7, D13; SPEC-motion-audio §8.3 segment C, §8.4; SPEC-ui §2.2.7 step 4;
// CONSISTENCY W-20: timing = MA, look and position = UI). The coin payout as Core Animation layers on the FX host (render
// server; the main thread only schedules): the "+N" label (≈ 36 pt white, outline #6B3A1E 2 pt) centred ≈ (229, 484) with a
// small coin pile at the flight origin pops (0.3 → 1.1 → 1.0, easeOutBack, 0.25 s); five coins (`iconCoin` 34 pt) lift from
// (196, 490) at C0 + 0.55 + 0.085·k and fly 0.22 s each on a quadratic Bézier (control (196, 180)) to the coin pill's icon
// (112.7, 70), easeInQuad, scale 1 → 0.85; the label + pile fade at C0 + 1.12 (0.20 s). Every number is `ui.json
// homeReturn.coins.*` (MA §13.2). Also reached as `FXEffect.coinFly` (the contract's form: amount, coins, from, to).

struct CoinFlySpec {
    var labelAt = 0.0, labelDur = 0.25, cueLead = 1.12, liftAt = 0.55, stagger = 0.085, flight = 0.22
    var count = 5
    var origin = CGPoint(x: 196, y: 490), control = CGPoint(x: 196, y: 180), target = CGPoint(x: 112.7, y: 70)
    var endScale: CGFloat = 0.85, labelFadeAt = 1.12, labelFadeDur = 0.20
    var labelCentre = CGPoint(x: 229, y: 484), labelSize: CGFloat = 36, coinSize: CGFloat = 34, pileWidth: CGFloat = 46

    init() {}

    init(_ t: Tokens) {
        let f = t.file, k = "homeReturn.coins."
        labelAt = f.double(k + "labelAt", labelAt); labelDur = f.double(k + "labelDur", labelDur)
        cueLead = f.double(k + "cueLead", cueLead); liftAt = f.double(k + "liftAt", liftAt)
        stagger = f.double(k + "stagger", stagger); flight = f.double(k + "flight", flight)
        count = max(1, f.int(k + "count", count))
        func pt(_ key: String, _ d: CGPoint) -> CGPoint {
            let v = f.doubles(k + key, [])
            return v.count == 2 ? CGPoint(x: v[0], y: v[1]) : d
        }
        origin = pt("origin", origin); control = pt("control", control); target = pt("target", target)
        endScale = CGFloat(f.double(k + "endScale", Double(endScale))); labelFadeAt = f.double(k + "labelFadeAt", labelFadeAt)
        labelCentre = pt("labelCentre", labelCentre); labelSize = CGFloat(f.double(k + "labelSize", Double(labelSize)))
        coinSize = CGFloat(f.double(k + "coinSize", Double(coinSize)))
    }

    /// The landing of coin k, from C0 (MA C4: 0.77 + 0.085·k).
    func landing(_ k: Int) -> Double { liftAt + stagger * Double(k) + flight }

    /// How much each landing adds: N/count, the remainder on the last coin (VERIFIED 1000 → 1024 … 1120).
    func shares(_ amount: Int) -> [Int] {
        let base = amount / count
        return (0..<count).map { $0 == count - 1 ? amount - base * (count - 1) : base }
    }
}

@MainActor enum CoinFly {
    /// Builds the segment-C layers in the FX host's time base (`t0` = the host layer's local time at C0). Points are screen pt.
    static func layers(amount: Int, spec: CoinFlySpec, from: CGPoint, to: CGPoint, control: CGPoint, labelCentre: CGPoint,
                       scale s: CGFloat, t0: CFTimeInterval, showLabel: Bool = true) -> [CALayer] {
        var out: [CALayer] = []
        if showLabel {
            // the small pile at the flight origin + the "+N" label, popping together (C1), fading at C5
            let pile = CALayer()
            if let img = ArtStore.image(.coinPileSmall)?.cgImage { pile.contents = img }
            let pw = spec.pileWidth * s, ph = pw * 56 / 68
            pile.bounds = CGRect(x: 0, y: 0, width: pw, height: ph)
            pile.position = CGPoint(x: from.x, y: from.y + 4 * s)
            pile.contentsGravity = .resizeAspect
            out.append(popAndFade(pile, spec: spec, t0: t0))
            if let label = labelImage("+\(amount)", size: spec.labelSize * s) {
                let l = CALayer()
                l.contents = label.image
                l.contentsScale = label.scale
                l.bounds = CGRect(origin: .zero, size: label.size)
                l.position = labelCentre
                out.append(popAndFade(l, spec: spec, t0: t0))
            }
        }
        let coinImage = ArtStore.image(.iconCoin)?.cgImage
        for k in 0..<spec.count {
            let coin = CALayer()
            coin.contents = coinImage
            coin.contentsGravity = .resizeAspect
            let d = spec.coinSize * s
            coin.bounds = CGRect(x: 0, y: 0, width: d, height: d)
            coin.position = to
            coin.opacity = 0
            let path = UIBezierPath()
            path.move(to: from)
            path.addQuadCurve(to: to, controlPoint: control)
            let move = CAKeyframeAnimation(keyPath: "position")
            move.path = path.cgPath
            move.calculationMode = .paced
            let sc = CABasicAnimation(keyPath: "transform.scale")
            sc.fromValue = 1; sc.toValue = spec.endScale
            let op = CAKeyframeAnimation(keyPath: "opacity")
            op.values = [1, 1]; op.keyTimes = [0, 1]
            let g = CAAnimationGroup()
            g.animations = [move, sc, op]
            g.duration = spec.flight
            g.timingFunction = CAMediaTimingFunction(controlPoints: 0.11, 0, 0.5, 0)         // easeInQuad
            g.beginTime = t0 + spec.liftAt + spec.stagger * Double(k)
            g.fillMode = .removed
            g.isRemovedOnCompletion = true
            coin.add(g, forKey: "fly")
            out.append(coin)
        }
        return out
    }

    /// C1 pop (0.3 → 1.1 → 1.0 over labelDur, easeOutBack) + C5 fade (labelFadeAt, 0.20 s).
    private static func popAndFade(_ l: CALayer, spec: CoinFlySpec, t0: CFTimeInterval) -> CALayer {
        l.opacity = 0
        let pop = CAKeyframeAnimation(keyPath: "transform.scale")
        pop.values = [0.3, 1.1, 1.0]
        pop.keyTimes = [0, 0.6, 1]
        pop.timingFunctions = [CAMediaTimingFunction(controlPoints: 0.34, 1.56, 0.64, 1), CAMediaTimingFunction(name: .easeInEaseOut)]
        pop.duration = spec.labelDur
        pop.beginTime = t0 + spec.labelAt
        pop.fillMode = .backwards
        let op = CAKeyframeAnimation(keyPath: "opacity")
        op.values = [1, 1, 0]
        let total = spec.labelFadeAt + spec.labelFadeDur - spec.labelAt
        op.keyTimes = [0, NSNumber(value: (spec.labelFadeAt - spec.labelAt) / total), 1]
        op.duration = total
        op.beginTime = t0 + spec.labelAt
        op.fillMode = .removed
        l.add(pop, forKey: "pop")
        l.add(op, forKey: "life")
        return l
    }

    struct LabelImage { let image: CGImage; let size: CGSize; let scale: CGFloat }

    /// "+N" as a raster of GameText (white face, outline #6B3A1E 2 pt, a small drop), rendered once per text.
    static func labelImage(_ text: String, size: CGFloat) -> LabelImage? {
        let st = GameTextStyle.s2(size, -0.8, [Skin.fxCoinFlyCoinFlyLabelImageSt0], outline: Skin.fxCoinFlyCoinFlyLabelImageStOutline, 2.0 * size / 36, drop: 1.6 * size / 36)
        let w = size * 0.62 * CGFloat(text.count) + 16, h = size * 1.35
        let scale = UIScreen.main.scale
        guard let img = RasterCache.image("payoutLabel|\(text)|\(size)", size: CGSize(width: w, height: h), scale: scale, content: {
            GameText(verbatim: text, style: st).frame(width: w, height: h)
        }) else { return nil }
        return LabelImage(image: img, size: CGSize(width: w, height: h), scale: scale)
    }
}
