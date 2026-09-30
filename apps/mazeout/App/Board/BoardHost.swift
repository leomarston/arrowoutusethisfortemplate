import SwiftUI
import UIKit

// B1 (SPEC-architecture §5.1, §3.5 BoardEntry). BoardHost hosts the ONE app-lifetime board container edge to edge
// (ignoring the safe area) and never re-creates it: a host adopts the container on appear and releases it only if it
// still holds it (a transition may already have moved it to the next host). BOARD installs its engine and BoardLab
// through `BoardEntry` (the WP0 entry-point pattern; the boot log names any default still in use).

struct BoardHost: UIViewRepresentable {
    let board: any BoardControlling

    func makeUIView(context: Context) -> BoardHostView {
        let v = BoardHostView()
        v.adopt(board.view)
        return v
    }

    func updateUIView(_ uiView: BoardHostView, context: Context) {
        uiView.adopt(board.view)
    }

    static func dismantleUIView(_ uiView: BoardHostView, coordinator: ()) {
        uiView.releaseHosted()
    }
}

final class BoardHostView: UIView {
    private weak var hosted: UIView?

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .white
        clipsToBounds = true
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    func adopt(_ v: UIView) {
        if v.superview !== self {
            v.removeFromSuperview()
            addSubview(v)
        }
        hosted = v
        setNeedsLayout()
    }

    func releaseHosted() {
        if let v = hosted, v.superview === self { v.removeFromSuperview() }
        hosted = nil
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        if let v = hosted, v.superview === self, v.frame != bounds { v.frame = bounds }
    }
}

extension BoardEntry {
    static func makeBoard(_ ctx: AppContext) -> any BoardControlling { BoardEngine(ctx) }
    #if DEBUG || PC_MEASURE
    // BoardLab is Debug / Measure only; the Release build keeps BoardEntryPoint's default (no debug screen)
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? {
        name == LabID.boardlab.rawValue ? AnyView(BoardLab(app: app)) : nil
    }
    #endif
}
