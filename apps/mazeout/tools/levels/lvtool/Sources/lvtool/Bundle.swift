import CryptoKit
import Foundation
import PathCore

// `lvtool bundle <design/levels.json> <out dir> [--publish] [--check] [--manifest FILE]`
//
// --publish (PUBLISH B0; SPEC.md ruling 39 OD8 "STRIP provenance from every shipped file"): the SHIPPED form of
//   App/Resources/Levels — each level file WITHOUT its research trail: no "_" comment keys, no `capture`, and (FIX-2 B,
//   N-01) no `source` and no `metrics` (`LevelJSON.encodePublish`). = PathCore's ContentBundle `.publish`; design/tools/strip_provenance.py
//   `check-bundle --publish` is the independent Python mirror. The small files and curve.json are the same in both forms
//   (the curve's "_about" is neutral text at the source, so the bundled curve stays = CurveSpec.default).
//
// SPEC-gameplay §14.1 / SPEC-architecture §4.3: design/levels.json -> App/Resources/Levels:
//   level_NNNN.json  one per level: C1's canonical bundle bytes (`LevelJSON.encodeBundle`: sorted keys, no escaped
//                    slashes, compact, one trailing newline) of the level decoded through the ◆ LevelSpec Codable path,
//                    plus the level's "_" comment keys (`_from`: CONSISTENCY O-5, "pclevels bundle copies it") spliced in
//                    at their sorted position (they sort before every lower-case key). The decoder ignores them.
//   sessions.json    `LevelJSON.encodeSessions` ({"schema":1,"sessions":[…]})
//   unlocks.json     {"schema":1,"unlocks":[…]}   (FeatureUnlock, canonical encoder)
//   tutorials.json   {"schema":1,"tutorials":[…]} (TutorialScript, canonical encoder)
//   curve.json       (L2) the source's `curve` object in PathCore's canonical content JSON (`ContentJSON.data`, the bytes
//                    `pclevels bundle` writes; JSONSerialization cannot hold curve.salt > Int64.max), decoded back through
//                    C4's `CurveSpec` and loaded back through `LevelLibrary.curve` before it counts.
// Every level is proven lossless on the way: the source object has no key the bundle schema does not know, the
// canonical bytes decode back to the same model, and (tools/levels/bundle_check.py, independently, in Python) the bundle
// equals the source object value for value.
// --check writes nothing: it compares every file with the folder byte for byte and lists missing / stale / extra files.

struct DocFile: Decodable {
    var authoredEnd: Int?
    var levels: [LevelSpec]
    var sessions: [SessionPlan]?
    var unlocks: [FeatureUnlock]?
    var tutorials: [TutorialScript]?
}

struct UnlocksFile: Encodable { var schema: Int; var unlocks: [FeatureUnlock] }
struct TutorialsFile: Encodable { var schema: Int; var tutorials: [TutorialScript] }

struct Content {
    var authoredEnd: Int
    var raw: [[String: Any]]
    var levels: [LevelSpec]
    var sessions: [SessionPlan]
    var unlocks: [FeatureUnlock]
    var tutorials: [TutorialScript]

    static func load(_ path: String) throws -> Content {
        let data = try readData(path)
        guard let top = try jsonObject(data, path) as? [String: Any], let raw = top["levels"] as? [[String: Any]] else {
            throw ToolError("\(path): no top-level `levels` array")
        }
        let doc: DocFile
        do { doc = try JSONDecoder().decode(DocFile.self, from: data) } catch {
            throw ToolError("\(path) does not decode through the ◆ LevelSpec Codable path: \(error)")
        }
        guard raw.count == doc.levels.count else { throw ToolError("\(path): raw/decoded level count differs") }
        return Content(authoredEnd: doc.authoredEnd ?? doc.levels.count, raw: raw, levels: doc.levels,
                       sessions: doc.sessions ?? [], unlocks: doc.unlocks ?? [], tutorials: doc.tutorials ?? [])
    }
}

func canonical<T: Encodable>(_ v: T) throws -> Data {
    var d = try LevelJSON.canonicalEncoder().encode(v)
    d.append(0x0A)
    return d
}

