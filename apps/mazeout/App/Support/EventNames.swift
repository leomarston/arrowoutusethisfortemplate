import Foundation
import PathCore

// Our event names (strings keys), moved as they were from Social/EventAnnounce.swift in the kit decoupling step: the
// notifications name the events too (the Double Event Week reminder), so the names are core's, like the events' ids.

/// Our event names (ruling 38 / T1; the internal EventID raw values never change: they live in saves).
enum EventNames {
    static func name(_ e: EventID) -> LocalizedStringResource {
        switch e.rawValue {
        case "streakRace": return "Hot Streak"
        case "weeklyContest": return "Weekly Cup"
        case "clawChallenge": return "Treasure Climb"
        case "rocketRace": return "Rocket Rally"
        case "skyJump": return "Cloud Hop"
        default: return "Up & Away"
        }
    }
}
