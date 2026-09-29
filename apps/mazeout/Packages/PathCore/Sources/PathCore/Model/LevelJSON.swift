import Foundation

// C1 (SPEC-architecture §4.3). The level JSON: one model, three readers.
// - bundle v1 (App/Resources/Levels/level_NNNN.json, written by `pclevels bundle`): `LevelCoding` below — the ◆ Codable
//   bodies of the LevelSpec family call EXACTLY these entry points (SPEC.md §5 item 17: fixed signatures).
// - phone (research/levels/Lnnn.json) and video (research/video-frames/work/extract/V?-Lnnn.json): LevelImport.swift.
//
// Bundle v1 keys (snake_case; `Cell` = [c, r]; keys starting with "_" are comments, ignored):
//   level:    schema:1, level, source, capture?, cols, rows, mask?, timer_s, hearts, tag, arrows, obstacles, unlock?, seed?, metrics?
//   arrow:    id, cells, dir, layer? (default 1), hidden_by?
//   obstacle: id, kind, cells, arrows?, ends?, counter?, counter_at?, order?, opens?, turn?, reveals?, sprite?
//   pipe end: cell, out
//   metrics:  rounds, free_at_start, arrows, cells, mean_length, bot_time_left?
//   session:  id, levels, hud_label?, panel_label?, reward?, stage_gap_s?, hearts ("carry" | "reset", default carry)
// The obstacle field names are PENDING-gameplay (§4.3): if SPEC-gameplay freezes other names, only this file changes.

struct LevelKey: CodingKey, ExpressibleByStringLiteral {
    let stringValue: String
    init(stringLiteral value: String) { stringValue = value }
    init?(stringValue: String) { self.stringValue = stringValue }
    var intValue: Int? { nil }
    init?(intValue: Int) { return nil }
}

enum LevelCoding {
    static let bundleSchema = 1

    /// FIX-2 lane B (N-01): the research metric's key (design/levels.json; the headless bot's time left). Read and written by
    /// the macOS content tools only (Package.swift PC_RESEARCH); the shipped publish form carries no `metrics` at all, and the
    /// iOS app neither reads nor writes this key (so its binary does not hold the word).
    #if PC_RESEARCH
    static let botTimeKey: String? = "bot_time_left"
    #else
    static let botTimeKey: String? = nil
    #endif

    /// FIX-2 lane B (N-01): `LevelJSON.encodePublish` sets this `userInfo` flag: the level is written in the PUBLISH form,
    /// without `source`, `capture` and `metrics` (what ships says nothing of where a board came from or how it measured).
    static let publishForm = CodingUserInfoKey(rawValue: "pc.publishForm")!

    // Known keys (LevelJSON.inspectBundle reports anything else).
    static let levelKeys: Set<String> = ["schema", "level", "source", "capture", "cols", "rows", "mask", "timer_s", "hearts",
                                         "tag", "arrows", "obstacles", "unlock", "seed", "metrics"]
    static let arrowKeys: Set<String> = ["id", "cells", "dir", "layer", "hidden_by"]
    static let obstacleKeys: Set<String> = ["id", "kind", "cells", "arrows", "ends", "counter", "counter_at", "order", "opens",
                                            "turn", "reveals", "sprite"]
    static let endKeys: Set<String> = ["cell", "out"]
    static let metricsKeys: Set<String> = Set(["rounds", "free_at_start", "arrows", "cells", "mean_length"] + [botTimeKey].compactMap { $0 })
    static let sessionKeys: Set<String> = ["id", "levels", "hud_label", "panel_label", "reward", "stage_gap_s", "hearts"]

    // MARK: LevelSpec

