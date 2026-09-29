import Foundation

// C4 (SPEC-architecture §4.14 `pclevels bundle`; SPEC-gameplay §14.1; CONSISTENCY O-5). design/levels.json → the bundle
// folder (App/Resources/Levels): level_NNNN.json = each level object AS IT IS (canonical: sorted keys, compact, Python's
// number forms, "_from" comments kept) + "\n"; sessions.json / unlocks.json / tutorials.json = {"schema":1,"<key>":[…]};
// curve.json = the curve object. Deterministic bytes: running it twice, or on an unchanged levels.json, rewrites the
// folder byte for byte (L1 acceptance). Every file written is decoded back (LevelJSON / LevelLibrary) before it counts.
// PUBLISH B0 (SPEC.md ruling 39 OD8, "STRIP provenance from every shipped file"): App/Resources/Levels ships the `.publish`
// form — the encoded form without the research trail (no "_" comment keys, no `capture`; FIX-2 B N-01: no `source`, no
// `metrics`); design/levels.json keeps all of them.

public enum ContentBundle {

    public struct Summary: Sendable, Equatable {
        public var levels: Int
        public var authoredEnd: Int
        public var files: [String]
    }

    public enum BundleError: Error, CustomStringConvertible, Equatable {
        case bad(String)
        public var description: String { switch self { case .bad(let s): return "bundle: \(s)" } }
    }

    /// How a level file is written.
    public enum Form: String, Sendable {
        /// SPEC-gameplay §14.1 / CONSISTENCY O-5: each level object as it is (the design/levels.json line + "\n").
        case asIs
        /// C1's `LevelJSON.encodeBundle` bytes (null keys, layer 1 and empty lists elided) with the source's "_" comment
        /// keys first, sessions via `LevelJSON.encodeSessions`, unlocks / tutorials via the canonical encoder — the form
        /// CONTENT's tools/levels/lvtool writes today.
        case encoded
        /// What ships (PUBLISH B0, ruling 39 OD8): `.encoded` with the provenance stripped — no "_" comment keys and no
        /// `capture` (the research shot / video frame a board was read from); FIX-2 lane B (N-01): no `source` (recorded /
        /// video) and no `metrics` (the bot's measurements) either (`LevelJSON.encodePublish`). The runtime reads none of
        /// them; the content validators check them on design/levels.json (Validator.Options.provenance `.source`) and their
        /// absence here (`.publish`). tools/levels/lvtool `bundle --publish` writes the same bytes;
        /// design/tools/strip_provenance.py `check-bundle --publish` is the independent Python mirror.
        case publish
    }

    struct UnlocksFile: Encodable { var schema: Int; var unlocks: [FeatureUnlock] }
    struct TutorialsFile: Encodable { var schema: Int; var tutorials: [TutorialScript] }

    static func canonical<T: Encodable>(_ v: T) throws -> Data {
        var d = try LevelJSON.canonicalEncoder().encode(v)
        d.append(0x0A)
        return d
    }

    /// The files of the bundle folder as bytes (file name → contents), without touching the disk.
    public static func files(of doc: JSONValue, form: Form = .asIs) throws -> [String: Data] {
        guard let levels = doc["levels"]?.arrayValue else { throw BundleError.bad("no \"levels\"") }
        var out: [String: Data] = [:]
        for v in levels {
            guard let n = v["level"]?.intValue else { throw BundleError.bad("a level without a number") }
            var data = ContentJSON.data(v, newline: true)
            let l: LevelSpec
            do { l = try LevelJSON.decodeBundle(data) } catch { throw BundleError.bad("L\(n) does not decode: \(error)") }
            guard l.level == n else { throw BundleError.bad("L\(n) decodes as L\(l.level)") }
            if form == .publish {
                data = try LevelJSON.encodePublish(l)
                guard try LevelJSON.decodeBundle(data) == LevelJSON.publishModel(l) else {
                    throw BundleError.bad("L\(n): publish bytes do not decode back")
                }
            } else if form == .encoded {
                data = try LevelJSON.encodeBundle(l)
                let enc = LevelJSON.canonicalEncoder()
                var insert = Data()
                for (k, c) in (v.objectPairs ?? []).filter({ $0.0.hasPrefix("_") }).sorted(by: { $0.0 < $1.0 }) {
                    guard let s = c.stringValue else { throw BundleError.bad("L\(n): comment \(k) is not a string") }
                    insert.append(try enc.encode(k)); insert.append(UInt8(ascii: ":"))
                    insert.append(try enc.encode(s)); insert.append(UInt8(ascii: ","))
                }
                if !insert.isEmpty { data.insert(contentsOf: insert, at: data.startIndex + 1) }
                guard try LevelJSON.decodeBundle(data) == l else { throw BundleError.bad("L\(n): encoded bytes do not decode back") }
            }
            let name = LevelLibrary.fileName(level: n)
            guard out[name] == nil else { throw BundleError.bad("L\(n) twice") }
            out[name] = data
        }
        for (name, key) in [("sessions.json", "sessions"), ("unlocks.json", "unlocks"), ("tutorials.json", "tutorials")] {
            let asIs = ContentJSON.data(.object([("schema", .int(LevelJSON.bundleSchema)), (key, doc[key] ?? .array([]))]), newline: true)
            guard form != .asIs else { out[name] = asIs; continue }
            do {
                switch key {
                case "sessions": out[name] = try LevelJSON.encodeSessions(try LevelJSON.decodeSessions(asIs))
                case "unlocks": out[name] = try canonical(UnlocksFile(schema: LevelJSON.bundleSchema, unlocks: try FeatureUnlock.decodeList(asIs)))
                default: out[name] = try canonical(TutorialsFile(schema: LevelJSON.bundleSchema, tutorials: try TutorialScript.decodeList(asIs)))
                }
            } catch { throw BundleError.bad("\(name): \(error)") }
        }
        if let c = doc["curve"] {
            do { _ = try CurveSpec(json: c) } catch { throw BundleError.bad("curve: \(error)") }
            out["curve.json"] = ContentJSON.data(c, newline: true)
        }
        return out
    }

    /// Writes the folder and loads it back through LevelLibrary (a load problem fails the bundle).
    @discardableResult
    public static func write(_ doc: JSONValue, to folder: URL, form: Form = .asIs) throws -> Summary {
        let files = try files(of: doc, form: form)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        for (name, data) in files { try data.write(to: folder.appendingPathComponent(name), options: .atomic) }
        let lib = try LevelLibrary.load(folder: folder)
        if !lib.problems.isEmpty { throw BundleError.bad("library problems: " + lib.problems.joined(separator: "; ")) }
        for n in 1...max(1, lib.authoredCount) where lib.authored(n) == nil {
            throw BundleError.bad("\(LevelLibrary.fileName(level: n)) does not load back")
        }
        return Summary(levels: files.keys.filter { $0.hasPrefix("level_") }.count, authoredEnd: lib.authoredCount,
                       files: files.keys.sorted())
    }
}
