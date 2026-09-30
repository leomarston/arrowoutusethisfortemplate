import UIKit
import QuartzCore
import PathCore
import SortPuzzle

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §6b): SortPuzzle's board — plain UIKit + Core Animation, no art
// files. Tubes are open-topped shape layers, units rounded squares; every colour is a skin token (skin/colors.json
// `puzzle.sortBoard.*`, tools/skin/build.py), every size and duration a sort.json `board.*` number.
//  - input: a released touch is hit-tested to a tube and sent as `.select(tube)` inside the touch handler (the session answers
//    synchronously and `present` animates the answer in the same run-loop turn); a release on nothing drops a lifted tube;
//  - beats: the board keeps its own clock (its display link while on screen, `advance(_:)` in headless tests) and acks
//    `.introFinished` after the build-in, `.boardCleared` when the stage's last pour has landed (W), `.stageTransitionDone`
//    after the swap to the next board — never synchronously inside the call that caused them;
//  - the board mirrors the session's tubes from the events (`poured`, `undone`, `tubesAdded`); `resync()` rebuilds from the
//    session if they ever disagree;
//  - the display link is also the Play's master clock (`boardFrame`) while the board is in a window.

/// sort.json `board.*` (the fallbacks are the shipped values).
struct SortBoardTuning {
    let file: TuningFile

    private func pt(_ key: String, _ fallback: Double) -> CGFloat { CGFloat(file.double("board." + key, fallback)) }
    private func sec(_ key: String, _ fallback: Double) -> Double { max(0, file.double("board." + key, fallback)) }

    // layout (pt at scale 1; the whole grid scales down to fit between the insets)
    var insetTop: CGFloat { pt("insetTop", 190) }
    var insetBottom: CGFloat { pt("insetBottom", 190) }
    var insetSide: CGFloat { pt("insetSide", 24) }
    var perRowMax: Int { max(1, file.int("board.perRowMax", 6)) }
    var tubeWidth: CGFloat { pt("tubeWidth", 54) }
    var tubeGapMin: CGFloat { pt("tubeGapMin", 10) }
    var rowGap: CGFloat { pt("rowGap", 36) }
    var unitSize: CGFloat { pt("unitSize", 42) }
    var unitGap: CGFloat { pt("unitGap", 4) }
    var tubePadding: CGFloat { pt("tubePadding", 6) }
    var tubeCorner: CGFloat { pt("tubeCorner", 20) }
    var tubeLineWidth: CGFloat { pt("tubeLineWidth", 3) }
    var unitCorner: CGFloat { pt("unitCorner", 21) }
    var unitEdgeWidth: CGFloat { pt("unitEdgeWidth", 1.5) }
    var liftHeight: CGFloat { pt("liftHeight", 26) }
    var pourArc: CGFloat { pt("pourArc", 36) }
    var hitSlop: CGFloat { pt("hitSlop", 12) }
    var introRise: CGFloat { pt("introRise", 40) }
    var refuseShake: CGFloat { pt("refuseShake", 9) }
    var completeScale: Double { file.double("board.completeScale", 1.08) }
    // motion (s)
    var introSeconds: Double { sec("introSeconds", 0.45) }
    var pourSeconds: Double { sec("pourSeconds", 0.28) }
    var liftSeconds: Double { sec("liftSeconds", 0.12) }
    var refuseSeconds: Double { sec("refuseSeconds", 0.24) }
    var refuseFlashSeconds: Double { sec("refuseFlashSeconds", 0.3) }
    var completeSeconds: Double { sec("completeSeconds", 0.3) }
    var clearSeconds: Double { sec("clearSeconds", 0.4) }
    var clearStagger: Double { sec("clearStagger", 0.05) }
    var transitionSeconds: Double { sec("transitionSeconds", 0.5) }
    var tubeAddSeconds: Double { sec("tubeAddSeconds", 0.3) }
    var layoutSeconds: Double { sec("layoutSeconds", 0.25) }
}