/// The bundle bytes of one level: C1's canonical encoding + the "_" comment keys of the source object; `publish`: the
/// level without capture, source and metrics and no comment keys (what ships; FIX-2 B N-01).
func levelBytes(_ spec: LevelSpec, raw: [String: Any], publish: Bool = false) throws -> Data {
    if publish { return try LevelJSON.encodePublish(spec) }
    var out = try LevelJSON.encodeBundle(spec)
    let comments = raw.keys.filter { $0.hasPrefix("_") }.sorted()
    guard !comments.isEmpty else { return out }
    let enc = LevelJSON.canonicalEncoder()
    var insert = Data()
    for k in comments {
        guard let s = raw[k] as? String else { throw ToolError("L\(spec.level): comment key \(k) is not a string") }
        insert.append(try enc.encode(k))
        insert.append(UInt8(ascii: ":"))
        insert.append(try enc.encode(s))
        insert.append(UInt8(ascii: ","))
    }
    guard out.first == UInt8(ascii: "{"), out.count > 2 else { throw ToolError("L\(spec.level): unexpected encoding") }
    out.insert(contentsOf: insert, at: out.startIndex + 1)
    return out
}

func sha256(_ d: Data) -> String { SHA256.hash(data: d).map { String(format: "%02x", $0) }.joined() }

