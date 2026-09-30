import Foundation
import Observation
import PathCore

// WP0 → G1 (SPEC-architecture §3.2, §4.12, §8.6, §9.1). The app's single copy of `PlayerState`, owned by GAME from G1 on.
// Every mutation goes through `mutate` (`store.mutate { $0.coins -= 900 }`). Saves are debounced 0.3 s, and immediate with
// `saveNow()` / `mutateAndSave` (attempt start, finish, purchase, scenePhase .background); encoding and the atomic write run
// on a utility queue (≤ 1 ms main-thread cost, §10). No @AppStorage / UserDefaults for any state (D11).
//
// G1: the file format is C3's `StateStore` (§4.12: `Application Support/Save/player.json`, sorted keys, ISO-8601 dates with
// the fraction of the second, the previous GOOD file rotated to `player.prev.json`, a corrupt file kept once as
// `player.corrupt.json` and the backup — or a fresh state — loaded; never crashes). A fresh install is C3's
// `Economy.freshState` (start coins, booster stock 3/3, full lives from `EconomyRules`), and the lives launch arguments go
// through C3's `Economy.setLives` so the refill anchor follows the rules' interval (rules.json `lives.refillSeconds`).

@MainActor @Observable final class PlayerStore {
    enum LoadSource: String { case primary, backup, fresh, injected }

    private(set) var state: PlayerState
    /// Where the state came from at launch (boot log).
    let loadSource: LoadSource
    /// A problem found while loading (a corrupt file kept aside), for the boot log.
    let loadProblem: String?

    @ObservationIgnored let directory: URL
    @ObservationIgnored private var pendingSave: Task<Void, Never>?
    @ObservationIgnored private let debounce: Double
    @ObservationIgnored private let io = DispatchQueue(label: "com.manycode.arrowout.save", qos: .utility)
    /// C3's store: touched only on `io` after init (it keeps whether the primary file is good).
    @ObservationIgnored private let disk: DiskBox
    /// Saves issued / written (tests, the boot log).
    @ObservationIgnored private(set) var savesIssued = 0
    /// Whether the most recent write reached the disk. Touched only on `io`.
    @ObservationIgnored private let lastWrite = WriteResult()

    var fileURL: URL { disk.store.url }
    var backupURL: URL { disk.store.backupURL }
    var corruptURL: URL { disk.store.corruptURL }

    /// `Application Support/Save/` (§4.12).
    nonisolated static func defaultDirectory() -> URL { StateStore.defaultURL().deletingLastPathComponent() }

    /// Loads the save (or makes a fresh install), applies the §9.1 launch arguments and saves once.
    /// `homeSeenFromLevel`: `-pc.level N` marks home seen when N ≥ it (game.json ftue.chainUntilLevel, 7).
    /// `rules`: C3's economy table (the fresh state's coins / boosters / lives, the refill interval of `-pc.livesNextIn`).
    init(args: LaunchArgs, now: Date, bundle: Bundle = .main, directory: URL = PlayerStore.defaultDirectory(),
         homeSeenFromLevel: Int = 7, rules: EconomyRules = .default, debounce: Double = 0.3) {
        self.directory = directory
        self.debounce = debounce
        let store = StateStore(url: directory.appendingPathComponent("player.json"))
        disk = DiskBox(store)
        if args.reset {
            store.wipe()
            Log.mark("store", "-pc.reset 1: save wiped")
        }
        let loaded = store.load()
        var source: LoadSource
        var s: PlayerState
        switch loaded.source {
        case .primary: s = loaded.state; source = .primary
        case .backup: s = loaded.state; source = .backup
        case .fresh:
            s = Economy.freshState(installSeed: UInt64.random(in: 1...UInt64.max), installDate: now, rules: rules)
            source = .fresh
        }
        if let p = loaded.problem { Log.error("store", p) }
        if let injected = args.state.flatMap(Self.decodeInjected) { s = injected; source = .injected }
        Self.apply(args, to: &s, now: now, bundle: bundle, homeSeenFromLevel: homeSeenFromLevel, rules: rules)
        state = s
        loadSource = source
        loadProblem = loaded.problem
        do { try store.save(s) } catch { Log.error("store", "first save failed: \(error)") }
        Log.mark("store", "state \(source.rawValue): level \(s.level), coins \(s.coins), lives \(s.lives.count), "
                 + "boosters \(s.boosters.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: ",")), "
                 + "seed \(s.installSeed)")
    }

    @discardableResult
    func mutate<R>(_ body: (inout PlayerState) -> R) -> R {
        let r = body(&state)
        scheduleSave()
        return r
    }

