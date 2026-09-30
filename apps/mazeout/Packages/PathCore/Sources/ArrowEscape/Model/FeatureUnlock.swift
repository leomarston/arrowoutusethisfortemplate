import Foundation
import GameCore

// C1 (SPEC-architecture §4.3, §8.4 UnlockDirector). The `FeatureUnlock` row itself is GameCore's (Session/FeatureUnlock.swift,
// moved in the kit decoupling step); the bundle's list reader stays here with the bundle schema it checks
// (`LevelJSON.bundleSchema`). Examples of this module's rows: {"feature":"linked","level":7,"title":"Linked Arrows!",
// "card":"LINKED ARROWS move together!","caps":"LINKED ARROWS","icon":"unlockIconLinked"}.

extension FeatureUnlock {
    /// unlocks.json in either form.
    public static func decodeList(_ data: Data) throws -> [FeatureUnlock] {
        let top = try JSONSerialization.jsonObject(with: data)
        if top is [Any] { return try JSONDecoder().decode([FeatureUnlock].self, from: data) }
        struct Wrapped: Decodable { var schema: Int?; var unlocks: [FeatureUnlock] }
        let w = try JSONDecoder().decode(Wrapped.self, from: data)
        if let s = w.schema, s > LevelJSON.bundleSchema { throw LevelJSONError.badValue("unlocks schema \(s) is newer than \(LevelJSON.bundleSchema)") }
        return w.unlocks
    }
}
