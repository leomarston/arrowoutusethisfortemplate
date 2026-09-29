import Foundation
import CoreGraphics

// SHELL S1 (SPEC-architecture §6.4 item 2, D14; art/PIPELINE.md §3.1 rig format). A cut-out puppet exported by the art pipeline:
// `Art/<name>/rig.json` = {character, frame_pt, full, placement_pt, layers: [{name, file, z, rect_pt, pivots_pt, group?,
// default?, overlay?, parent?}], groups: {g: {members, default}}, proof}. Every layer shares the full render's camera, so
// drawing each DEFAULT layer at its `rect_pt` recomposes the full render (the art lane's proof; ShellTests re-prove it through
// this loader + PuppetStage's layer tree, mean ≤ 1/255).

struct PuppetRig {
    struct Layer: Equatable {
        let name: String
        let file: String
        let z: Int
        let rect: CGRect                        // pt inside the frame, origin top-left
        let pivots: [String: CGPoint]           // pt inside the frame
        let group: String?
        let isDefault: Bool
        let overlay: Bool
        let parent: String?
    }

    let name: String                            // the rig folder ("char_boss_home_rig")
    let character: String
    let frame: CGSize                           // frame_pt
    let placement: CGPoint                      // frame top-left on the 393 x 852 screen (pt)
    let fullPath: String?                       // bundle path of the full render ("Art/char_boss_home@3x.png")
    let layers: [Layer]                         // back → front (z)
    let groups: [String: (members: [String], defaultMember: String)]

    /// The rig's layers drawn at rest: non-group, non-overlay layers + each group's default member.
    var restLayers: [Layer] { layers.filter(isVisibleAtRest) }

    func isVisibleAtRest(_ l: Layer) -> Bool {
        if l.overlay { return false }
        if let g = l.group, let group = groups[g] { return group.defaultMember == l.name }
        return true
    }

    func layer(_ name: String) -> Layer? { layers.first { $0.name == name } }

    /// A pivot by name from any layer that declares it ("feet", "neck", "shoulder" …).
    func pivot(_ name: String) -> CGPoint? {
        for l in layers { if let p = l.pivots[name] { return p } }
        return nil
    }

    /// Bundle path of a layer's PNG.
    func path(_ l: Layer) -> String { "Art/\(name)/\(l.file)" }

    enum LoadError: Error, CustomStringConvertible {
        case missing(String), malformed(String)
        var description: String {
            switch self { case .missing(let s): return "missing \(s)"; case .malformed(let s): return "malformed \(s)" }
        }
    }

    static func load(_ name: String, bundle: Bundle = .main) throws -> PuppetRig {
        guard let url = bundle.resourceURL?.appendingPathComponent("Art/\(name)/rig.json"),
              let data = try? Data(contentsOf: url) else { throw LoadError.missing("Art/\(name)/rig.json") }
        return try parse(name, data: data)
    }

    static func parse(_ name: String, data: Data) throws -> PuppetRig {
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LoadError.malformed(name) }
        func pt(_ a: Any?) -> CGPoint? {
            guard let v = a as? [Any], v.count == 2, let x = (v[0] as? NSNumber)?.doubleValue,
                  let y = (v[1] as? NSNumber)?.doubleValue else { return nil }
            return CGPoint(x: x, y: y)
        }
        guard let fr = root["frame_pt"] as? [Any], fr.count == 2, let fw = (fr[0] as? NSNumber)?.doubleValue,
              let fh = (fr[1] as? NSNumber)?.doubleValue else { throw LoadError.malformed("\(name) frame_pt") }
        let placement = root["placement_pt"] as? [String: Any]
        let px = (placement?["x"] as? NSNumber)?.doubleValue ?? 0
        let py = (placement?["y"] as? NSNumber)?.doubleValue ?? 0
        var layers: [Layer] = []
        for item in root["layers"] as? [[String: Any]] ?? [] {
            guard let n = item["name"] as? String, let file = item["file"] as? String, let r = item["rect_pt"] as? [Any], r.count == 4
            else { throw LoadError.malformed("\(name) layer") }
            let rv = r.compactMap { ($0 as? NSNumber)?.doubleValue }
            guard rv.count == 4 else { throw LoadError.malformed("\(name) \(n) rect_pt") }
            var pivots: [String: CGPoint] = [:]
            for (k, v) in item["pivots_pt"] as? [String: Any] ?? [:] { if let p = pt(v) { pivots[k] = p } }
            layers.append(Layer(name: n, file: file, z: (item["z"] as? Int) ?? layers.count,
                                rect: CGRect(x: rv[0], y: rv[1], width: rv[2], height: rv[3]), pivots: pivots,
                                group: item["group"] as? String, isDefault: (item["default"] as? Bool) ?? false,
                                overlay: (item["overlay"] as? Bool) ?? false, parent: item["parent"] as? String))
        }
        var groups: [String: (members: [String], defaultMember: String)] = [:]
        for (g, v) in root["groups"] as? [String: [String: Any]] ?? [:] {
            let members = v["members"] as? [String] ?? []
            groups[g] = (members, (v["default"] as? String) ?? members.first ?? "")
        }
        let full = (root["full"] as? String).map { f -> String in
            f.hasPrefix("../") ? "Art/" + String(f.dropFirst(3)) : "Art/\(name)/\(f)"
        }
        return PuppetRig(name: name, character: root["character"] as? String ?? name, frame: CGSize(width: fw, height: fh),
                         placement: CGPoint(x: px, y: py), fullPath: full, layers: layers.sorted { $0.z < $1.z }, groups: groups)
    }
}
