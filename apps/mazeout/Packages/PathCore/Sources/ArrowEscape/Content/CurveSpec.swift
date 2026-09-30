import Foundation
import GameCore

// C4 (SPEC-architecture §4.14; SPEC-gameplay §14.3; CONSISTENCY L-5..L-11). The generator curve: design/levels.json
// "curve" (= design/tools/work/curve.json, fitted to the recorded L30-L83 by design/tools/build_levels.py) as a typed
// value. The runtime reads bundle/Levels/curve.json (CONTENT writes it with `pclevels bundle`); until then, and whenever
// that file is absent or unreadable, `CurveSpec.default` is the same curve compiled in (GeneratorTests pins it against
// design/levels.json byte for byte).

public struct CurveSpec: Sendable, Equatable {
    public struct Template: Sendable, Equatable {
        public var slot: Int
        public var pos: Int
        public var level: Int
        public var cols: Int
        public var rows: Int
        public var units: Int
        public var rounds: Int
        public var free: Int
        public var timer: Int
        public var tag: String
    }
    public struct Growth: Sendable, Equatable {
        public var from: Int
        public var perDecade: Double
        public var cap: Double
    }
    public struct Timers: Sendable, Equatable {
        public var hard: Int
        public var superHard: Int
        public var normal: Int
        public var short: Int
        public var pShort: Double
        public var maxWorkShareShort: Double
        /// `timers.fromTemplate` (recast 2026-09-25; absent = false): every level's timer is its target template's recorded
        /// timer, whatever its tag (gen_levels.timer_for; no random draw is made).
        public var fromTemplate: Bool
    }
    public struct Silhouette: Sendable, Equatable {
        public var p: Double
        public var shapes: [String]
    }
    public struct Obstacles: Sendable, Equatable {
        public var firstLevel: [String: Int]
        public var kindOrder: [String]
        public var kindWeights: [String: Int]
        public var countWeights: [Int]
    }

    public var schema: Int
    public var salt: UInt64
    public var authoredEnd: Int
    public var cycle: Int
    /// Decade slots the templates rotate through (`slots`, absent = 3): target slot = floor(n / 10) mod slots.
    public var slots: Int
    public var tagByPosition: [Int: String]
    public var templates: [Template]
    public var growth: Growth
    public var maxCols: Int
    public var maxRows: Int
    public var timers: Timers
    /// (length, count) sorted by length (the recorded histogram, `curve.lengths`).
    public var lengths: [(length: Int, count: Int)]
    public var straight: Double
    public var maxLength: Int
    public var mergeFactor: Int
    public var flipSteps: Int
    public var silhouette: Silhouette
    public var obstacles: Obstacles
    public var attempts: Int
    public var goodEnough: Double
    /// The curve exactly as read (canonical bytes; what `pclevels bundle` writes as curve.json).
    public var json: JSONValue

    public static func == (a: CurveSpec, b: CurveSpec) -> Bool { a.json == b.json }

    public enum DecodeError: Error, CustomStringConvertible, Equatable {
        case missing(String)
        public var description: String { switch self { case .missing(let k): return "curve: key \(k) missing or of the wrong type" } }
    }

