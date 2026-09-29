import UIKit

// B1 (SPEC-architecture §5.1, §5.2). The zoom/pan surface: full screen, clipping at the SCREEN edge; its content view is
// the board's content space at fit (bounds = layout.contentSize, clipsToBounds false so exits run to the screen edge)
// and holds the stage layer.
//
// Placement: at every zoom the content is centred in the play rect when it is smaller than it, and the player can pan
// it `pan.slackPt` beyond (VERIFIED: a swipe pans the board even at fit and the pan persists, levels L47e; limits and
// snap-back are unmeasured → board.json `pan.*`, PENDING-motion-audio). Along each axis the content's origin on screen
// may range over [min(o_c, b − C) − slack, max(o_c, a) + slack], where [a, b] is the play rect span, C the zoomed
// content length and o_c the centred origin; `contentInset` encodes exactly that range.

final class BoardContentView: UIView {
    override init(frame: CGRect) {
        super.init(frame: frame)
        clipsToBounds = false
        backgroundColor = .clear
        isUserInteractionEnabled = false
        layer.masksToBounds = false
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }
}

final class BoardScrollView: UIScrollView {
    let content = BoardContentView()
    /// The play rect in this view's coordinates (the board centres in it).
    var playRect: CGRect = .zero
    var slack: CGFloat = 120
    /// SPEC-motion-audio §3.9 `pan.limit = "centreInGrid"` (CONSISTENCY G-11; `pan.slackPt` is then ignored): the play-rect
    /// centre may reach, but not pass, the grid's outer edge, at every zoom (VERIFIED meta-116…123).
    var centreInGrid = false
    /// The one empty margin cell round the grid, in content pt at zoom 1 (= the pitch).
    var gridMargin: CGFloat = 0

    override init(frame: CGRect) {
        super.init(frame: frame)
        clipsToBounds = true
        backgroundColor = .clear
        showsVerticalScrollIndicator = false
        showsHorizontalScrollIndicator = false
        contentInsetAdjustmentBehavior = .never
        delaysContentTouches = false
        canCancelContentTouches = true
        bouncesZoom = true
        alwaysBounceVertical = true
        alwaysBounceHorizontal = true
        decelerationRate = .normal
        scrollsToTop = false
        addSubview(content)
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    /// Recomputes the insets for the current zoom (the allowed range of the content's on-screen origin, per axis).
    func updateInsets() {
        guard bounds.width > 0, playRect.width > 0 else { return }
        if centreInGrid {
            let inset = insets(forZoom: zoomScale)
            if contentInset != inset { contentInset = inset }
            return
        }
        let c = contentSize
        let (top, bottom) = Self.range(a: playRect.minY, b: playRect.maxY, length: c.height, view: bounds.height, slack: slack)
        let (left, right) = Self.range(a: playRect.minX, b: playRect.maxX, length: c.width, view: bounds.width, slack: slack)
        let inset = UIEdgeInsets(top: top, left: left, bottom: bottom, right: right)
        if contentInset != inset { contentInset = inset }
    }

    /// The insets at zoom `z`. Centre-in-grid: along each axis the content origin o may range so that the play-rect
    /// centre c stays over the grid: c ∈ [o + m·z, o + (C − m)·z] ⇔ o ∈ [c − (C − m)·z, c − m·z]; with B1's range
    /// encoding that is inset before = c − m·z and inset after = view − c − m·z (independent of the content length).
    func insets(forZoom z: CGFloat) -> UIEdgeInsets {
        if centreInGrid {
            let m = gridMargin * z
            let cx = playRect.midX, cy = playRect.midY
            return UIEdgeInsets(top: cy - m, left: cx - m, bottom: bounds.height - cy - m, right: bounds.width - cx - m)
        }
        let c = CGSize(width: content.bounds.width * z, height: content.bounds.height * z)
        let (top, bottom) = Self.range(a: playRect.minY, b: playRect.maxY, length: c.height, view: bounds.height, slack: slack)
        let (left, right) = Self.range(a: playRect.minX, b: playRect.maxX, length: c.width, view: bounds.width, slack: slack)
        return UIEdgeInsets(top: top, left: left, bottom: bottom, right: right)
    }

    /// (inset before, inset after) for one axis: origin ∈ [lo, hi] ⇔ offset ∈ [−hi, −lo]; offset min = −insetBefore,
    /// offset max = length + insetAfter − view.
    static func range(a: CGFloat, b: CGFloat, length: CGFloat, view: CGFloat, slack: CGFloat) -> (CGFloat, CGFloat) {
        let centred = (a + b) / 2 - length / 2
        let lo = min(centred, b - length) - slack
        let hi = max(centred, a) + slack
        return (hi, -lo - length + view)
    }

    /// The offset that centres the content in the play rect.
    func centredOffset() -> CGPoint { centredOffset(contentSize: contentSize) }

    /// The offset that centres content of size `c` (at zoom 1) in the play rect (FEEL: the next stage's placement before
    /// its geometry is installed).
    func centredOffset(contentSize c: CGSize) -> CGPoint {
        let ox = (playRect.minX + playRect.maxX) / 2 - c.width / 2
        let oy = (playRect.minY + playRect.maxY) / 2 - c.height / 2
        return CGPoint(x: -ox, y: -oy)
    }
}
