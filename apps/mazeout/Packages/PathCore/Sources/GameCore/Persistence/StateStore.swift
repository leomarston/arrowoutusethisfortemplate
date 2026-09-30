import Foundation

// C3 (SPEC-architecture §4.12, D11). MF's StateStore (e10a076), renamed: `Application Support/Save/player.json`.
// - JSON with sorted keys and ISO-8601 UTC dates WITH the fraction of the second (3–9 digits, "2026-09-25T09:20:00.125Z"),
//   exact enough that a Date reads back identical (plain `.iso8601` drops the fraction and would shift every refill anchor
//   and ∞ end on each relaunch). Both forms decode.
// - ATOMIC writes (`.atomic`: a temp file renamed over the old one) after copying the previous GOOD file to
//   `player.prev.json` (through a temp copy + an atomic replace, so a failure half-way — a full disk — never leaves the store
//   without a readable file).
// - A file that fails to decode is kept once as `player.corrupt.json` (the latest bad copy) and is never rotated into the
//   backup; the backup loads, and failing that a fresh state. The problem is reported in `LoadResult.problem` (the app logs
//   it); nothing crashes.
// - `decode` goes through `Migrations` only when the save is older than the schema.
// - Rewind safety lives in the data, not in the file: `social.highWater` (the rewind-safe clock) is saved with everything
//   else, so a relaunch with the device clock set back still sees the latest time ever shown (`EconomyClock`).
// The app's `PlayerStore` (G1) wraps it: debounced saves on a utility queue, immediate at attempt start / finish / purchase /
// background.

public final class StateStore {
    public enum LoadSource: String, Sendable { case primary, backup, fresh }
    public struct LoadResult: Sendable {
        public var state: PlayerState
        public var source: LoadSource
        public var problem: String?
    }

    public let url: URL
    public var backupURL: URL { url.deletingLastPathComponent().appendingPathComponent("player.prev.json") }
    public var corruptURL: URL { url.deletingLastPathComponent().appendingPathComponent("player.corrupt.json") }

    /// true after a successful load or save, false after the file failed to decode, nil when not looked at yet (then
    /// `save` checks it before rotating it into the backup).
    private var primaryIsGood: Bool?

    public init(url: URL) { self.url = url }

