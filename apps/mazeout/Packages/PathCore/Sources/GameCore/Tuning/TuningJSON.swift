import Foundation

// Template phase 1: the tolerant-decoding helpers every tuning table of the core shares (moved from
// ArrowEscape/Rules/RulesTuning.swift so GameCore's tables — EconomyRules, EventRules, MetaRules — and the puzzle's
// tables use one implementation). `package` access: visible to every target of this package, not to the app.

/// Dotted `-pc.tune` overrides onto a decoded JSON object (`RulesTuning.load`, `EconomyRules.load`).
package enum TuningJSON {
    package static func overrideValue(_ raw: String) -> Any {
        if raw.contains(";") { return raw.split(separator: ";").map { overrideValue(String($0)) } }
        if let i = Int(raw) { return i }
        if let d = Double(raw) { return d }
        switch raw.lowercased() {
        case "true", "yes", "on": return true
        case "false", "no", "off": return false
        default: return raw
        }
    }

    package static func setPath(_ obj: [String: Any], _ parts: ArraySlice<String>, _ value: Any) -> [String: Any] {
        var o = obj
        guard let head = parts.first else { return o }
        if parts.count == 1 { o[head] = value; return o }
        o[head] = setPath((o[head] as? [String: Any]) ?? [:], parts.dropFirst(), value)
        return o
    }
}

extension KeyedDecodingContainer {
    /// `decodeIfPresent` with a default (the tolerant decoding of every tuning struct).
    package func v<T: Decodable>(_ key: Key, _ fallback: T) throws -> T { try decodeIfPresent(T.self, forKey: key) ?? fallback }
}