    /// Mutates and writes at once (attempt start, finish, purchase).
    @discardableResult
    func mutateAndSave<R>(_ body: (inout PlayerState) -> R) -> R {
        let r = body(&state)
        saveNow()
        return r
    }

    /// Writes now (encoding and the atomic write off the main thread); `flush()` waits for the write.
    func saveNow() {
        pendingSave?.cancel(); pendingSave = nil
        savesIssued += 1
        let snapshot = state
        let disk = self.disk
        let lastWrite = self.lastWrite
        io.async {
            do { try disk.store.save(snapshot); lastWrite.ok = true } catch {
                lastWrite.ok = false
                Log.error("store", "save failed: \(error)")
            }
        }
    }

    /// Blocks until every queued write has finished (backgrounding, tests).
    func flush() { io.sync {} }

    /// A1 (additive, commented for GAME's review): waits WITHOUT blocking the main thread until every queued write has
    /// finished. The store pipeline finishes a StoreKit transaction only after its grant is on disk, so a kill can never
    /// leave a finished (never redelivered) transaction whose coins were still in memory.
    /// Returns whether the last queued write actually reached the disk (false: a write error, e.g. a full disk).
    @discardableResult
    func flushed() async -> Bool {
        let lastWrite = self.lastWrite
        return await withCheckedContinuation { (c: CheckedContinuation<Bool, Never>) in io.async { c.resume(returning: lastWrite.ok) } }
    }

    private func scheduleSave() {
        pendingSave?.cancel()
        let delay = debounce
        pendingSave = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            guard !Task.isCancelled else { return }
            self?.saveNow()
        }
    }

    // MARK: format (§4.12: C3's StateStore coding)

    nonisolated static func encode(_ s: PlayerState) throws -> Data { try StateStore.encode(s) }

    nonisolated static func decode(_ d: Data) throws -> PlayerState { try StateStore.decode(d) }

    // MARK: launch arguments (§9.1)

    /// `-pc.state <path | base64 JSON>`.
    static func decodeInjected(_ value: String) -> PlayerState? {
        let data: Data? = FileManager.default.fileExists(atPath: value)
            ? FileManager.default.contents(atPath: value)
            : Data(base64Encoded: value)
        guard let data, let s = try? decode(data) else {
            Log.error("store", "-pc.state could not be read")
            return nil
        }
        return s
    }

    static func apply(_ args: LaunchArgs, to s: inout PlayerState, now: Date, bundle: Bundle, homeSeenFromLevel: Int,
                      rules: EconomyRules) {
        if let seed = args.effectiveSeed { s.installSeed = seed }
        if let n = args.level { s.level = max(1, n); if n >= homeSeenFromLevel { s.homeSeen = true } }
        if let c = args.coins { s.coins = max(0, c) }
        if let n = args.lives {
            Economy.setLives(&s, count: min(max(0, n), rules.lives.max), nextIn: args.livesNextIn, now: now, rules: rules)
        }
        if let secs = args.unlimitedLives { s.unlimitedLivesUntil = secs > 0 ? now.addingTimeInterval(secs) : nil }
        for (k, v) in args.boosters { s.boosters[k] = max(0, v) }
        switch args.tutorials {
        case .skip?: s.tutorialsDone = bundleIDs(file: "tutorials", key: "id", bundle: bundle)
        case .force?: s.tutorialsDone = []
        case nil: break
        }
        switch args.unlocks {
        case .skip?: s.unlocksSeen = bundleIDs(file: "unlocks", key: "feature", bundle: bundle)
        case .force?: s.unlocksSeen = []
        case nil: break
        }
    }

    /// Every string value of `key` anywhere in `bundle/Levels/<file>.json` (the content ids to mark done / seen).
    static func bundleIDs(file: String, key: String, bundle: Bundle) -> Set<String> {
        guard let url = bundle.url(forResource: file, withExtension: "json", subdirectory: "Levels"),
              let data = try? Data(contentsOf: url),
              let root = try? JSONSerialization.jsonObject(with: data) else {
            Log.mark("store", "Levels/\(file).json not in the bundle: nothing to mark")
            return []
        }
        var out: Set<String> = []
        func walk(_ node: Any) {
            if let d = node as? [String: Any] {
                if let v = d[key] as? String { out.insert(v) }
                d.values.forEach(walk)
            } else if let a = node as? [Any] {
                a.forEach(walk)
            }
        }
        walk(root)
        return out
    }
}

/// C3's `StateStore` handed to the save queue: after init it is only ever used on that one serial queue.
private final class DiskBox: @unchecked Sendable {
    let store: StateStore
    init(_ store: StateStore) { self.store = store }
}

/// The result of the latest save, read and written only on PlayerStore's serial `io` queue.
private final class WriteResult: @unchecked Sendable {
    var ok = true
}