    static func decodeLevel(from decoder: Decoder) throws -> LevelSpec {
        let c = try decoder.container(keyedBy: LevelKey.self)
        if let schema = try c.decodeIfPresent(Int.self, forKey: "schema"), schema > bundleSchema {
            throw DecodingError.dataCorruptedError(forKey: "schema", in: c,
                                                   debugDescription: "bundle schema \(schema) is newer than \(bundleSchema)")
        }
        return LevelSpec(
            level: try c.decode(Int.self, forKey: "level"),
            source: try c.decodeIfPresent(LevelSource.self, forKey: "source") ?? .designed,
            capture: try c.decodeIfPresent(String.self, forKey: "capture"),
            cols: try c.decode(Int.self, forKey: "cols"),
            rows: try c.decode(Int.self, forKey: "rows"),
            mask: try c.decodeIfPresent([String].self, forKey: "mask"),
            timerSeconds: try c.decode(Int.self, forKey: "timer_s"),
            hearts: try c.decodeIfPresent(Int.self, forKey: "hearts") ?? 3,
            tag: try c.decodeIfPresent(LevelTag.self, forKey: "tag") ?? .normal,
            arrows: try c.decodeIfPresent([ArrowSpec].self, forKey: "arrows") ?? [],
            obstacles: try c.decodeIfPresent([ObstacleSpec].self, forKey: "obstacles") ?? [],
            unlock: try c.decodeIfPresent(FeatureID.self, forKey: "unlock"),
            seed: try c.decodeIfPresent(UInt64.self, forKey: "seed"),
            metrics: try c.decodeIfPresent(LevelMetrics.self, forKey: "metrics"))
    }