/// Where the tubes go: rows of at most `perRowMax`, centred between the insets, scaled down (never up) to fit.
struct SortBoardLayout: Equatable {
    var tubes: [CGRect]
    var scale: CGFloat

    static func make(count: Int, capacity: Int, size: CGSize, tuning t: SortBoardTuning) -> SortBoardLayout {
        guard count > 0, size.width > 0, size.height > 0 else { return SortBoardLayout(tubes: [], scale: 1) }
        let rows = (count + t.perRowMax - 1) / t.perRowMax
        let perRow = (count + rows - 1) / rows
        let cap = CGFloat(max(1, capacity))
        let tubeH = t.tubePadding * 2 + cap * t.unitSize + (cap - 1) * t.unitGap
        let slotH = tubeH + t.liftHeight                                   // room above each tube for a lifted run
        let avail = CGRect(x: t.insetSide, y: t.insetTop, width: max(1, size.width - 2 * t.insetSide),
                           height: max(1, size.height - t.insetTop - t.insetBottom))
        let gridW = CGFloat(perRow) * t.tubeWidth + CGFloat(perRow - 1) * t.tubeGapMin
        let gridH = CGFloat(rows) * slotH + CGFloat(rows - 1) * t.rowGap
        let scale = min(1, avail.width / gridW, avail.height / gridH)
        let cellW = avail.width / CGFloat(perRow)
        let rowH = slotH * scale
        let totalH = CGFloat(rows) * rowH + CGFloat(rows - 1) * t.rowGap * scale
        var y = avail.midY - totalH / 2
        var out: [CGRect] = []
        var left = count
        for _ in 0..<rows {
            let n = min(perRow, left)
            let x0 = avail.minX + CGFloat(perRow - n) * cellW / 2
            for i in 0..<n {
                let cx = x0 + (CGFloat(i) + 0.5) * cellW
                out.append(CGRect(x: cx - t.tubeWidth * scale / 2, y: y + t.liftHeight * scale, width: t.tubeWidth * scale,
                                  height: tubeH * scale))
            }
            left -= n
            y += rowH + t.rowGap * scale
        }
        return SortBoardLayout(tubes: out, scale: scale)
    }
}

/// The board's view: touches end here (the release handler), size and window changes go to the board.
final class SortBoardView: UIView {
    weak var board: SortPuzzleBoard?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isMultipleTouchEnabled = false
        backgroundColor = UIColor(rgb: Skin.puzzleSortBoardBackground)
        accessibilityIdentifier = "sort.board"
    }

    required init?(coder: NSCoder) { nil }

    override func layoutSubviews() {
        super.layoutSubviews()
        board?.viewResized()
    }

    override func didMoveToWindow() {
        super.didMoveToWindow()
        board?.windowChanged()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        super.touchesEnded(touches, with: event)
        guard let t = touches.first else { return }
        board?.handleRelease(at: t.location(in: self), touchTimestamp: t.timestamp)
    }
}

@MainActor final class SortPuzzleBoard: NSObject, PuzzleBoard {
    let tuning: SortBoardTuning
    let boardView: SortBoardView

    /// Cleared when a Play lets go of the board: its pending beats go with it.
    weak var delegate: PuzzleBoardDelegate? {
        didSet { if delegate == nil { pending.removeAll() } }
    }
    var view: UIView { boardView }
    var inputEnabled = false
    var allowedTargets: Set<PuzzleTarget>?

    /// The unit colours by colour index (the skin's tokens; a level uses the first `colors`).
    static let unitColors: [UInt32] = [
        Skin.puzzleSortBoardUnit0, Skin.puzzleSortBoardUnit1, Skin.puzzleSortBoardUnit2, Skin.puzzleSortBoardUnit3,
        Skin.puzzleSortBoardUnit4, Skin.puzzleSortBoardUnit5, Skin.puzzleSortBoardUnit6, Skin.puzzleSortBoardUnit7,
        Skin.puzzleSortBoardUnit8, Skin.puzzleSortBoardUnit9,
    ]