    /// `Application Support/Save/player.json` (REUSE §1, confirmed §4.12).
    public static func defaultURL() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        return base.appendingPathComponent("Save", isDirectory: true).appendingPathComponent("player.json")
    }

    // MARK: coding

    public static func encoder() -> JSONEncoder {
        let e = JSONEncoder()
        e.outputFormatting = [.sortedKeys, .prettyPrinted]
        e.dateEncodingStrategy = .custom { date, enc in
            var c = enc.singleValueContainer()
            try c.encode(ISODate.string(date))
        }
        return e
    }

    public static func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { dec in
            let c = try dec.singleValueContainer()
            let s = try c.decode(String.self)
            guard let date = ISODate.date(s) else {
                throw DecodingError.dataCorruptedError(in: c, debugDescription: "not an ISO-8601 date: \(s)")
            }
            return date
        }
        return d
    }

    private struct VersionPeek: Decodable { var version: Int? }

    /// Decodes a save of any known version. Throws when the data is not a PlayerState JSON object.
    public static func decode(_ data: Data) throws -> PlayerState {
        let peek = try? JSONDecoder().decode(VersionPeek.self, from: data)
        if let v = peek?.version, v >= PlayerState.schemaVersion {
            return try decoder().decode(PlayerState.self, from: data)
        }
        let raw = try JSONSerialization.jsonObject(with: data)
        guard let obj = raw as? [String: Any] else { throw CocoaError(.fileReadCorruptFile) }
        let migrated = Migrations.upgrade(obj)
        return try decoder().decode(PlayerState.self, from: JSONSerialization.data(withJSONObject: migrated))
    }

    public static func encode(_ s: PlayerState) throws -> Data { try encoder().encode(s) }

    // MARK: load / save

    public func load() -> LoadResult {
        var problem: String?
        let fm = FileManager.default
        if let data = fm.contents(atPath: url.path) {
            do {
                let s = try Self.decode(data)
                primaryIsGood = true
                return LoadResult(state: s, source: .primary, problem: nil)
            } catch {
                primaryIsGood = false
                problem = "player.json unreadable (\(data.count) bytes): \(error)"
                try? fm.removeItem(at: corruptURL)
                try? fm.copyItem(at: url, to: corruptURL)
            }
        } else {
            primaryIsGood = nil
        }
        if let data = fm.contents(atPath: backupURL.path) {
            do {
                return LoadResult(state: try Self.decode(data), source: .backup, problem: problem)
            } catch {
                problem = (problem.map { $0 + "; " } ?? "") + "player.prev.json unreadable: \(error)"
            }
        }
        return LoadResult(state: PlayerState(), source: .fresh, problem: problem)
    }

    /// Rotates the current (good) file into the backup, then writes `s` atomically.
    public func save(_ s: PlayerState) throws {
        try write(Self.encode(s))
    }

    /// `save` with the bytes already encoded (the app encodes off the main thread).
    public func write(_ data: Data) throws {
        let fm = FileManager.default
        try fm.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        if fm.fileExists(atPath: url.path), primaryLooksGood() { rotateBackup() }
        try data.write(to: url, options: .atomic)
        primaryIsGood = true
    }

    /// `-pc.reset 1`: removes the save, its backup and any kept corrupt copy.
    public func wipe() {
        for u in [url, backupURL, corruptURL] { try? FileManager.default.removeItem(at: u) }
        primaryIsGood = nil
    }

    private func primaryLooksGood() -> Bool {
        if let known = primaryIsGood { return known }
        guard let data = FileManager.default.contents(atPath: url.path) else { return false }
        let ok = (try? Self.decode(data)) != nil
        primaryIsGood = ok
        return ok
    }

    /// player.json → temp copy → atomic replace of player.prev.json. On any failure the old backup stays.
    private func rotateBackup() {
        let fm = FileManager.default
        let tmp = url.deletingLastPathComponent().appendingPathComponent(".player.prev.\(UUID().uuidString).tmp")
        do {
            try fm.copyItem(at: url, to: tmp)
            if fm.fileExists(atPath: backupURL.path) {
                _ = try fm.replaceItemAt(backupURL, withItemAt: tmp)
            } else {
                try fm.moveItem(at: tmp, to: backupURL)
            }
        } catch {
            try? fm.removeItem(at: tmp)
        }
    }
}

/// ISO-8601 UTC with a decimal fraction of the second: at least 3 digits, up to 9 (nanoseconds), trailing zeros trimmed
/// ("2026-09-25T09:20:00.125Z"). Nine digits are finer than a Date's own resolution for any date after 2001-04, so a saved
/// date reads back as the identical Date and a save round-trips bit for bit. Reads with or without a fraction and with any
/// zone offset.
public enum ISODate {
    public static func string(_ d: Date) -> String {
        let t = d.timeIntervalSinceReferenceDate
        var whole = t.rounded(.down)
        var nanos = ((t - whole) * 1e9).rounded()                     // t - whole is exact (Sterbenz)
        if nanos >= 1e9 { whole += 1; nanos -= 1e9 }
        let base = plain().string(from: Date(timeIntervalSinceReferenceDate: whole))   // "2026-09-25T09:20:00Z"
        var digits = String(Int(nanos))
        digits = String(repeating: "0", count: max(0, 9 - digits.count)) + digits
        while digits.count > 3 && digits.hasSuffix("0") { digits.removeLast() }
        return String(base.dropLast()) + "." + digits + "Z"
    }

    public static func date(_ s: String) -> Date? {
        // Exact path for what `string` writes: "...:ssZ" or "...:ss.f...Z".
        if s.hasSuffix("Z"), let dot = s.lastIndex(of: ".") {
            let digits = s[s.index(after: dot)..<s.index(before: s.endIndex)]
            if !digits.isEmpty, digits.allSatisfy({ $0.isASCII && $0.isNumber }),
               let base = plain().date(from: String(s[..<dot]) + "Z"), let f = Double("0." + digits) {
                return Date(timeIntervalSinceReferenceDate: base.timeIntervalSinceReferenceDate + f)
            }
        }
        if let d = plain().date(from: s) { return d }
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: s)
    }

    private static func plain() -> ISO8601DateFormatter {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }
}
