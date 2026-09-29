import UIKit

// B1 (SPEC-architecture §5.1). The one full-screen board view for the whole app run (hosted edge to edge by BoardHost,
// never re-created): the zoom/pan scroll view with the stage, the screen-space FX above it (no touches), and the
// invisible `board.probe` element (§9.4). It tells the engine about its first layout (the command queue replays then)
// and about window changes (the display link runs only while the board is in a window).

final class BoardContainerView: UIView {
    let scroll = BoardScrollView()
    let screenFX = ScreenFXView()
    let probeElement = ProbeElementView()
    var onLayout: ((CGSize) -> Void)?
    var onWindow: ((UIWindow?) -> Void)?
    private var lastSize: CGSize = .zero

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .white                 // plain white board ground, no grid lines (VERIFIED motion §2.1)
        accessibilityIdentifier = "board"
        addSubview(scroll)
        addSubview(screenFX)
        addSubview(probeElement)
        probeElement.isHidden = true
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override func layoutSubviews() {
        super.layoutSubviews()
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        scroll.frame = bounds
        screenFX.frame = bounds
        probeElement.frame = CGRect(x: 0, y: 0, width: 2, height: 2)
        CATransaction.commit()
        if bounds.size != lastSize, bounds.width > 0, bounds.height > 0 {
            lastSize = bounds.size
            onLayout?(bounds.size)
        }
    }

    override func didMoveToWindow() {
        super.didMoveToWindow()
        onWindow?(window)
    }
}

/// The §9.4 probe: an invisible accessibility element whose value is the compact probe JSON (refreshed ≤ 4 Hz).
final class ProbeElementView: UIView {
    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = true
        accessibilityIdentifier = "board.probe"
        accessibilityLabel = "board.probe"
        accessibilityTraits = .staticText
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }
}
