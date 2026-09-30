import Foundation

// C3 (SPEC-architecture §4.12). MF's Migrations (e10a076), renamed. Upgrades a saved PlayerState JSON object step by step
// to `PlayerState.schemaVersion`:
// - a save without a `version` key (written before the schema was numbered) is version 0;
// - `steps[v]` turns a version-v object into a version-(v + 1) object and sets "version" to v + 1; they run in order, so a
//   v1 save opened by a v4 build goes 1 → 2 → 3 → 4;
// - schema v1 is the first real version: 0 → 1 only stamps the version, because PlayerState decodes every missing key to its
//   default (additive-only evolution needs no step); a rename / removal (orchestrator-approved) adds one step here and one
//   fixture in PersistenceTests;
// - a save from a NEWER build (version above ours) is left as it is: the tolerant decoder reads what it knows.

extension PlayerState {
    /// The schema this build writes (◆ PlayerState.version's default).
    public static var schemaVersion: Int { PlayerState().version }
}

public enum Migrations {
    public typealias Step = ([String: Any]) -> [String: Any]

    /// The shipped steps, keyed by the version they upgrade FROM.
    public static let steps: [Int: Step] = [
        0: { j in var o = j; o["version"] = 1; return o },
    ]

    /// The version a JSON object claims (0 when missing or malformed).
    public static func version(of json: [String: Any]) -> Int {
        if let v = json["version"] as? Int { return v }
        if let n = json["version"] as? NSNumber { return n.intValue }
        return 0
    }

    public static func upgrade(_ json: [String: Any]) -> [String: Any] {
        upgrade(json, steps: steps, to: PlayerState.schemaVersion)
    }

    /// The general form (tests inject steps). A missing step stops the chain where it is.
    public static func upgrade(_ json: [String: Any], steps: [Int: Step], to target: Int) -> [String: Any] {
        var j = json
        var v = version(of: j)
        while v < target, let step = steps[v] {
            j = step(j)
            let next = version(of: j)
            v = next > v ? next : v + 1          // a step that forgot to stamp its version still advances
            j["version"] = v
        }
        return j
    }
}