    static func encode(_ l: LevelSpec, to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LevelKey.self)
        let publish = encoder.userInfo[publishForm] as? Bool == true
        try c.encode(bundleSchema, forKey: "schema")
        try c.encode(l.level, forKey: "level")
        if !publish {
            try c.encode(l.source, forKey: "source")
            try c.encodeIfPresent(l.capture, forKey: "capture")
        }
        try c.encode(l.cols, forKey: "cols")
        try c.encode(l.rows, forKey: "rows")
        try c.encodeIfPresent(l.mask, forKey: "mask")
        try c.encode(l.timerSeconds, forKey: "timer_s")
        try c.encode(l.hearts, forKey: "hearts")
        try c.encode(l.tag, forKey: "tag")
        try c.encode(l.arrows, forKey: "arrows")
        try c.encode(l.obstacles, forKey: "obstacles")
        try c.encodeIfPresent(l.unlock, forKey: "unlock")
        try c.encodeIfPresent(l.seed, forKey: "seed")
        if !publish { try c.encodeIfPresent(l.metrics, forKey: "metrics") }
    }

    // MARK: ArrowSpec

    static func decodeArrow(from decoder: Decoder) throws -> ArrowSpec {
        let c = try decoder.container(keyedBy: LevelKey.self)
        return ArrowSpec(id: try c.decode(ArrowID.self, forKey: "id"),
                         cells: try c.decode([Cell].self, forKey: "cells"),
                         dir: try c.decode(Dir.self, forKey: "dir"),
                         layer: try c.decodeIfPresent(Int.self, forKey: "layer") ?? 1,
                         hiddenBy: try c.decodeIfPresent(ObstacleID.self, forKey: "hidden_by"))
    }

    static func encode(_ a: ArrowSpec, to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LevelKey.self)
        try c.encode(a.id, forKey: "id")
        try c.encode(a.cells, forKey: "cells")
        try c.encode(a.dir, forKey: "dir")
        if a.layer != 1 { try c.encode(a.layer, forKey: "layer") }
        try c.encodeIfPresent(a.hiddenBy, forKey: "hidden_by")
    }

    // MARK: ObstacleSpec

    static func decodeObstacle(from decoder: Decoder) throws -> ObstacleSpec {
        let c = try decoder.container(keyedBy: LevelKey.self)
        return ObstacleSpec(id: try c.decode(ObstacleID.self, forKey: "id"),
                            kind: try c.decode(ObstacleKind.self, forKey: "kind"),
                            cells: try c.decodeIfPresent([Cell].self, forKey: "cells") ?? [],
                            arrows: try c.decodeIfPresent([ArrowID].self, forKey: "arrows") ?? [],
                            ends: try c.decodeIfPresent([PipeEnd].self, forKey: "ends") ?? [],
                            counter: try c.decodeIfPresent(Int.self, forKey: "counter"),
                            counterAt: try c.decodeIfPresent([Double].self, forKey: "counter_at"),
                            order: try c.decodeIfPresent(Int.self, forKey: "order"),
                            opens: try c.decodeIfPresent(ObstacleID.self, forKey: "opens"),
                            turn: try c.decodeIfPresent(CornerTurn.self, forKey: "turn"),
                            reveals: try c.decodeIfPresent([ArrowID].self, forKey: "reveals") ?? [],
                            sprite: try c.decodeIfPresent(String.self, forKey: "sprite"))
    }

    static func encode(_ o: ObstacleSpec, to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LevelKey.self)
        try c.encode(o.id, forKey: "id")
        try c.encode(o.kind, forKey: "kind")
        try c.encode(o.cells, forKey: "cells")
        if !o.arrows.isEmpty { try c.encode(o.arrows, forKey: "arrows") }
        if !o.ends.isEmpty { try c.encode(o.ends, forKey: "ends") }
        try c.encodeIfPresent(o.counter, forKey: "counter")
        try c.encodeIfPresent(o.counterAt, forKey: "counter_at")
        try c.encodeIfPresent(o.order, forKey: "order")
        try c.encodeIfPresent(o.opens, forKey: "opens")
        try c.encodeIfPresent(o.turn, forKey: "turn")
        if !o.reveals.isEmpty { try c.encode(o.reveals, forKey: "reveals") }
        try c.encodeIfPresent(o.sprite, forKey: "sprite")
    }

    // MARK: LevelMetrics

    static func decodeMetrics(from decoder: Decoder) throws -> LevelMetrics {
        let c = try decoder.container(keyedBy: LevelKey.self)
        return LevelMetrics(rounds: try c.decode(Int.self, forKey: "rounds"),
                            freeAtStart: try c.decode(Int.self, forKey: "free_at_start"),
                            arrows: try c.decode(Int.self, forKey: "arrows"),
                            cells: try c.decode(Int.self, forKey: "cells"),
                            meanLength: try c.decode(Double.self, forKey: "mean_length"),
                            botTimeLeft: try botTimeKey.flatMap { try c.decodeIfPresent(Double.self, forKey: LevelKey(stringLiteral: $0)) })
    }

    static func encode(_ m: LevelMetrics, to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LevelKey.self)
        try c.encode(m.rounds, forKey: "rounds")
        try c.encode(m.freeAtStart, forKey: "free_at_start")
        try c.encode(m.arrows, forKey: "arrows")
        try c.encode(m.cells, forKey: "cells")
        try c.encode(m.meanLength, forKey: "mean_length")
        if let k = botTimeKey { try c.encodeIfPresent(m.botTimeLeft, forKey: LevelKey(stringLiteral: k)) }
    }

    // MARK: SessionPlan

    static func decodeSession(from decoder: Decoder) throws -> SessionPlan {
        let c = try decoder.container(keyedBy: LevelKey.self)
        let levels = try c.decode([Int].self, forKey: "levels")
        guard !levels.isEmpty else {
            throw DecodingError.dataCorruptedError(forKey: "levels", in: c, debugDescription: "a session needs ≥ 1 level")
        }
        return SessionPlan(id: try c.decode(String.self, forKey: "id"),
                           levels: levels,
                           hudLabel: try c.decodeIfPresent(String.self, forKey: "hud_label"),
                           panelLabel: try c.decodeIfPresent(String.self, forKey: "panel_label"),
                           reward: try c.decodeIfPresent(Int.self, forKey: "reward"),
                           stageGap: try c.decodeIfPresent(Double.self, forKey: "stage_gap_s"),
                           hearts: try c.decodeIfPresent(HeartsCarry.self, forKey: "hearts") ?? .carry)
    }

    static func encode(_ s: SessionPlan, to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LevelKey.self)
        try c.encode(s.id, forKey: "id")
        try c.encode(s.levels, forKey: "levels")
        try c.encodeIfPresent(s.hudLabel, forKey: "hud_label")
        try c.encodeIfPresent(s.panelLabel, forKey: "panel_label")
        try c.encodeIfPresent(s.reward, forKey: "reward")
        try c.encodeIfPresent(s.stageGap, forKey: "stage_gap_s")
        try c.encode(s.hearts, forKey: "hearts")
    }
}

// MARK: - Public entry points

