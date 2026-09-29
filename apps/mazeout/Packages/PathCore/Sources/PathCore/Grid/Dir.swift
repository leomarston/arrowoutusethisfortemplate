import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.2). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests). Real code, not a stub: it is tiny and final.

/// A head direction / a step direction on the grid. JSON: "up" | "down" | "left" | "right" (every schema).
public enum Dir: String, Codable, Sendable, CaseIterable {
    case up, down, left, right

    /// Column step: left −1, right +1.
    public var dc: Int {
        switch self {
        case .left: return -1
        case .right: return 1
        case .up, .down: return 0
        }
    }

    /// Row step (rows grow DOWN): up −1, down +1.
    public var dr: Int {
        switch self {
        case .up: return -1
        case .down: return 1
        case .left, .right: return 0
        }
    }

    public var opposite: Dir {
        switch self {
        case .up: return .down
        case .down: return .up
        case .left: return .right
        case .right: return .left
        }
    }

    /// Screen-space angle, y DOWN: right 0, down π/2, left π, up −π/2 (a head path drawn pointing right, rotated by it).
    public var angle: Double {
        switch self {
        case .right: return 0
        case .down: return Double.pi / 2
        case .left: return Double.pi
        case .up: return -Double.pi / 2
        }
    }

    public var isHorizontal: Bool { self == .left || self == .right }

    /// The direction of one orthogonal step a → b; nil when b is not an orthogonal neighbour of a.
    public init?(from a: Cell, to b: Cell) {
        switch (b.c - a.c, b.r - a.r) {
        case (0, -1): self = .up
        case (0, 1): self = .down
        case (-1, 0): self = .left
        case (1, 0): self = .right
        default: return nil
        }
    }
}
