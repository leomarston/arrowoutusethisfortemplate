import Foundation
import PathCore

// The log line of an event outcome (`[PC][win] … banked … events …`, the events' refresh notes). Moved as it was from
// EventsDirector (Game/EventsDirector.swift, which forwards to it) in the kit decoupling step, so the win flow logs a win
// without the events engine. FIX-2 A (V3-02): a switch, not "\($0)" (Swift's reflection-based description cost the FIRST
// event-counted win of a process ~14 ms between `won` and `banked`).

enum EventOutcomeLog {
    static func describe(_ o: EventOutcome) -> String {
        switch o {
        case .multiplier(let a, let b): return "streak multiplier x\(a) → x\(b)"
        case .clawPoints(let added, let total, let target): return "clawChallenge +\(added) → \(total)/\(target)"
        case .clawStep(let step, let reward): return "clawChallenge step \(step) completed: \(reward)"
        case .streakRaceScore(let n): return "streakRace score \(n)"
        case .skyJumpProgress(let n, let of): return "skyJump progress \(n)/\(of)"
        case .skyJumpWon(let share, let winners): return "skyJump won: \(share) coins (\(winners) winners)"
        case .skyJumpFailed: return "skyJump failed"
        case .rocketProgress(let n): return "rocketRace progress \(n)"
        case .rocketFinished(let rank, let reward): return "rocketRace finished rank \(rank)\(reward.map { " \($0)" } ?? "")"
        case .weeklyScore(let n): return "weeklyContest score \(n)"
        case .grant(let g): return "grant \(g)"
        // A0: contract amend 4 (SPEC.md §5 item 42), Balloon Rise (v582 rules); B1 emits these
        case .balloonStreak(let added, let total, let goal): return "balloonRise +\(added) → \(total)\(goal.map { "/\($0)" } ?? " (all platforms)")"
        case .balloonStep(let step, let reward): return "balloonRise platform \(step) reached: \(reward)"
        case .balloonFell(let from): return "balloonRise fell from \(from) to 0"
        }
    }
}
