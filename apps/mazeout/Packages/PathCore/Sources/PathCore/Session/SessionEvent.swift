import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.5, D7). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
// THE one ordered event stream. LevelSession returns batches in causal order; GAME forwards every batch unchanged to the
// presenters in the §8.1 order (board, haptics, audio, HUD, FX, directors) on the same frame.

public enum SessionEvent: Equatable, Sendable {
    case stageLoaded(stage: Int, of: Int, level: Int)
    case timerArmed(stage: Int, seconds: Int)                  // .ready: the HUD shows the limit, frozen
    case timerStarted(stage: Int)                              // the first tap of the stage
    case exited(ExitPlan)
    case bumped(BumpPlan)
    case tapIgnored(ArrowID?, IgnoreReason)
    case heartLost(remaining: Int)                             // at .bumpContact
    case arrowMarked(ArrowID)                                  // at .bumpContact (turns red on the return, §5.5)
    case keyDispatched(key: ObstacleID, door: ObstacleID)
    case doorOpened(ObstacleID, revealed: [ArrowID])           // at .doorBurst
    case pipeUsed(ObstacleID, remaining: Int)
    case pipeBroken(ObstacleID)
    case counterChanged(ObstacleID, remaining: Int)
    case counterBroken(ObstacleID, revealed: [ArrowID])
    case elevatorActivated(ObstacleID, revealed: [ArrowID])
    case timerAlert(TimerAlert)
    case timeAdded(seconds: Int, cause: TimeCause)
    case freezeStarted(seconds: Double)
    case freezeEnded
    case boosterUsed(BoosterID)
    case hintShown([ArrowID])
    case stageCleared(stage: Int)
    case stageAdvanced(to: Int)
    case offer(ContinueOffer)
    case continued(ContinueOffer)
    case won(WinResult)
    case lost(LossReason)
}