/// Which of the three schemas a level file uses. FIX-2 lane B (N-01): the two research schemas exist in the macOS content
/// tools only (PC_RESEARCH); the app reads the bundle schema.
public enum LevelSchema: String, Sendable, CaseIterable, Codable {
    case bundle     // App/Resources/Levels (has "schema")
    #if PC_RESEARCH
    case phone      // research/levels (source "recorded")
    case video      // research/video-frames/work/extract (source "video")
    #endif
}

public enum LevelJSONError: Error, CustomStringConvertible, Equatable {
    case notAnObject
    case missing(String)
    case badValue(String)
    case unknownSchema

    public var description: String {
        switch self {
        case .notAnObject: return "level JSON is not an object"
        case .missing(let k): return "level JSON: required key \(k) missing"
        case .badValue(let s): return "level JSON: \(s)"
        case .unknownSchema: return "level JSON: unknown schema"            // FIX-2 B (N-01): no research vocabulary
        }
    }
}

/// What an import or an inspection found beside the model: nothing is dropped silently (§4.3).
public struct ImportReport: Sendable, Equatable, CustomStringConvertible {
    public var schema: LevelSchema
    /// Key paths the reader does not know at all (e.g. "obstacles[].shape"). Never applied.
    public var unknownKeys: [String] = []
    /// Research-only key paths dropped on purpose (bbox_px, mean_rgb, anomalies, reader, fit_px, verify, …).
    public var droppedKeys: [String] = []
    /// Obstacle blobs not carried into the model, as "kind ×count" (box_part rings/bolts, unknown blobs, …).
    public var droppedObstacles: [String] = []
    /// Anything the mapping had to guess or could not map (counters missing, door splits, pipes without ends, …).
    public var warnings: [String] = []
    /// `reveals` file names the phone JSON lists (the Lnnn-openK.json states to merge).
    public var revealFiles: [String] = []

    public init(schema: LevelSchema) { self.schema = schema }

    public var isClean: Bool { unknownKeys.isEmpty && warnings.isEmpty }

    public var description: String {
        var s = "schema \(schema.rawValue)"
        if !unknownKeys.isEmpty { s += "; UNKNOWN keys: " + unknownKeys.joined(separator: ", ") }
        if !droppedKeys.isEmpty { s += "; dropped: " + droppedKeys.joined(separator: ", ") }
        if !droppedObstacles.isEmpty { s += "; dropped obstacles: " + droppedObstacles.joined(separator: ", ") }
        if !warnings.isEmpty { s += "; warnings: " + warnings.joined(separator: " | ") }
        if !revealFiles.isEmpty { s += "; reveals: " + revealFiles.joined(separator: ", ") }
        return s
    }
}

/// A level read from any schema plus its report.
public struct ImportedLevel: Sendable, Equatable {
    public var level: LevelSpec
    public var report: ImportReport
    public init(level: LevelSpec, report: ImportReport) { self.level = level; self.report = report }
}

public enum LevelJSON {
    /// The bundle schema this build reads and writes.
    public static let bundleSchema = LevelCoding.bundleSchema

