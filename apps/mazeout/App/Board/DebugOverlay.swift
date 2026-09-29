import UIKit

// B1 (SPEC-architecture §9.6; tools/bench/bench.py HUD_CROP "0,95,260,60"). `-pc.hud debug` (hidden in captures): three
// lines of monospaced digits at (0, 95)–(260, 155) pt, above everything (it lives in the window, not under the HUD):
//   "<fps> fps p95 <ms> p99 <ms> ms"      (last 600 frames)
//   "<MB> MB <n> layers <n> movers"       (phys_footprint, live board layers, arrows in motion)
//   "tap <ms>/<ms> vsync <ms>"            (last tap: touch→handler / handler→commit, commit→vsync)

final class DebugOverlayView: UIView {
    private let label = UILabel()

    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = UIColor(white: 1, alpha: 0.82)
        accessibilityIdentifier = "debug.hud"
        label.numberOfLines = 3
        label.font = .monospacedDigitSystemFont(ofSize: 13, weight: .semibold)
        label.textColor = .black
        addSubview(label)
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override func layoutSubviews() {
        super.layoutSubviews()
        label.frame = bounds.insetBy(dx: 6, dy: 2)
    }

    func update(_ lines: [String]) {
        let text = lines.joined(separator: "\n")
        if label.text != text { label.text = text }
    }

    /// Installs itself at the top of `window` (idempotent).
    func install(in window: UIWindow) {
        if superview !== window { window.addSubview(self) }
        frame = CGRect(x: 0, y: 95, width: 260, height: 60)
        window.bringSubviewToFront(self)
    }
}
