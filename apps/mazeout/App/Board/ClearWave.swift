import UIKit
import PathCore

// B2 (SPEC-architecture §5.7 "Board-clear wave"; SPEC-motion-audio §3.8; anchor W = the last arrow's tail left its last
// cell). The vacated dots flash colour in a ring expanding from the board centre: warm (#FF6500) at the centre, through
// green / cyan / blue / violet to pink (#FF2FC6, palette index 10) at the farthest dot — colour by RADIUS; the front
// r(t) = r_max · t / 0.45; each dot's colour weight after the front passes: kf[0: 0, 0.05: 1, 0.15: 1, 0.40: 0] over #C5E1FF.
// Implementation (arch §5.7 adapted by MA §3.8): ONE container masked by ONE shape layer holding every dot (built at the
// clear, ≤ 1 ms) → a static radial rainbow gradient (the palette by radius) → masked by a radial ALPHA gradient (the
// envelope as a ring) whose `locations` move outward (60 Hz keyframes, linear: exact between samples). The gradients
// are square about the grid centre, 1.9 × r_max in radius so the whole envelope stays inside their unit radius.
// `.clearWaveFinished` at W + 0.50 (NOT a gate: the celebration runs on its own W clock, MA §5); the layers go at W + 0.87.

extension BoardEngine {
    /// Plays the wave over the active stage's dots from stage-local `w` (now when nil); returns the wave's end beat time.
    @discardableResult
    func runClearWave(begin w: CFTimeInterval? = nil, report: Bool = true) -> Double {
        guard let st = stage, let dotsPath = dots.layer.path else {
            if report { DispatchQueue.main.async { [weak self] in self?.delegate?.boardBeat(.clearWaveFinished) } }
            return 0
        }
        let set = roots
        let t0 = w ?? Anim.now(set.dots)
        let geo = st.geo
        let p = geo.pitch
        // the grid centre and the farthest dot
        let c0 = geo.centre(Cell(0, 0)), c1 = geo.centre(Cell(st.level.cols - 1, st.level.rows - 1))
        let centre = CGPoint(x: (c0.x + c1.x) / 2, y: (c0.y + c1.y) / 2)
        let box = dotsPath.boundingBoxOfPath
        let corners = [CGPoint(x: box.minX, y: box.minY), CGPoint(x: box.maxX, y: box.minY),
                       CGPoint(x: box.minX, y: box.maxY), CGPoint(x: box.maxX, y: box.maxY)]
        let rMax = max(p, corners.map { hypot($0.x - centre.x, $0.y - centre.y) }.max() ?? p)
        let front = fx.waveFront
        let env = fx.waveEnvelope
        let envTimes = stride(from: 0, to: env.count - 1, by: 2).map { env[$0] }
        let envW = stride(from: 1, to: env.count, by: 2).map { env[$0] }
        let envEnd = envTimes.last ?? 0.4
        let R = rMax * CGFloat(1 + envEnd / front) * 1.02          // the envelope stays inside the unit radius
        let square = CGRect(x: centre.x - R, y: centre.y - R, width: 2 * R, height: 2 * R)
        let scale = screenScale

        let container = CALayer()
        container.frame = set.dots.bounds
        let mask = CAShapeLayer()
        mask.frame = container.bounds
        mask.path = dotsPath
        mask.fillColor = UIColor.black.cgColor
        container.mask = mask

        let rainbow = CAGradientLayer()
        rainbow.type = .radial
        rainbow.frame = square
        rainbow.startPoint = CGPoint(x: 0.5, y: 0.5)
        rainbow.endPoint = CGPoint(x: 1, y: 1)
        let pal = fx.rainbowPalette
        var cols: [CGColor] = []
        var locs: [NSNumber] = []
        let span = Double(rMax / R)
        for i in 0...10 {
            cols.append(pal[min(i, pal.count - 1)])
            locs.append(NSNumber(value: span * Double(i) / 10))
        }
        cols.append(pal[min(10, pal.count - 1)]); locs.append(1)
        rainbow.colors = cols
        rainbow.locations = locs
        rainbow.contentsScale = scale

        let ring = CAGradientLayer()
        ring.type = .radial
        ring.frame = CGRect(origin: .zero, size: square.size)
        ring.startPoint = CGPoint(x: 0.5, y: 0.5)
        ring.endPoint = CGPoint(x: 1, y: 1)
        let clear = UIColor.white.withAlphaComponent(0).cgColor
        // stops (behind the front, in gradient-radius units): age a ↔ ρ = ρ_f − a / front · r_max / R
        let k = Double(rMax / R) / front
        ring.colors = [clear] + envW.map { UIColor.white.withAlphaComponent(CGFloat($0)).cgColor }.reversed() + [clear]
        var times: [Double] = []
        var values: [[NSNumber]] = []
        let total = front * Double(R / rMax) * 0.999
        var t = 0.0
        while t <= total + 1e-9 {
            let rhoF = t / front * Double(rMax / R)          // the front in gradient units
            var row: [Double] = [0]
            for a in envTimes.reversed() { row.append(rhoF - a * k) }
            row.append(1)
            // clamp into [0, 1] keeping the order
            var prev = 0.0
            let fixed = row.map { v -> Double in let c = min(1, max(prev, v)); prev = c; return c }
            values.append(fixed.map { NSNumber(value: $0) })
            times.append(t)
            t += 1.0 / 60
        }
        ring.locations = values.last
        let la = Anim.keyframes("locations", values, times: times, duration: times.last ?? 0.5, begin: t0)
        la.fillMode = .both
        ring.add(la, forKey: "front")
        rainbow.mask = ring
        container.addSublayer(rainbow)
        set.dots.addSublayer(container)
        let life = front + envEnd + 0.03
        Anim.beat(on: container, key: "waveEnd", begin: t0, delay: life) { [weak container] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            container?.removeFromSuperlayer()
            CATransaction.commit()
        }
        if report {
            Anim.beat(on: set.dots, key: "waveDone", begin: t0, delay: fx.waveTotal) { [weak self] finished in
                guard let self else { return }
                if finished { self.noteFirst("clearWave") }
                self.delegate?.boardBeat(.clearWaveFinished)
            }
        }
        return fx.waveTotal
    }
}