func cmdBundle(_ a: Args) throws -> Int32 {
    guard a.positional.count == 2 else { throw ToolError("usage: lvtool bundle <design/levels.json> <out dir> [--publish] [--check] [--manifest FILE]") }
    let (src, outDir) = (a.positional[0], a.positional[1])
    let check = a.flags.contains("check")
    let publish = a.flags.contains("publish")
    let content = try Content.load(src)
    var files: [(String, Data)] = []
    var problems: [String] = []

    for (raw, spec) in zip(content.raw, content.levels) {
        guard let n = raw["level"] as? Int, n == spec.level else { problems.append("raw/decoded order differs at L\(spec.level)"); continue }
        let rawData = try JSONSerialization.data(withJSONObject: raw)
        let rawReport = try LevelJSON.inspectBundle(rawData)
        if !rawReport.unknownKeys.isEmpty {
            problems.append("L\(n): source keys the bundle schema does not know (would be dropped): \(rawReport.unknownKeys)")
        }
        let bytes = try levelBytes(spec, raw: raw, publish: publish)
        let want = publish ? LevelJSON.publishModel(spec) : spec
        let back = try LevelJSON.decodeBundle(bytes)
        if back != want { problems.append("L\(n): canonical bytes do not decode back to the same model") }
        if publish, let s = String(data: bytes, encoding: .utf8),
           s.contains("\"capture\"") || s.contains("\"source\"") || s.contains("\"metrics\"") || s.contains("bot_")
            || s.contains("{\"_") || s.contains(",\"_") {
            problems.append("L\(n): the publish form still carries provenance")
        }
        if !(try LevelJSON.inspectBundle(bytes)).unknownKeys.isEmpty { problems.append("L\(n): bundle has unknown keys") }
        files.append((LevelLibrary.fileName(level: n), bytes))
    }
    let numbers = content.levels.map(\.level)
    if numbers != Array(1...max(1, content.authoredEnd)) || numbers.count != content.authoredEnd {
        problems.append("levels are not 1…authoredEnd (\(content.authoredEnd)): \(numbers.prefix(5))…")
    }
    files.append(("sessions.json", try LevelJSON.encodeSessions(content.sessions)))
    files.append(("unlocks.json", try canonical(UnlocksFile(schema: LevelJSON.bundleSchema, unlocks: content.unlocks))))
    files.append(("tutorials.json", try canonical(TutorialsFile(schema: LevelJSON.bundleSchema, tutorials: content.tutorials))))
    // curve.json (L2): the generator curve of the endless levels (SPEC-gameplay §14.1, §14.3)
    let doc = try ContentJSON.parse(try readData(src))
    if let c = doc["curve"] {
        let bytes = ContentJSON.data(c, newline: true)
        do {
            let spec = try CurveSpec(data: bytes)
            if spec.authoredEnd != content.authoredEnd { problems.append("curve.authoredEnd \(spec.authoredEnd) != authoredEnd \(content.authoredEnd)") }
            if try CurveSpec(json: c) != spec { problems.append("curve.json does not round-trip") }
        } catch { problems.append("curve does not decode as CurveSpec: \(error)") }
        files.append(("curve.json", bytes))
    } else {
        problems.append("\(src) has no `curve` (L2 bundles curve.json)")
    }

    // the small files must decode with the readers the app uses
    let tmpS = try LevelJSON.decodeSessions(files.first { $0.0 == "sessions.json" }!.1)
    if tmpS != content.sessions { problems.append("sessions.json does not round-trip") }
    if try FeatureUnlock.decodeList(files.first { $0.0 == "unlocks.json" }!.1) != content.unlocks { problems.append("unlocks.json does not round-trip") }
    if try TutorialScript.decodeList(files.first { $0.0 == "tutorials.json" }!.1) != content.tutorials { problems.append("tutorials.json does not round-trip") }

    guard problems.isEmpty else {
        for p in problems { FileHandle.standardError.write(Data("bundle: \(p)\n".utf8)) }
        return 1
    }

    let fm = FileManager.default
    let produced = Set(files.map(\.0))
    var existing: [String] = []
    if let names = try? fm.contentsOfDirectory(atPath: outDir) {
        existing = names.filter { $0.hasSuffix(".json") }.sorted()
    }
    let extra = existing.filter { !produced.contains($0) }
    var manifest = ""
    for (name, data) in files { manifest += "\(sha256(data))  \(name)\n" }

    /// The folder's curve as the app reads it (LevelLibrary.curveJSON -> C4's LevelLibrary.curve).
    func curveLoadsBack() throws -> String? {
        let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: outDir))
        guard let raw = lib.curveJSON, let want = files.first(where: { $0.0 == "curve.json" }) else { return "curve.json not read by LevelLibrary" }
        if raw != want.1 { return "LevelLibrary.curveJSON differs from the produced bytes" }
        if lib.curve != (try CurveSpec(data: want.1)) { return "LevelLibrary.curve is not the bundled curve (fell back to CurveSpec.default?)" }
        return nil
    }

    if check {
        var bad: [String] = []
        for (name, data) in files {
            let path = (outDir as NSString).appendingPathComponent(name)
            guard let cur = fm.contents(atPath: path) else { bad.append("missing \(name)"); continue }
            if cur != data { bad.append("stale \(name)") }
        }
        for e in extra { bad.append("extra \(e) (not produced from \(src))") }
        if bad.isEmpty, let p = try curveLoadsBack() { bad.append(p) }
        if let m = a.options["manifest"] { try writeData(Data(manifest.utf8), m) }
        if bad.isEmpty {
            print("bundle --check: \(files.count) files (\(content.levels.count) levels + sessions, unlocks, tutorials, curve\(publish ? "; publish form" : "")) identical to \(outDir), byte for byte; no extra file")
            return 0
        }
        for b in bad.prefix(40) { print("bundle --check: \(b)") }
        print("bundle --check: \(bad.count) difference(s)")
        return 1
    }
    for (name, data) in files { try writeData(data, (outDir as NSString).appendingPathComponent(name)) }
    if let p = try curveLoadsBack() { FileHandle.standardError.write(Data("bundle: \(p)\n".utf8)); return 1 }
    for e in extra { print("bundle: WARNING extra file left in \(outDir): \(e)") }
    if let m = a.options["manifest"] { try writeData(Data(manifest.utf8), m) }
    print("bundle: wrote \(files.count) files to \(outDir) (\(publish ? "publish form, " : "")\(content.levels.count) levels, sessions \(content.sessions.count), unlocks \(content.unlocks.count), tutorials \(content.tutorials.count), curve)")
    return extra.isEmpty ? 0 : 1
}
