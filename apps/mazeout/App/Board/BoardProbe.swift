import UIKit
import PathCore

// B1 (SPEC-architecture §9.4, P8). The board fills its half of `BoardProbeData` (zoom, pitch, settled, moving, fps, each
// live arrow's tap point + red flag, the tapes); the session's half (lvl, stage, phase, t, hearts, free, unit, hidden,
// counters) comes from the delegate when it conforms to `BoardProbeSupplying` (GAME's GameController, BoardLab), so
// GAME merges without a contract change. Published under `-pc.uitest 1` as the `board.probe` element's value and under
// `-pc.probeFile 1` as Documents/probe.json, refreshed continuously at ≤ `probe.hz` (4 Hz) from the display link.

/// A board delegate that also owns the session's half of the probe.
@MainActor protocol BoardProbeSupplying: AnyObject {
    func supplementProbe(_ probe: inout BoardProbeData)
}

extension BoardEngine {
    /// The board's half of the probe.
    func boardProbe() -> BoardProbeData {
        var p = BoardProbeData()
        p.zoom = Double(zoomScale)
        p.pitch = Double(pitchOnScreen)
        p.settled = isSettled
        p.moving = movers.values.filter { $0.kind == .exit || $0.kind == .bump }.count
        p.fps = perf.snapshot().fps.rounded()
        guard let st = stage else { return p }
        p.stage = st.stage
        p.stages = st.stages
        p.lvl = st.level.level
        var arrows: [BoardProbeData.Arrow] = []
        arrows.reserveCapacity(nodes.count)
        for a in st.level.arrows {
            guard let n = nodes[a.id], n.attached, !preAttached.contains(a.id), movers[a.id]?.kind != .exit else { continue }
            let pt = tapPoint(of: a.id)
            arrows.append(BoardProbeData.Arrow(id: a.id.raw, x: pt.map { Double($0.x) } ?? -1, y: pt.map { Double($0.y) } ?? -1,
                                               free: false, unit: [a.id.raw], red: n.marked))
        }
        p.arrows = arrows
        p.hidden = st.level.arrows.filter { (nodes[$0.id]?.attached != true || preAttached.contains($0.id)) && !exited.contains($0.id) }
            .map(\.id.raw)
        p.obstacles = (st.level.obstacles.filter { $0.kind == .tape }.map {
            BoardProbeData.Obstacle(id: $0.id.raw, k: $0.kind.rawValue, n: nil, state: tapes[$0.id] == nil ? "gone" : "on")
        } + obstacles.probeRows()).sorted { $0.id < $1.id }
        return p
    }

    /// Publishes the merged probe (element value + optional file). Called from the display link at ≤ probe.hz.
    func publishProbe() {
        var p = boardProbe()
        (delegate as? BoardProbeSupplying)?.supplementProbe(&p)
        let json = p.json()
        if json != lastProbeJSON {
            lastProbeJSON = json
            container.probeElement.accessibilityValue = json
            if args.probeFile {
                let url = Self.documents.appendingPathComponent("probe.json")
                let data = Data(json.utf8)
                DispatchQueue.global(qos: .utility).async { try? data.write(to: url, options: .atomic) }
            }
        }
    }

    static var documents: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
    }
}