    /// Decodes curve JSON (the object itself, as in levels.json "curve" or bundle/Levels/curve.json).
    public init(json v: JSONValue) throws {
        func obj(_ o: JSONValue?, _ k: String) throws -> JSONValue {
            guard let x = o?[k], x.objectPairs != nil else { throw DecodeError.missing(k) }
            return x
        }
        func int(_ o: JSONValue?, _ k: String) throws -> Int {
            guard let x = o?[k]?.intValue else { throw DecodeError.missing(k) }
            return x
        }
        func dbl(_ o: JSONValue?, _ k: String) throws -> Double {
            guard let x = o?[k]?.doubleValue else { throw DecodeError.missing(k) }
            return x
        }
        func arr(_ o: JSONValue?, _ k: String) throws -> [JSONValue] {
            guard let x = o?[k]?.arrayValue else { throw DecodeError.missing(k) }
            return x
        }
        json = v
        schema = (v["schema"]?.intValue) ?? 1
        guard let s = v["salt"]?.uint64Value else { throw DecodeError.missing("salt") }
        salt = s
        authoredEnd = try int(v, "authoredEnd")
        cycle = (v["cycle"]?.intValue) ?? 10
        slots = (v["slots"]?.intValue) ?? 3                   // gen_levels.target_for: curve.get('slots', 3)
        var tbp: [Int: String] = [:]
        for (k, x) in (v["tagByPosition"]?.objectPairs ?? []) { if let p = Int(k), let t = x.stringValue { tbp[p] = t } }
        tagByPosition = tbp
        templates = try arr(v, "templates").map { t in
            Template(slot: try int(t, "slot"), pos: try int(t, "pos"), level: try int(t, "level"), cols: try int(t, "cols"),
                     rows: try int(t, "rows"), units: try int(t, "units"), rounds: try int(t, "rounds"),
                     free: try int(t, "free"), timer: try int(t, "timer"), tag: t["tag"]?.stringValue ?? "normal")
        }
        let g = try obj(v, "growth")
        growth = Growth(from: try int(g, "from"), perDecade: try dbl(g, "perDecade"), cap: try dbl(g, "cap"))
        maxCols = try int(v, "maxCols")
        maxRows = try int(v, "maxRows")
        let t = try obj(v, "timers")
        timers = Timers(hard: try int(t, "hard"), superHard: try int(t, "superHard"), normal: try int(t, "normal"),
                        short: try int(t, "short"), pShort: try dbl(t, "pShort"),
                        maxWorkShareShort: try dbl(t, "maxWorkShareShort"),
                        fromTemplate: t["fromTemplate"]?.isTruthy ?? false)    // timer_for: t.get('fromTemplate')
        var lens: [(length: Int, count: Int)] = []
        for (k, x) in (try obj(v, "lengths")).objectPairs! {
            guard let n = Int(k), let c = x.intValue else { throw DecodeError.missing("lengths.\(k)") }
            lens.append((n, c))
        }
        lengths = lens.sorted { $0.length < $1.length }
        straight = try dbl(v, "straight")
        maxLength = try int(v, "maxLength")
        mergeFactor = try int(v, "mergeFactor")
        flipSteps = try int(v, "flipSteps")
        let sil = try obj(v, "silhouette")
        silhouette = Silhouette(p: try dbl(sil, "p"), shapes: try arr(sil, "shapes").compactMap(\.stringValue))
        let ob = try obj(v, "obstacles")
        var fl: [String: Int] = [:]
        for (k, x) in (try obj(ob, "firstLevel")).objectPairs! { fl[k] = x.intValue }
        var kw: [String: Int] = [:]
        for (k, x) in (try obj(ob, "kindWeights")).objectPairs! { kw[k] = x.intValue }
        obstacles = Obstacles(firstLevel: fl, kindOrder: try arr(ob, "kindOrder").compactMap(\.stringValue), kindWeights: kw,
                              countWeights: try arr(ob, "countWeights").compactMap(\.intValue))
        attempts = try int(v, "attempts")
        goodEnough = try dbl(v, "goodEnough")
    }

    public init(data: Data) throws { try self.init(json: try ContentJSON.parse(data)) }

    /// The template for cycle position `pos` and decade slot `slot` (SPEC-gameplay §14.3 step 1).
    public func template(pos: Int, slot: Int) -> Template? { templates.first { $0.pos == pos && $0.slot == slot } }

    /// The compiled-in curve (design/levels.json "curve": content recast 2's fit of 2026-09-25 — templates L30-L99 in 7
    /// decade slots, growth from L100, template timers, corners and elevators in the obstacle mix).
    public static let `default`: CurveSpec = {
        do { return try CurveSpec(data: Data(defaultJSON.replacingOccurrences(of: "\n", with: "").utf8)) }
        catch { fatalError("CurveSpec.default does not decode: \(error)") }
    }()

