import Foundation
import PathCore
import SortPuzzle

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §6b): SortPuzzle's module, app half. Compiled into every build, active
// only when `ActivePuzzle.entry` names `SortPuzzleEntry` (the `PC_PUZZLE_SORT` compilation condition flips that one line).
//  - `SortPuzzlePlugin`: the stages (the seeded generator, or an injected level source), the session over the rules.json
//    meta rules + sort.json (the module's `stuck` chain where rules.json has none), no tutorials or unlock cards yet (they
//    are content: strings + a tutorials file, docs/TEMPLATE.md), the bot's deliberate mistake, the headless warm-up win;
//  - `SortPuzzleBoard` (SortPuzzleBoard.swift): the board;
//  - `SortPuzzleEntry`: what `ActivePuzzle.entry` names.

@MainActor final class SortPuzzlePlugin: PuzzlePlugin {
    let rules: SortRules
    /// rules.json's meta half (rewards, the fail chains of every kind it lists).
    let meta: MetaRules
    private let level: @MainActor (Int) -> SortLevel?
    let tutorials: [TutorialStep] = []
    let unlocks: [FeatureUnlock] = []

    /// `level` = the level source (nil: the seeded generator over `rules`, the same board for every player).
    init(rules: SortRules, meta: MetaRules, level: (@MainActor (Int) -> SortLevel?)? = nil) {
        self.rules = rules
        self.meta = meta
        if let level {
            self.level = level
        } else {
            self.level = { n in n >= 1 ? SortPuzzleModule.level(n, rules: rules) : nil }
        }
    }

    var id: String { SortPuzzleModule.id }
    var capabilities: PuzzleCapabilities { SortPuzzleModule.capabilities }

    /// sort.json from the bundle (+ `-pc.tune sort.*` for the board's numbers); its problems are logged, the defaults apply.
    static func loadRules(_ file: TuningFile) -> SortRules {
        let (rules, problems) = SortRules.load(json: file.data)
        for p in problems { Log.error("tuning", p) }
        return rules
    }

    func stages(for plan: SessionPlan, args: LaunchArgs) -> [PuzzleStage]? {
        var stages: [PuzzleStage] = []
        for n in plan.levels {
            guard let l = level(n) else {
                Log.error("game", "L\(n) is not available (sort levels): the Play is refused")
                return nil
            }
            stages.append(SortPuzzleModule.stage(l))
        }
        return stages
    }

    func makeSession(plan: SessionPlan, stages: [PuzzleStage], setup: AttemptSetup, streakActive: Bool) -> any PuzzleSession {
        let levels = stages.compactMap { $0.content as? SortLevel }
        precondition(levels.count == stages.count && !levels.isEmpty, "SortPuzzle stages carry SortLevels (stages(for:args:))")
        return SortPuzzleModule.makeSession(stages: levels, levels: plan.levels, setup: setup, meta: meta, rules: rules,
                                            reward: plan.reward, streakActive: streakActive)
    }

    /// With a tube lifted: the tubes the rules would refuse it (a failed move for the autoplayer); none otherwise.
    func mistakeTargets(_ session: any PuzzleSession, board: any PuzzleBoard) -> [PuzzleTarget] {
        guard let s = session as? SortPuzzleSession, let lifted = s.selection else { return [] }
        return s.tubes.indices
            .filter { $0 != lifted && !SortMechanics.canPour(s.tubes, from: lifted, to: $0, capacity: s.capacity) }
            .map { PuzzleTarget($0) }
    }

    func warmUpWin() -> @Sendable () -> WinResult? {
        let meta = meta, rules = rules
        return { SortPuzzleModule.warmUpWin(meta: meta, rules: rules) }
    }
}

/// `ActivePuzzle.entry` for SortPuzzle.
@MainActor enum SortPuzzleEntry: PuzzleEntryPoint {
    /// The module's data file (App/Resources/Tuning/sort.json).
    static let tuningFile = "sort"

    static func makePlugin(_ app: AppModel) -> any PuzzlePlugin {
        let file = TuningFile.load(tuningFile, bundle: app.bundle, tune: app.args.tune)
        return SortPuzzlePlugin(rules: SortPuzzlePlugin.loadRules(file), meta: app.rules.meta)
    }

    static func makeBoard(_ app: AppModel) -> any PuzzleBoard {
        SortPuzzleBoard(tuning: SortBoardTuning(file: TuningFile.load(tuningFile, bundle: app.bundle, tune: app.args.tune)))
    }
}