    #if PC_RESEARCH
    /// Which schema `data` uses (bundle: has "schema"; video: source "video" or a "video" key; phone: source "recorded"
    /// or the phone reader's keys). Research tools only (PC_RESEARCH).
    public static func schema(of data: Data) throws -> LevelSchema {
        guard let o = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LevelJSONError.notAnObject }
        return try schema(of: o)
    }

    static func schema(of o: [String: Any]) throws -> LevelSchema {
        if o["schema"] != nil { return .bundle }
        let source = o["source"] as? String
        if source == "video" || o["video"] != nil { return .video }
        if source == "recorded" || o["shot"] != nil || o["pitch_pt"] != nil { return .phone }
        if o["level"] != nil && o["arrows"] != nil { return .bundle }
        throw LevelJSONError.unknownSchema
    }
    #endif

    /// A bundle v1 file → the model (the ◆ Codable path).
    public static func decodeBundle(_ data: Data) throws -> LevelSpec {
        try JSONDecoder().decode(LevelSpec.self, from: data)
    }

    /// The canonical bundle bytes: sorted keys, no escaped slashes, compact, one trailing newline. `pclevels bundle`
    /// writes these, so the folder is reproducible byte for byte (L1 acceptance).
    public static func encodeBundle(_ level: LevelSpec) throws -> Data {
        var d = try canonicalEncoder().encode(level)
        d.append(0x0A)
        return d
    }

    /// FIX-2 lane B (N-01; PUBLISH B0, SPEC.md ruling 39 OD8): the SHIPPED form of a level — `encodeBundle`'s bytes without
    /// `source`, `capture` and `metrics` (the research trail: where a board was read from, and the bot's measurements). The
    /// runtime reads none of them; it decodes back as `publishModel(level)` (source .designed, no capture, no metrics).
    public static func encodePublish(_ level: LevelSpec) throws -> Data {
        let e = canonicalEncoder()
        e.userInfo[LevelCoding.publishForm] = true
        var d = try e.encode(level)
        d.append(0x0A)
        return d
    }

    /// What the publish bytes of `level` decode back to.
    public static func publishModel(_ level: LevelSpec) -> LevelSpec {
        var p = level
        p.source = .designed
        p.capture = nil
        p.metrics = nil
        return p
    }

    public static func canonicalEncoder() -> JSONEncoder {
        let e = JSONEncoder()
        e.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return e
    }

    /// Unknown-key report for a bundle file (the decoder itself ignores unknown keys).
    public static func inspectBundle(_ data: Data) throws -> ImportReport {
        guard let o = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LevelJSONError.notAnObject }
        var r = ImportReport(schema: .bundle)
        var unknown = Set<String>()
        func check(_ obj: [String: Any], _ known: Set<String>, _ path: String) {
            for k in obj.keys where !known.contains(k) && !k.hasPrefix("_") { unknown.insert(path + k) }
        }
        check(o, LevelCoding.levelKeys, "")
        for a in (o["arrows"] as? [[String: Any]]) ?? [] { check(a, LevelCoding.arrowKeys, "arrows[].") }
        for ob in (o["obstacles"] as? [[String: Any]]) ?? [] {
            check(ob, LevelCoding.obstacleKeys, "obstacles[].")
            for e in (ob["ends"] as? [[String: Any]]) ?? [] { check(e, LevelCoding.endKeys, "obstacles[].ends[].") }
        }
        if let m = o["metrics"] as? [String: Any] { check(m, LevelCoding.metricsKeys, "metrics.") }
        r.unknownKeys = unknown.sorted()
        return r
    }

    #if PC_RESEARCH
    /// Any schema → the model + report. Phone/video go through `LevelImport`; `reveals` (phone Lnnn-openK.json states,
    /// in order) are merged as hidden arrows under the doors they were revealed from.
    public static func load(_ data: Data, reveals: [Data] = []) throws -> ImportedLevel {
        guard let o = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LevelJSONError.notAnObject }
        switch try schema(of: o) {
        case .bundle:
            return ImportedLevel(level: try decodeBundle(data), report: try inspectBundle(data))
        case .phone, .video:
            let base = try LevelImport.research(o)
            guard !reveals.isEmpty else { return base }
            let states = try reveals.map { d -> ImportedLevel in
                guard let ro = try JSONSerialization.jsonObject(with: d) as? [String: Any] else { throw LevelJSONError.notAnObject }
                return try LevelImport.research(ro)
            }
            return LevelImport.mergeReveals(base: base, states: states)
        }
    }
    #endif

    // MARK: sessions.json

    /// `{"schema":1,"sessions":[…]}` (§4.3) or a bare array of sessions.
    public static func decodeSessions(_ data: Data) throws -> [SessionPlan] {
        let top = try JSONSerialization.jsonObject(with: data)
        if top is [Any] { return try JSONDecoder().decode([SessionPlan].self, from: data) }
        let wrapped = try JSONDecoder().decode(SessionsFile.self, from: data)
        if let s = wrapped.schema, s > bundleSchema { throw LevelJSONError.badValue("sessions schema \(s) is newer than \(bundleSchema)") }
        return wrapped.sessions
    }

    public static func encodeSessions(_ sessions: [SessionPlan]) throws -> Data {
        var d = try canonicalEncoder().encode(SessionsFile(schema: bundleSchema, sessions: sessions))
        d.append(0x0A)
        return d
    }

    struct SessionsFile: Codable {
        var schema: Int?
        var sessions: [SessionPlan]
    }
}