    /// `design/levels.json` "curve", canonical (sorted keys, compact), wrapped at commas for reading (newlines removed
    /// before parsing).
    static let defaultJSON = #"""
{"_about":"Generator curve (SPEC-gameplay \u00a714.3). Fitted to L30-L105 by design/tools/build_levels.py (templates L30-L99 in 7 decade slots; timers from the templates; obstacle mix of L40-L105 incl. corners and elevators; growth from L100); the designed L106-L150 and every endless level past the authored end come from it (gen_levels.py = the reference algorithm C4 ports).",
"attempts":10,"authoredEnd":150,"cycle":10,"flipSteps":3000,"goodEnough":0.25,"growth":{"cap":1.25,"from":100,
"perDecade":0.02},"lengths":{"10":142,"11":120,"118":1,"12":108,"13":83,"14":45,"15":44,"16":40,"17":31,"18":28,
"19":18,"2":197,"20":29,"21":24,"22":38,"23":20,"24":27,"25":21,"26":15,"27":11,"28":14,"29":16,"3":659,"30":14,
"31":11,"32":3,"33":6,"34":6,"35":5,"36":7,"37":27,"38":17,"39":18,"4":814,"40":22,"41":17,"42":16,"43":9,"44":13,
"45":7,"46":4,"47":2,"48":2,"49":1,"5":285,"52":1,"53":1,"59":1,"6":432,"65":3,"66":3,"67":1,"68":2,"7":213,"72":2,
"73":2,"75":1,"8":253,"80":1,"81":1,"9":150},"maxCols":26,"maxLength":60,"maxRows":36,"mergeFactor":80,
"obstacles":{"countWeights":[26,36,38],"firstLevel":{"box":11,"corner":70,"door":33,"elevator":31,"pipe":21,"tape":7},
"kindOrder":["door","pipe","box","tape","elevator","corner"],"kindWeights":{"box":21,"corner":36,"door":27,
"elevator":6,"pipe":23,"tape":17}},"salt":15177990143040770677,"schema":1,"silhouette":{"p":0.25,"shapes":["oval",
"octagon","notch","blocks","cross","heart","diamond","arch"]},"slots":7,"straight":0.82,"tagByPosition":{"4":"hard",
"9":"superHard"},"templates":[{"cols":16,"free":9,"level":30,"pos":0,"rounds":7,"rows":16,"slot":0,"tag":"normal",
"timer":180,"units":25},{"cols":16,"free":8,"level":31,"pos":1,"rounds":12,"rows":17,"slot":0,"tag":"normal",
"timer":180,"units":35},{"cols":20,"free":10,"level":32,"pos":2,"rounds":12,"rows":20,"slot":0,"tag":"normal",
"timer":180,"units":41},{"cols":20,"free":2,"level":33,"pos":3,"rounds":23,"rows":20,"slot":0,"tag":"normal",
"timer":180,"units":50},{"cols":25,"free":5,"level":34,"pos":4,"rounds":42,"rows":35,"slot":0,"tag":"hard",
"timer":210,"units":116},{"cols":12,"free":1,"level":35,"pos":5,"rounds":10,"rows":18,"slot":0,"tag":"normal",
"timer":180,"units":20},{"cols":16,"free":8,"level":36,"pos":6,"rounds":14,"rows":23,"slot":0,"tag":"normal",
"timer":180,"units":31},{"cols":22,"free":5,"level":37,"pos":7,"rounds":23,"rows":30,"slot":0,"tag":"normal",
"timer":180,"units":49},{"cols":20,"free":6,"level":38,"pos":8,"rounds":15,"rows":22,"slot":0,"tag":"normal",
"timer":180,"units":39},{"cols":24,"free":10,"level":39,"pos":9,"rounds":38,"rows":34,"slot":0,"tag":"superHard",
"timer":180,"units":102},{"cols":20,"free":8,"level":40,"pos":0,"rounds":13,"rows":27,"slot":1,"tag":"normal",
"timer":150,"units":42},{"cols":20,"free":8,"level":41,"pos":1,"rounds":19,"rows":26,"slot":1,"tag":"normal",
"timer":150,"units":48},{"cols":22,"free":10,"level":42,"pos":2,"rounds":23,"rows":30,"slot":1,"tag":"normal",
"timer":180,"units":45},{"cols":20,"free":1,"level":43,"pos":3,"rounds":19,"rows":32,"slot":1,"tag":"normal",
"timer":180,"units":59},{"cols":25,"free":6,"level":44,"pos":4,"rounds":33,"rows":36,"slot":1,"tag":"hard",
"timer":180,"units":83},{"cols":15,"free":4,"level":45,"pos":5,"rounds":12,"rows":19,"slot":1,"tag":"normal",
"timer":150,"units":26},{"cols":24,"free":13,"level":46,"pos":6,"rounds":37,"rows":32,"slot":1,"tag":"normal",
"timer":180,"units":102},{"cols":20,"free":3,"level":47,"pos":7,"rounds":18,"rows":30,"slot":1,"tag":"normal",
"timer":180,"units":55},{"cols":20,"free":6,"level":48,"pos":8,"rounds":20,"rows":24,"slot":1,"tag":"normal",
"timer":150,"units":47},{"cols":24,"free":12,"level":49,"pos":9,"rounds":30,"rows":36,"slot":1,"tag":"superHard",
"timer":150,"units":69},{"cols":10,"free":2,"level":50,"pos":0,"rounds":9,"rows":18,"slot":2,"tag":"normal",
"timer":180,"units":16},{"cols":15,"free":4,"level":51,"pos":1,"rounds":10,"rows":21,"slot":2,"tag":"normal",
"timer":180,"units":24},{"cols":13,"free":5,"level":52,"pos":2,"rounds":5,"rows":16,"slot":2,"tag":"normal",
"timer":180,"units":15},{"cols":20,"free":6,"level":53,"pos":3,"rounds":24,"rows":30,"slot":2,"tag":"normal",
"timer":150,"units":61},{"cols":26,"free":16,"level":54,"pos":4,"rounds":44,"rows":34,"slot":2,"tag":"hard",
"timer":180,"units":102},{"cols":20,"free":6,"level":55,"pos":5,"rounds":22,"rows":27,"slot":2,"tag":"normal",
"timer":150,"units":48},{"cols":24,"free":10,"level":56,"pos":6,"rounds":23,"rows":32,"slot":2,"tag":"normal",
"timer":180,"units":60},{"cols":20,"free":13,"level":57,"pos":7,"rounds":13,"rows":24,"slot":2,"tag":"normal",
"timer":180,"units":38},{"cols":22,"free":5,"level":58,"pos":8,"rounds":26,"rows":24,"slot":2,"tag":"normal",
"timer":150,"units":61},{"cols":26,"free":16,"level":59,"pos":9,"rounds":34,"rows":34,"slot":2,"tag":"superHard",
"timer":120,"units":85},{"cols":20,"free":5,"level":60,"pos":0,"rounds":7,"rows":20,"slot":3,"tag":"normal",
"timer":180,"units":34},{"cols":20,"free":6,"level":61,"pos":1,"rounds":9,"rows":20,"slot":3,"tag":"normal",
"timer":150,"units":35},{"cols":26,"free":11,"level":62,"pos":2,"rounds":30,"rows":34,"slot":3,"tag":"normal",
"timer":180,"units":72},{"cols":22,"free":9,"level":63,"pos":3,"rounds":25,"rows":28,"slot":3,"tag":"normal",
"timer":150,"units":60},{"cols":24,"free":13,"level":64,"pos":4,"rounds":33,"rows":30,"slot":3,"tag":"hard",
"timer":100,"units":75},{"cols":26,"free":6,"level":65,"pos":5,"rounds":21,"rows":34,"slot":3,"tag":"normal",
"timer":180,"units":65},{"cols":20,"free":5,"level":66,"pos":6,"rounds":12,"rows":20,"slot":3,"tag":"normal",
"timer":150,"units":25},{"cols":20,"free":4,"level":67,"pos":7,"rounds":16,"rows":20,"slot":3,"tag":"normal",
"timer":150,"units":37},{"cols":20,"free":8,"level":68,"pos":8,"rounds":19,"rows":31,"slot":3,"tag":"normal",
"timer":180,"units":50},{"cols":26,"free":9,"level":69,"pos":9,"rounds":36,"rows":34,"slot":3,"tag":"superHard",
"timer":120,"units":99},{"cols":17,"free":7,"level":70,"pos":0,"rounds":6,"rows":18,"slot":4,"tag":"normal",
"timer":180,"units":22},{"cols":18,"free":2,"level":71,"pos":1,"rounds":11,"rows":18,"slot":4,"tag":"normal",
"timer":180,"units":25},{"cols":13,"free":5,"level":72,"pos":2,"rounds":5,"rows":16,"slot":4,"tag":"normal",
"timer":180,"units":15},{"cols":20,"free":9,"level":73,"pos":3,"rounds":19,"rows":26,"slot":4,"tag":"normal",
"timer":150,"units":61},{"cols":26,"free":13,"level":74,"pos":4,"rounds":43,"rows":36,"slot":4,"tag":"hard",
"timer":180,"units":113},{"cols":20,"free":6,"level":75,"pos":5,"rounds":22,"rows":27,"slot":4,"tag":"normal",
"timer":150,"units":48},{"cols":24,"free":6,"level":76,"pos":6,"rounds":18,"rows":26,"slot":4,"tag":"normal",
"timer":180,"units":56},{"cols":20,"free":13,"level":77,"pos":7,"rounds":13,"rows":24,"slot":4,"tag":"normal",
"timer":180,"units":38},{"cols":18,"free":8,"level":78,"pos":8,"rounds":15,"rows":28,"slot":4,"tag":"normal",
"timer":180,"units":37},{"cols":24,"free":14,"level":79,"pos":9,"rounds":28,"rows":30,"slot":4,"tag":"superHard",
"timer":180,"units":74},{"cols":22,"free":6,"level":80,"pos":0,"rounds":18,"rows":24,"slot":5,"tag":"normal",
"timer":180,"units":42},{"cols":20,"free":6,"level":81,"pos":1,"rounds":9,"rows":20,"slot":5,"tag":"normal",
"timer":150,"units":35},{"cols":21,"free":10,"level":82,"pos":2,"rounds":27,"rows":29,"slot":5,"tag":"normal",
"timer":150,"units":60},{"cols":22,"free":9,"level":83,"pos":3,"rounds":25,"rows":28,"slot":5,"tag":"normal",
"timer":150,"units":60},{"cols":26,"free":15,"level":84,"pos":4,"rounds":44,"rows":33,"slot":5,"tag":"hard",
"timer":120,"units":87},{"cols":20,"free":6,"level":85,"pos":5,"rounds":14,"rows":26,"slot":5,"tag":"normal",
"timer":150,"units":45},{"cols":20,"free":5,"level":86,"pos":6,"rounds":12,"rows":20,"slot":5,"tag":"normal",
"timer":150,"units":25},{"cols":18,"free":7,"level":87,"pos":7,"rounds":23,"rows":26,"slot":5,"tag":"normal",
"timer":180,"units":43},{"cols":24,"free":9,"level":88,"pos":8,"rounds":21,"rows":30,"slot":5,"tag":"normal",
"timer":150,"units":68},{"cols":26,"free":9,"level":89,"pos":9,"rounds":36,"rows":36,"slot":5,"tag":"superHard",
"timer":150,"units":99},{"cols":20,"free":5,"level":90,"pos":0,"rounds":14,"rows":20,"slot":6,"tag":"normal",
"timer":150,"units":33},{"cols":20,"free":6,"level":91,"pos":1,"rounds":18,"rows":20,"slot":6,"tag":"normal",
"timer":150,"units":38},{"cols":18,"free":4,"level":92,"pos":2,"rounds":19,"rows":22,"slot":6,"tag":"normal",
"timer":150,"units":40},{"cols":21,"free":7,"level":93,"pos":3,"rounds":19,"rows":26,"slot":6,"tag":"normal",
"timer":150,"units":64},{"cols":26,"free":13,"level":94,"pos":4,"rounds":38,"rows":36,"slot":6,"tag":"hard",
"timer":150,"units":104},{"cols":20,"free":6,"level":95,"pos":5,"rounds":14,"rows":26,"slot":6,"tag":"normal",
"timer":150,"units":41},{"cols":20,"free":5,"level":96,"pos":6,"rounds":12,"rows":22,"slot":6,"tag":"normal",
"timer":150,"units":32},{"cols":22,"free":6,"level":97,"pos":7,"rounds":25,"rows":26,"slot":6,"tag":"normal",
"timer":150,"units":48},{"cols":24,"free":7,"level":98,"pos":8,"rounds":31,"rows":30,"slot":6,"tag":"normal",
"timer":150,"units":74},{"cols":26,"free":17,"level":99,"pos":9,"rounds":25,"rows":32,"slot":6,"tag":"superHard",
"timer":180,"units":85}],"timers":{"fromTemplate":true,"hard":180,"maxWorkShareShort":0.4,"normal":180,"pShort":0.47,
"short":150,"superHard":150}}
"""#
}

extension LevelLibrary {
    /// The generator curve of this content: bundle/Levels/curve.json when present and valid, else `CurveSpec.default`.
    public var curve: CurveSpec {
        guard let d = curveJSON, let c = try? CurveSpec(data: d) else { return .default }
        return c
    }
}
