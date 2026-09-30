import Foundation

// C1 (SPEC-architecture §3.4 rule 4, §14). Every measured or PENDING value in Motion/ and Grid/Metrics is a Codable
// parameter struct with compiled defaults (`.measured`, `.style`). The app keeps its values as DATA: an owner reads a
// Tuning JSON object (board.json, ui.json, …) and applies it with `overridden(by:)`, so SPEC-motion-audio / SPEC-ui can
// replace a number without a code change. Missing keys keep the default; keys the struct does not know are reported
// (`unknownKeys(in:)`) and ignored, never a crash.

public protocol TunableParameters: Codable {}

public enum TunableError: Error, CustomStringConvertible {
    case notAnObject
    case decoding(String)
    public var description: String {
        switch self {
        case .notAnObject: return "tuning override is not a JSON object"
        case .decoding(let s): return "tuning override does not decode: \(s)"
        }
    }
}

extension TunableParameters {
    /// A copy whose fields present in `json` (a JSON object; nested objects merge recursively, arrays replace) replace
    /// this value's. Throws when a known key carries the wrong type.
    public func overridden(by json: Data) throws -> Self {
        guard let over = try JSONSerialization.jsonObject(with: json) as? [String: Any] else { throw TunableError.notAnObject }
        return try overridden(byObject: over)
    }

    /// Same, from an already parsed JSON object (what `TuningFile` hands out).
    public func overridden(byObject over: [String: Any]) throws -> Self {
        let baseData = try JSONEncoder().encode(self)
        guard let base = try JSONSerialization.jsonObject(with: baseData) as? [String: Any] else { throw TunableError.notAnObject }
        let merged = Self.merge(base, over)
        let data = try JSONSerialization.data(withJSONObject: merged, options: [.sortedKeys])
        do { return try JSONDecoder().decode(Self.self, from: data) } catch { throw TunableError.decoding(String(describing: error)) }
    }

    /// Key paths in `json` that this parameter set does not have (dotted, e.g. "badge.scale0"); reported, never applied.
    public func unknownKeys(in json: Data) -> [String] {
        guard let over = (try? JSONSerialization.jsonObject(with: json)) as? [String: Any],
              let baseData = try? JSONEncoder().encode(self),
              let base = (try? JSONSerialization.jsonObject(with: baseData)) as? [String: Any] else { return [] }
        return Self.unknown(base, over, prefix: "").sorted()
    }

    static func merge(_ base: [String: Any], _ over: [String: Any]) -> [String: Any] {
        var out = base
        for (k, v) in over where base[k] != nil {
            if let b = base[k] as? [String: Any], let o = v as? [String: Any] { out[k] = merge(b, o) } else { out[k] = v }
        }
        return out
    }

    static func unknown(_ base: [String: Any], _ over: [String: Any], prefix: String) -> [String] {
        var out: [String] = []
        for (k, v) in over {
            let path = prefix.isEmpty ? k : prefix + "." + k
            guard let b = base[k] else { if !k.hasPrefix("_") { out.append(path) }; continue }
            if let bo = b as? [String: Any], let oo = v as? [String: Any] { out += unknown(bo, oo, prefix: path) }
        }
        return out
    }
}

// MARK: - KeyTrack as data

extension KeyTrack: Codable {
    private enum K: String, CodingKey { case t, v, interpolation, endSlopesZero }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: K.self)
        let t = try c.decode([Double].self, forKey: .t)
        let v = try c.decode([Double].self, forKey: .v)
        guard !t.isEmpty, t.count == v.count else {
            throw DecodingError.dataCorruptedError(forKey: .v, in: c, debugDescription: "KeyTrack needs as many values as times (≥ 1)")
        }
        guard zip(t, t.dropFirst()).allSatisfy({ $0 < $1 }) else {
            throw DecodingError.dataCorruptedError(forKey: .t, in: c, debugDescription: "KeyTrack times must be strictly increasing")
        }
        let interp = try c.decodeIfPresent(String.self, forKey: .interpolation).flatMap(Interpolation.init(rawValue:)) ?? .linear
        let flat = try c.decodeIfPresent(Bool.self, forKey: .endSlopesZero) ?? false
        self.init(Array(zip(t, v)), interpolation: interp, endSlopesZero: flat)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: K.self)
        try c.encode(times, forKey: .t)
        try c.encode(values, forKey: .v)
        try c.encode(interpolation.rawValue, forKey: .interpolation)
        try c.encode(endSlopesZero, forKey: .endSlopesZero)
    }
}
