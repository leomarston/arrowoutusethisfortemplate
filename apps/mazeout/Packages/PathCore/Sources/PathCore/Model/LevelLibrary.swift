import Foundation

// C1 (SPEC-architecture §4.3, §8.5 boot step 2). The authored content in bundle/Levels/: level_NNNN.json (bundle v1),
// sessions.json, unlocks.json, tutorials.json, curve.json.
//
// `load(folder:)` reads the index and the small files at boot and decodes LEVELS LAZILY (first `authored(n)`, cached,
// thread-safe): 100+ level files are never parsed on the launch path (FEEL: no first-launch stall, §10).
// `curve`: CurveSpec is C4's type (Content/CurveSpec.swift, not written yet). The library keeps the raw `curveJSON` and
// C4 adds `extension LevelLibrary { public var curve: CurveSpec }` in its own file (C1 → C4 request).

public struct LevelLibrary: Sendable {
    /// The largest n such that level_0001 … level_n all exist (the authored end; `LevelProvider` generates past it).
    public let authoredCount: Int
    public let sessions: [SessionPlan]
    public let unlocks: [FeatureUnlock]
    public let tutorials: [TutorialScript]
    /// Levels/curve.json as read (C4 decodes it into `CurveSpec`); nil when the file is absent.
    public let curveJSON: Data?
    /// Level number → file (bundle folder), for every level_NNNN.json present.
    public let files: [Int: URL]
    /// Content problems found at load (gaps in the numbering, a level in two sessions, a session of missing levels,
    /// an unlock or tutorial for a missing level). Empty for sound content; LevelLibraryTests (C4) assert it.
    public let problems: [String]

    private let cache: LevelCache

    public enum LoadError: Error, CustomStringConvertible, Equatable {
        case folderMissing(String)
        case file(String, String)
        case mismatch(String)
        public var description: String {
            switch self {
            case .folderMissing(let p): return "LevelLibrary: no levels folder at \(p)"
            case .file(let f, let e): return "LevelLibrary: \(f): \(e)"
            case .mismatch(let s): return "LevelLibrary: \(s)"
            }
        }
    }

    /// Reads the folder's index and small files; level files decode on first use.
    public static func load(folder: URL) throws -> LevelLibrary {
        let fm = FileManager.default
        var isDir: ObjCBool = false
        guard fm.fileExists(atPath: folder.path, isDirectory: &isDir), isDir.boolValue else {
            throw LoadError.folderMissing(folder.path)
        }
        var files: [Int: URL] = [:]
        for name in try fm.contentsOfDirectory(atPath: folder.path) {
            guard let n = levelNumber(fileName: name) else { continue }
            files[n] = folder.appendingPathComponent(name)
        }
        func read(_ name: String) throws -> Data? {
            let url = folder.appendingPathComponent(name)
            guard fm.fileExists(atPath: url.path) else { return nil }
            do { return try Data(contentsOf: url) } catch { throw LoadError.file(name, String(describing: error)) }
        }
        func decode<T>(_ name: String, _ f: (Data) throws -> T) throws -> T? {
            guard let d = try read(name) else { return nil }
            do { return try f(d) } catch { throw LoadError.file(name, String(describing: error)) }
        }
        let sessions = try decode("sessions.json", LevelJSON.decodeSessions) ?? []
        let unlocks = try decode("unlocks.json", FeatureUnlock.decodeList) ?? []
        let tutorials = try decode("tutorials.json", TutorialScript.decodeList) ?? []
        let curve = try read("curve.json")
        return LevelLibrary(files: files, levels: [:], sessions: sessions, unlocks: unlocks, tutorials: tutorials,
                            curveJSON: curve)
    }

    /// An in-memory library (tests, the generator's scratch runs, `pclevels`).
    public init(levels: [LevelSpec], sessions: [SessionPlan] = [], unlocks: [FeatureUnlock] = [],
                tutorials: [TutorialScript] = [], curveJSON: Data? = nil) {
        var byNumber: [Int: LevelSpec] = [:]
        for l in levels where byNumber[l.level] == nil { byNumber[l.level] = l }
        self.init(files: [:], levels: byNumber, sessions: sessions, unlocks: unlocks, tutorials: tutorials, curveJSON: curveJSON)
    }