    // layers
    private let root = CALayer()
    private let tubesLayer = CALayer()
    private let unitsLayer = CALayer()
    private var glass: [CAShapeLayer] = []
    private var units: [[CALayer]] = []

    // the mirror of the session's board
    private(set) var tubes: [[Int]] = []
    private(set) var capacity = 0
    private(set) var lifted: (tube: Int, count: Int)?
    private(set) var layout = SortBoardLayout(tubes: [], scale: 1)
    private var laidOutSize: CGSize = .zero
    private(set) var stageInfo: StageContext?

    // the board's clock and its pending beats
    private(set) var clock: Double = 0
    private var pending: [(at: Double, run: () -> Void)] = []
    private var link: CADisplayLink?
    private var lastTimestamp: CFTimeInterval = 0

    init(tuning: SortBoardTuning) {
        self.tuning = tuning
        boardView = SortBoardView(frame: .zero)
        super.init()
        boardView.board = self
        root.addSublayer(tubesLayer)
        root.addSublayer(unitsLayer)
        boardView.layer.addSublayer(root)
    }

    // MARK: PuzzleBoard

    func prepare() async {}

    func load(_ stage: StageContext) {
        guard let level = stage.info.content as? SortLevel else {
            Log.error("board", "stage \(stage.stage + 1) of L\(stage.info.level) carries no SortLevel: not loaded")
            return
        }
        if boardView.bounds.size == .zero { boardView.frame = CGRect(origin: .zero, size: stage.screen) }
        pending.removeAll()
        stageInfo = stage
        rebuild(level)
        root.opacity = 0                                                   // hidden until the intro
    }

    func playIntro(_ style: IntroStyle) {
        let d: Double
        switch style {
        case .none: d = 0
        case .growFromTails, .growFromTailsNoHUD: d = tuning.introSeconds
        }
        root.opacity = 1
        if d > 0 {
            let fade = CABasicAnimation(keyPath: "opacity")
            fade.fromValue = 0
            fade.toValue = 1
            let rise = CABasicAnimation(keyPath: "transform.translation.y")
            rise.fromValue = tuning.introRise
            rise.toValue = 0
            let g = CAAnimationGroup()
            g.animations = [fade, rise]
            g.duration = d
            g.timingFunction = CAMediaTimingFunction(name: .easeOut)
            root.add(g, forKey: "intro")
        }
        schedule(after: d) { [weak self] in self?.delegate?.boardAck(.introFinished) }
    }

    func present(_ outputs: [SessionOutput]) {
        var busy = 0.0
        for e in SessionOutput.sortEvents(outputs) {
            switch e {
            case .selected(let t, let count):
                lift(t, count: count)
            case .deselected(let t):
                drop(t)
            case .poured(let from, let to, let count, _), .undone(let from, let to, let count):
                transfer(from: from, to: to, count: count)
                busy = max(busy, tuning.pourSeconds)
            case .refused(let from, let to):
                drop(from)
                refuse(to)
            case .ignored:
                break
            case .tubeCompleted(let t, _):
                complete(t, after: tuning.pourSeconds)
            case .tubesAdded(let count, _):
                addTubes(count)
                busy = max(busy, tuning.tubeAddSeconds)
            }
        }
        let stageEnds = outputs.contains { o in
            switch o {
            case .meta(.won), .meta(.stageCleared): return true
            default: return false
            }
        }
        if stageEnds {
            // W: the last pour has landed and the tube's completion pulse played
            schedule(after: busy + tuning.completeSeconds) { [weak self] in self?.delegate?.boardAck(.boardCleared) }
        }
    }