    private init(files: [Int: URL], levels: [Int: LevelSpec], sessions: [SessionPlan], unlocks: [FeatureUnlock],
                 tutorials: [TutorialScript], curveJSON: Data?) {
        self.files = files
        self.sessions = sessions
        self.unlocks = unlocks
        self.tutorials = tutorials
        self.curveJSON = curveJSON
        self.cache = LevelCache(levels)
        let present = Set(files.keys).union(levels.keys)
        var n = 0
        while present.contains(n + 1) { n += 1 }
        authoredCount = n
        var problems: [String] = []
        if let top = present.max(), top > n {
            let missing = (1...top).filter { !present.contains($0) }
            problems.append("levels missing below \(top): \(missing.map(String.init).joined(separator: ", "))")
        }
        var owner: [Int: String] = [:]
        for s in sessions {
            for l in s.levels {
                if let o = owner[l] { problems.append("level \(l) is in sessions \(o) and \(s.id)") } else { owner[l] = s.id }
                if !present.contains(l) { problems.append("session \(s.id) lists level \(l), which has no file") }
            }
            if s.levels != Array((s.levels.first ?? 0)..<((s.levels.first ?? 0) + s.levels.count)) {
                problems.append("session \(s.id) levels \(s.levels) are not consecutive")
            }
        }
        for u in unlocks where !present.contains(u.level) { problems.append("unlock \(u.feature) at level \(u.level), which has no file") }
        for t in tutorials where !present.contains(t.level) { problems.append("tutorial \(t.id) at level \(t.level), which has no file") }
        self.problems = problems
    }

    /// "level_0001.json" → 1 (any digit count after "level_").
    public static func levelNumber(fileName: String) -> Int? {
        guard fileName.hasPrefix("level_"), fileName.hasSuffix(".json") else { return nil }
        let digits = fileName.dropFirst("level_".count).dropLast(".json".count)
        guard !digits.isEmpty, digits.allSatisfy(\.isASCII), digits.allSatisfy(\.isNumber) else { return nil }
        return Int(digits)
    }

    /// The bundle file name of a level ("level_0007.json").
    public static func fileName(level: Int) -> String { String(format: "level_%04d.json", level) }

    /// The session a level is played in: its sessions.json entry, else a one-stage session "L<n>".
    public func session(containing level: Int) -> SessionPlan {
        sessions.first { $0.levels.contains(level) } ?? SessionPlan(id: "L\(level)", levels: [level])
    }

    /// The level after a session (its last + 1).
    public func nextLevel(after session: SessionPlan) -> Int { (session.levels.max() ?? 0) + 1 }

    /// The authored level, decoded on first use and cached; nil if absent or undecodable (see `loadAuthored`).
    public func authored(_ level: Int) -> LevelSpec? { try? loadAuthored(level) }

    /// Like `authored`, with the reason when it fails.
    public func loadAuthored(_ level: Int) throws -> LevelSpec {
        if let l = cache.get(level) { return l }
        guard let url = files[level] else { throw LoadError.mismatch("no file for level \(level)") }
        let spec: LevelSpec
        do { spec = try LevelJSON.decodeBundle(Data(contentsOf: url)) } catch {
            throw LoadError.file(url.lastPathComponent, String(describing: error))
        }
        guard spec.level == level else {
            throw LoadError.mismatch("\(url.lastPathComponent) holds level \(spec.level)")
        }
        cache.set(level, spec)
        return spec
    }

    /// The unlock whose overlay the first Play of `level` shows.
    public func unlock(at level: Int) -> FeatureUnlock? { unlocks.first { $0.level == level } }

    /// The tutorial steps of one board.
    public func tutorials(level: Int, stage: Int? = nil) -> [TutorialScript] {
        tutorials.filter { $0.level == level && (stage == nil || $0.stage == stage) }
    }
}

/// The lazily filled level cache (a class so the library stays a value; guarded by a lock → safe from any thread).
final class LevelCache: @unchecked Sendable {
    private var levels: [Int: LevelSpec]
    private let lock = NSLock()
    init(_ levels: [Int: LevelSpec]) { self.levels = levels }
    func get(_ n: Int) -> LevelSpec? { lock.lock(); defer { lock.unlock() }; return levels[n] }
    func set(_ n: Int, _ l: LevelSpec) { lock.lock(); levels[n] = l; lock.unlock() }
}