    func playStageTransition(to next: StageContext) {
        guard let level = next.info.content as? SortLevel else {
            Log.error("board", "stage \(next.stage + 1) of L\(next.info.level) carries no SortLevel: no transition")
            return
        }
        let half = tuning.transitionSeconds / 2
        fade(to: 0, duration: half)
        schedule(after: half) { [weak self] in
            guard let self else { return }
            self.stageInfo = next
            self.rebuild(level)
            self.fade(to: 1, duration: half)
            self.schedule(after: half) { [weak self] in self?.delegate?.boardAck(.stageTransitionDone) }
        }
    }

    func playClearWave() {
        for i in glass.indices {
            complete(i, after: Double(i) * tuning.clearStagger, duration: tuning.clearSeconds)
        }
    }

    /// The tube's middle (`at`: an offset in unit sizes, [dx, dy]).
    func handPoint(for target: PuzzleTarget, at: [Double]?) -> CGPoint? {
        guard layout.tubes.indices.contains(target.raw) else { return nil }
        let f = layout.tubes[target.raw]
        let unit = tuning.unitSize * layout.scale
        guard let at, at.count == 2 else { return CGPoint(x: f.midX, y: f.midY) }
        return CGPoint(x: f.midX + CGFloat(at[0]) * unit, y: f.midY + CGFloat(at[1]) * unit)
    }

    /// A release at the tube's middle through the real handler; false while input is closed (the caller then feeds the
    /// session itself).
    func performTap(on target: PuzzleTarget) -> Bool {
        guard inputEnabled, layout.tubes.indices.contains(target.raw) else { return false }
        let f = layout.tubes[target.raw]
        handleRelease(at: CGPoint(x: f.midX, y: f.midY), touchTimestamp: CACurrentMediaTime())
        return true
    }

    /// The board's half of a probe: the level, the tubes and the lifted tube, as JSON in the view's accessibility value.
    func publishProbe() {
        var obj: [String: Any] = ["tubes": tubes, "capacity": capacity]
        if let s = stageInfo { obj["lvl"] = s.info.level; obj["stage"] = s.stage; obj["stages"] = s.stages }
        if let l = lifted { obj["lifted"] = l.tube }
        guard let data = try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys]) else { return }
        boardView.accessibilityValue = String(decoding: data, as: UTF8.self)
    }

    var diagnostics: BoardDiagnostics? { nil }

    // MARK: input (the release handler)

    /// The tube under `p`: the nearest tube whose frame (+ the lift room above it, + the slop) holds the point.
    func tube(at p: CGPoint) -> Int? {
        let slop = tuning.hitSlop
        let lift = tuning.liftHeight * layout.scale
        var best: (i: Int, d: CGFloat)?
        for (i, f) in layout.tubes.enumerated() {
            let area = CGRect(x: f.minX - slop, y: f.minY - lift - slop, width: f.width + 2 * slop,
                              height: f.height + lift + 2 * slop)
            guard area.contains(p) else { continue }
            let d = hypot(p.x - f.midX, p.y - f.midY)
            if best == nil || d < best!.d { best = (i, d) }
        }
        return best?.i
    }

    func handleRelease(at p: CGPoint, touchTimestamp: TimeInterval) {
        guard inputEnabled, let d = delegate else { return }
        guard let t = tube(at: p) else {
            // a release on nothing drops the lifted tube (the same pick again)
            if let l = lifted { d.boardInput(.select(PuzzleTarget(l.tube)), touchTimestamp: touchTimestamp) }
            return
        }
        if let allowed = allowedTargets, !allowed.contains(PuzzleTarget(t)) { return }
        d.boardInput(.select(PuzzleTarget(t)), touchTimestamp: touchTimestamp)
    }

    // MARK: the clock

    /// Advances the board's clock by `seconds` and runs every beat that falls due, in time order (the display link calls it
    /// every frame; headless tests call it directly).
    func advance(_ seconds: Double) {
        let until = clock + max(0, seconds)
        while let i = pending.indices.min(by: { pending[$0].at < pending[$1].at }), pending[i].at <= until + 1e-9 {
            let item = pending.remove(at: i)
            clock = max(clock, item.at)
            item.run()
        }
        clock = until
    }

    /// Beats pending (tests).
    var pendingBeats: Int { pending.count }

    private func schedule(after seconds: Double, _ run: @escaping () -> Void) {
        pending.append((clock + max(0, seconds), run))
    }

    func windowChanged() {
        if boardView.window != nil {
            guard link == nil else { return }
            let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
            l.add(to: .main, forMode: .common)
            link = l
            lastTimestamp = 0
        } else {
            link?.invalidate()
            link = nil
        }
    }

    @objc private func tick(_ l: CADisplayLink) {
        let ts = l.timestamp
        if lastTimestamp > 0 { advance(ts - lastTimestamp) }
        lastTimestamp = ts
        delegate?.boardFrame(timestamp: ts, targetTimestamp: l.targetTimestamp)
    }

    func viewResized() {
        guard boardView.bounds.size != laidOutSize, !glass.isEmpty else { return }
        layoutAll(duration: 0)
    }

    // MARK: building

    private var boardSize: CGSize {
        boardView.bounds.size == .zero ? (stageInfo?.screen ?? .zero) : boardView.bounds.size
    }

    private func rebuild(_ level: SortLevel) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        for g in glass { g.removeFromSuperlayer() }
        for u in units.joined() { u.removeFromSuperlayer() }
        capacity = level.capacity
        tubes = level.tubes
        lifted = nil
        glass = level.tubes.map { _ in makeGlass() }
        for g in glass { tubesLayer.addSublayer(g) }
        units = level.tubes.map { t in t.map { makeUnit($0) } }
        for u in units.joined() { unitsLayer.addSublayer(u) }
        CATransaction.commit()
        layoutAll(duration: 0)
    }

    /// Rebuilds the units from the session's tubes (the mirror disagreed with an event).
    private func resync() {
        guard let s = delegate?.activeSession as? SortPuzzleSession else { return }
        Log.error("board", "the sort board's tubes disagreed with the session's: rebuilt")
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        for u in units.joined() { u.removeFromSuperlayer() }
        while glass.count < s.tubes.count {
            let g = makeGlass()
            tubesLayer.addSublayer(g)
            glass.append(g)
        }
        tubes = s.tubes
        capacity = s.capacity
        lifted = nil
        units = s.tubes.map { t in t.map { makeUnit($0) } }
        for u in units.joined() { unitsLayer.addSublayer(u) }
        CATransaction.commit()
        layoutAll(duration: 0)
    }

    private func makeGlass() -> CAShapeLayer {
        let g = CAShapeLayer()
        g.fillColor = UIColor(rgb: Skin.puzzleSortBoardTubeFill).cgColor
        g.strokeColor = UIColor(rgb: Skin.puzzleSortBoardTubeStroke).cgColor
        g.lineCap = .round
        g.lineJoin = .round
        return g
    }

    private func makeUnit(_ colour: Int) -> CALayer {
        let u = CALayer()
        let palette = Self.unitColors
        u.backgroundColor = UIColor(rgb: palette[((colour % palette.count) + palette.count) % palette.count]).cgColor
        u.borderColor = UIColor(rgb: Skin.puzzleSortBoardUnitEdge).cgColor
        return u
    }

    /// An open-topped tube with rounded bottom corners, in its own bounds.
    private func glassPath(_ size: CGSize) -> CGPath {
        let r = min(tuning.tubeCorner * layout.scale, size.width / 2, size.height / 2)
        let p = UIBezierPath()
        p.move(to: .zero)
        p.addLine(to: CGPoint(x: 0, y: size.height - r))
        p.addArc(withCenter: CGPoint(x: r, y: size.height - r), radius: r, startAngle: .pi, endAngle: .pi / 2, clockwise: false)
        p.addLine(to: CGPoint(x: size.width - r, y: size.height))
        p.addArc(withCenter: CGPoint(x: size.width - r, y: size.height - r), radius: r, startAngle: .pi / 2, endAngle: 0,
                 clockwise: false)
        p.addLine(to: CGPoint(x: size.width, y: 0))
        return p.cgPath
    }

    private func layoutAll(duration: Double) {
        let size = boardSize
        laidOutSize = boardView.bounds.size
        layout = SortBoardLayout.make(count: glass.count, capacity: capacity, size: size, tuning: tuning)
        CATransaction.begin()
        CATransaction.setDisableActions(duration <= 0)
        CATransaction.setAnimationDuration(duration)
        root.frame = CGRect(origin: .zero, size: size)
        tubesLayer.frame = root.bounds
        unitsLayer.frame = root.bounds
        let side = tuning.unitSize * layout.scale
        for (i, g) in glass.enumerated() where layout.tubes.indices.contains(i) {
            let f = layout.tubes[i]
            g.frame = f
            g.path = glassPath(f.size)
            g.lineWidth = tuning.tubeLineWidth * layout.scale
        }
        for (i, column) in units.enumerated() {
            for (j, u) in column.enumerated() {
                u.bounds = CGRect(x: 0, y: 0, width: side, height: side)
                u.cornerRadius = tuning.unitCorner * layout.scale
                u.borderWidth = tuning.unitEdgeWidth * layout.scale
                u.position = center(tube: i, slot: j, lifted: isLifted(tube: i, slot: j))
            }
        }
        CATransaction.commit()
    }

    private func isLifted(tube: Int, slot: Int) -> Bool {
        guard let l = lifted, l.tube == tube else { return false }
        return slot >= (units.indices.contains(tube) ? units[tube].count : 0) - l.count
    }

    /// A unit's centre: slot 0 at the bottom; a lifted run rises by `liftHeight`.
    private func center(tube: Int, slot: Int, lifted up: Bool) -> CGPoint {
        guard layout.tubes.indices.contains(tube) else { return .zero }
        let f = layout.tubes[tube]
        let s = layout.scale
        let side = tuning.unitSize * s
        let y = f.maxY - tuning.tubePadding * s - side / 2 - CGFloat(slot) * (side + tuning.unitGap * s)
            - (up ? tuning.liftHeight * s : 0)
        return CGPoint(x: f.midX, y: y)
    }

    // MARK: animating the session's events

    private func move(_ l: CALayer, to p: CGPoint, arcTop: CGFloat?, duration: Double) {
        let from = l.presentation()?.position ?? l.position
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        l.position = p
        CATransaction.commit()
        guard duration > 0 else { return }
        let path = UIBezierPath()
        path.move(to: from)
        if let top = arcTop {
            path.addLine(to: CGPoint(x: from.x, y: top))
            path.addLine(to: CGPoint(x: p.x, y: top))
        }
        path.addLine(to: p)
        let a = CAKeyframeAnimation(keyPath: "position")
        a.path = path.cgPath
        a.duration = duration
        a.calculationMode = .paced
        a.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        l.add(a, forKey: "move")
    }

    private func setStroke(_ tube: Int, _ rgb: UInt32) {
        guard glass.indices.contains(tube) else { return }
        glass[tube].strokeColor = UIColor(rgb: rgb).cgColor
    }

    private func restStroke(_ tube: Int) -> UInt32 {
        guard tubes.indices.contains(tube), SortMechanics.isComplete(tubes[tube], capacity: capacity) else {
            return Skin.puzzleSortBoardTubeStroke
        }
        return Skin.puzzleSortBoardTubeComplete
    }

    private func lift(_ tube: Int, count: Int) {
        guard units.indices.contains(tube) else { return }
        if let l = lifted, l.tube != tube { drop(l.tube) }
        lifted = (tube, min(count, units[tube].count))
        setStroke(tube, Skin.puzzleSortBoardTubeSelected)
        for (j, u) in units[tube].enumerated() where isLifted(tube: tube, slot: j) {
            move(u, to: center(tube: tube, slot: j, lifted: true), arcTop: nil, duration: tuning.liftSeconds)
        }
    }

    private func drop(_ tube: Int) {
        guard units.indices.contains(tube) else { return }
        if lifted?.tube == tube { lifted = nil }
        setStroke(tube, restStroke(tube))
        for (j, u) in units[tube].enumerated() {
            move(u, to: center(tube: tube, slot: j, lifted: false), arcTop: nil, duration: tuning.liftSeconds)
        }
    }

    /// `count` units from the top of `from` onto `to` (a pour, or an undo going back), over the higher of the two tubes.
    private func transfer(from: Int, to: Int, count: Int) {
        guard units.indices.contains(from), units.indices.contains(to), count > 0, units[from].count >= count,
              tubes.indices.contains(from), tubes[from].count >= count else { resync(); return }
        if lifted?.tube == from { lifted = nil }
        let moving = Array(units[from].suffix(count))
        units[from].removeLast(count)
        let colours = Array(tubes[from].suffix(count))
        tubes[from].removeLast(count)
        let base = units[to].count
        units[to].append(contentsOf: moving)
        tubes[to].append(contentsOf: colours)
        setStroke(from, restStroke(from))
        setStroke(to, restStroke(to))
        let s = layout.scale
        let top = min(tubeTop(from), tubeTop(to)) - (tuning.liftHeight + tuning.pourArc) * s
        for (i, u) in moving.enumerated() {
            move(u, to: center(tube: to, slot: base + i, lifted: false), arcTop: top, duration: tuning.pourSeconds)
        }
    }

    private func tubeTop(_ tube: Int) -> CGFloat { layout.tubes.indices.contains(tube) ? layout.tubes[tube].minY : 0 }

    private func refuse(_ tube: Int) {
        guard glass.indices.contains(tube), units.indices.contains(tube) else { return }
        let shake = CAKeyframeAnimation(keyPath: "transform.translation.x")
        let a = tuning.refuseShake * layout.scale
        shake.values = [0, a, -a, a / 2, -a / 2, 0]
        shake.duration = tuning.refuseSeconds
        glass[tube].add(shake, forKey: "refuse")
        for u in units[tube] { u.add(shake, forKey: "refuse") }
        let flash = CABasicAnimation(keyPath: "strokeColor")
        flash.fromValue = UIColor(rgb: Skin.puzzleSortBoardTubeRefused).cgColor
        flash.toValue = UIColor(rgb: restStroke(tube)).cgColor
        flash.duration = tuning.refuseFlashSeconds
        glass[tube].add(flash, forKey: "refuseFlash")
    }

    /// The completion pulse of one tube (after its pour lands), and the tube's complete stroke.
    private func complete(_ tube: Int, after delay: Double, duration: Double? = nil) {
        guard glass.indices.contains(tube) else { return }
        setStroke(tube, restStroke(tube))
        let pulse = CAKeyframeAnimation(keyPath: "transform.scale")
        pulse.values = [1, tuning.completeScale, 1]
        pulse.duration = duration ?? tuning.completeSeconds
        pulse.beginTime = CACurrentMediaTime() + delay
        pulse.fillMode = .backwards
        glass[tube].add(pulse, forKey: "complete")
    }

    private func addTubes(_ n: Int) {
        guard n > 0 else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        for _ in 0..<n {
            let g = makeGlass()
            g.opacity = 0
            tubesLayer.addSublayer(g)
            glass.append(g)
            units.append([])
            tubes.append([])
        }
        CATransaction.commit()
        layoutAll(duration: tuning.layoutSeconds)
        CATransaction.begin()
        CATransaction.setAnimationDuration(tuning.tubeAddSeconds)
        for g in glass.suffix(n) { g.opacity = 1 }
        CATransaction.commit()
    }

    private func fade(to opacity: Float, duration: Double) {
        CATransaction.begin()
        CATransaction.setAnimationDuration(duration)
        CATransaction.setDisableActions(duration <= 0)
        root.opacity = opacity
        CATransaction.commit()
    }
}
