import SwiftUI
import UIKit
import QuartzCore
import PathCore

// SOCIAL SOC2 (SPEC-architecture §10.2 "200-row leaderboard scroll: 0 frames > 20 ms"; SPEC-ui §1.6.11 RankRow, §1.6.21
// JumpPill, §2.15.3-§2.15.5 pinned player row, §2.16 Streak Race rows; SPEC-motion-audio §9 live updates). The long social lists
// as a recycling UIScrollView of Core Animation rows:
//   - ~12 row views exist, whatever the list length; a row entering the viewport points its layers at prepared contents
//     (SocRow: shaped glyph paths, shared face / avatar bitmaps) — no text layout, no image decode, no SwiftUI on scroll;
//   - the player's row pins to the viewport's top or bottom edge while it is scrolled out of view (Weekly, Country, Streak
//     Race; VERIFIED meta-014 / meta-027 / meta-111); World has no pin but the "Bottom" pill (VERIFIED meta-019);
//   - a new snapshot (every 5 s while visible) slides reordered rows to their new slots in 0.35 s and counts changed numbers
//     up in 0.30 s (never backwards: SPEC-social §0 rule 3);
//   - geometry is authored on the 393 pt reference canvas and scaled as a whole by ShellMetrics.s.

/// Row geometry of a list kind (reference pt, x absolute on the canvas, y from the row's top).
struct SocRowGeometry {
    var faceX: CGFloat
    var faceW: CGFloat
    var faceH: CGFloat = 64.4          // face 60.4 + the 4 pt lip
    var meX: CGFloat = 5.0             // the player's row: 383.3 × 66.4, 1.9 pt higher (SPEC-ui `lb.rowMe`)
    var meW: CGFloat = 383.3
    var meH: CGFloat = 66.4
    var meDY: CGFloat = -1.9
    var pitch: CGFloat = 72.07
    var separator: CGFloat = 43.7      // the "• • •" row (36 pt) + the row gap
    var streak = false

    static let leaderboard = SocRowGeometry(faceX: 7.7, faceW: 378)
    static let streakRace = SocRowGeometry(faceX: 7.0, faceW: 379.3, meX: 4.3, meW: 384.6, streak: true)
}

/// One recycled row: its layers, re-pointed by `configure`.
final class SocRowView: UIView {
    let geo: SocRowGeometry
    let kind: SocListKind
    private let face = CALayer()
    private let badge = CALayer()
    private let avatar = CALayer()
    private let bowl = CALayer()
    private let pill = CALayer()
    private let flag = CALayer()
    private var rankLabel: SocLabelLayer!
    private var nameLabel: SocLabelLayer!
    private var captionLabel: SocLabelLayer!
    private var valueLabel: SocLabelLayer!
    private var prizeLabel: SocLabelLayer!
    private(set) var row: SocRow?
    private var countLink: CADisplayLink?
    private var countFrom = 0, countTo = 0, countStart: CFTimeInterval = 0
    let scale: CGFloat

    init(kind: SocListKind, geo: SocRowGeometry, scale: CGFloat) {
        self.kind = kind; self.geo = geo; self.scale = scale
        super.init(frame: CGRect(x: 0, y: 0, width: 393, height: geo.pitch))
        isOpaque = false
        layer.masksToBounds = false
        for l in [face, badge, avatar, bowl, pill, flag] {
            l.contentsScale = scale
            l.contentsGravity = .resize
            l.actions = ["contents": NSNull(), "position": NSNull(), "bounds": NSNull(), "hidden": NSNull(), "frame": NSNull()]
        }
        layer.addSublayer(face)
        layer.addSublayer(badge)
        rankLabel = SocLabelLayer(in: layer, scale: scale)
        layer.addSublayer(avatar)
        nameLabel = SocLabelLayer(in: layer, scale: scale)
        captionLabel = SocLabelLayer(in: layer, scale: scale)
        if geo.streak {
            layer.addSublayer(bowl)
            prizeLabel = SocLabelLayer(in: layer, scale: scale)
            layer.addSublayer(pill)
            layer.addSublayer(flag)
        } else {
            prizeLabel = SocLabelLayer(in: CALayer(), scale: scale)
        }
        valueLabel = SocLabelLayer(in: layer, scale: scale)
        isAccessibilityElement = true
        accessibilityTraits = .staticText
    }

    required init?(coder: NSCoder) { fatalError("SocRowView is built in code") }

    /// Points the layers at `r` (no implicit animations). `animateFrom` counts the value up from an older snapshot's value.
    func configure(_ r: SocRow, animateFrom old: Int? = nil) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        defer { CATransaction.commit() }
        let changed = row.map { !$0.sameContent(r) } ?? true
        row = r
        accessibilityIdentifier = r.identifier(kind)
        accessibilityLabel = r.name
        accessibilityValue = r.isMe && kind != .streak ? "\(r.rank)" : "\(r.value)"
        guard changed else { return }
        let top: CGFloat = 0
        // the player's green row: white numbers with a dark green outline, the caption dark green
        let green: (face: UInt32, outline: UInt32?)? = r.isMe ? (Skin.socialSocListSocRowViewConfigureGreen, Skin.socialSocListSocRowViewConfigureGreenV2) : nil
        rankLabel.tint = r.isMe && r.badge == nil ? (Skin.socialSocListSocRowViewConfigureTint, nil) : nil        // white rank, its navy / brown outline (meta-026)
        valueLabel.tint = green
        captionLabel.tint = r.isMe ? (Skin.socialSocListSocRowViewConfigureTintV2, nil) : nil
        prizeLabel.tint = nil
        // face
        if r.isMe {
            face.frame = CGRect(x: geo.meX, y: top + geo.meDY, width: geo.meW, height: geo.meH)
            face.contents = SocArt.rowFace(.me, size: CGSize(width: geo.meW, height: geo.meH), scale: scale)
        } else {
            face.frame = CGRect(x: geo.faceX, y: top, width: geo.faceW, height: geo.faceH)
            face.contents = SocArt.rowFace(r.look, size: CGSize(width: geo.faceW, height: geo.faceH), scale: scale)
        }
        // rank: the hexagon (1-3) with its digit, or the plain outlined rank
        if let b = r.badge {
            badge.isHidden = false
            badge.contents = SocArt.art(b)
            badge.frame = CGRect(x: 12.15, y: top + 10.3, width: 40, height: 40)
            rankLabel.set(r.rankText, centreX: 32.15, baseline: top + 29.6 + r.rankText.capHeight / 2)
        } else {
            badge.isHidden = true
            rankLabel.set(r.rankText, centreX: 32, baseline: top + 30.75 + r.rankText.capHeight / 2)
        }
        // avatar
        avatar.frame = CGRect(x: 54.7, y: top + 4, width: 53, height: 53.4)
        // the portrait keeps its BLUE frame on the player's green row too (VERIFIED 203 / meta-013 / meta-026)
        avatar.contents = SocArt.avatarTile(r.avatar, me: false, size: CGSize(width: 53, height: 53.4), scale: scale)
        // name
        nameLabel.set(r.nameText, origin: CGPoint(x: 110, y: top + 30.2 + r.nameText.capHeight / 2))
        if geo.streak {
            captionLabel.set(nil, origin: .zero)
            if r.prize > 0 {
                bowl.isHidden = false
                bowl.contents = SocArt.art(.rewardCoinBowl)
                // the 74 × 62 canvas (ink 69 × 56) scaled so the ink is 55.4 × 43 at (243.2, +10.7) (SPEC-ui §2.16)
                bowl.frame = CGRect(x: 241.2, y: top + 8.3, width: 59.4, height: 49.8)
                prizeLabel.set(r.prizeText, centreX: 270.9, baseline: top + 44.4 + (r.prizeText?.capHeight ?? 0) / 2)
            } else {
                bowl.isHidden = true
                prizeLabel.set(nil, origin: .zero)
            }
            pill.frame = CGRect(x: 325.6, y: top + 16, width: 53.4, height: 33.4)
            pill.contents = SocArt.pill(r.look, size: CGSize(width: 53.4, height: 33.4), scale: scale)
            flag.frame = CGRect(x: 299.4, y: top + 11.9, width: 39.6, height: 43.6)
            flag.contents = SocArt.art(.socialScoreChip)
            setValue(r.value, animateFrom: old)
        } else {
            captionLabel.set(r.captionText, centreX: 355, baseline: top + 19.2)
            setValue(r.value, animateFrom: old)
        }
    }

    private func place(_ s: SocShaped) {
        if geo.streak {
            valueLabel.set(s, centreX: 358.4, baseline: top0 + 32.7 + s.capHeight / 2)
        } else {
            valueLabel.set(s, centreX: 355, baseline: top0 + 45)
        }
    }

    private var top0: CGFloat { 0 }

    private func style() -> SocStyle { geo.streak ? SocRowStyles.score : SocRowStyles.value }

    private func setValue(_ v: Int, animateFrom old: Int?) {
        countLink?.invalidate(); countLink = nil
        guard let old, old < v, v - old < 1_000_000 else {
            place(row?.valueText ?? SocType.number(v, style()))
            return
        }
        countFrom = old; countTo = v; countStart = CACurrentMediaTime()
        place(SocType.number(old, style()))
        let link = CADisplayLink(target: SocWeakTarget(self), selector: #selector(SocWeakTarget.tick))
        link.add(to: .main, forMode: .common)
        countLink = link
    }

    /// The 0.30 s easeOutQuad count-up (SPEC-motion-audio §9), integer steps each frame from the digit cache.
    fileprivate func tick() {
        let u = min(1, (CACurrentMediaTime() - countStart) / 0.30)
        let e = 1 - (1 - u) * (1 - u)
        let v = countFrom + Int((Double(countTo - countFrom) * e).rounded(.down))
        CATransaction.begin(); CATransaction.setDisableActions(true)
        place(u >= 1 ? (row?.valueText ?? SocType.number(countTo, style())) : SocType.number(v, style()))
        CATransaction.commit()
        if u >= 1 { countLink?.invalidate(); countLink = nil }
    }

    override func removeFromSuperview() {
        countLink?.invalidate(); countLink = nil
        super.removeFromSuperview()
    }
}

/// Breaks the display link's retain of its target.
@MainActor final class SocWeakTarget: NSObject {
    weak var row: SocRowView?
    weak var list: SocListView?
    init(_ row: SocRowView) { self.row = row }
    init(list: SocListView) { self.list = list }
    @objc func tick() { row?.tick(); list?.slideTick() }
}

/// Where the pill appears and what it does.
enum SocJump: Equatable { case none, top, bottom }

/// The scrolling list (reference-point coordinates; the host scales it).
final class SocListView: UIView, UIScrollViewDelegate {
    struct Spec {
        var kind: SocListKind
        var geo: SocRowGeometry
        /// The first item's top inside the scroll content.
        var firstTop: CGFloat
        /// Space after the last item.
        var bottomPad: CGFloat
        /// The player's row pins at these edges (list-local y of the pinned face's top / bottom), nil = no pin.
        var pinTop: CGFloat?
        var pinBottom: CGFloat?
        /// Where the first open scrolls: the top, or the player's row centred (Country, Streak Race, Weekly).
        var opensAtMe: Bool
        /// World: the "Bottom" pill while the player's row is below; Country: the "Top" pill while rank 1 is off screen.
        var jump: SocJump
    }

    let spec: Spec
    let scroll = UIScrollView()
    private let content = UIView()
    private var pinned: SocRowView
    private var pool: [SocRowView] = []
    private var live: [Int: SocRowView] = [:]                // item index → view
    private var separators: [Int: CALayer] = [:]
    private var tops: [CGFloat] = []
    private(set) var data = SocListContent.empty(.world)
    private var didInitialScroll = false
    /// FIX-V2 F-04: an opens-at-me list keeps re-centring on the player for the snapshots that land in the first
    /// `settleWindow` s after it opens (the page's own event refresh arrives a few frames after the first data and can move
    /// the player several rows), until the player touches the list. Afterwards a live refresh never moves the viewport.
    private var openedAt: CFTimeInterval = -1
    static let settleWindow: CFTimeInterval = 1.5
    private let scale: CGFloat
    var onJump: ((SocJump) -> Void)?
    var onPinBottom: ((Bool) -> Void)?
    private var lastJump: SocJump = .none
    private var lastPinBottom = false
    // slides of reordered rows
    private var slideLink: CADisplayLink?
    private var slides: [(view: SocRowView, from: CGFloat, to: CGFloat)] = []
    private var slideStart: CFTimeInterval = 0

    init(spec: Spec, scale: CGFloat) {
        self.spec = spec
        self.scale = scale
        pinned = SocRowView(kind: spec.kind, geo: spec.geo, scale: scale)
        super.init(frame: CGRect(x: 0, y: 0, width: 393, height: 600))
        clipsToBounds = true
        scroll.delegate = self
        scroll.showsVerticalScrollIndicator = false
        scroll.showsHorizontalScrollIndicator = false
        scroll.alwaysBounceVertical = true
        scroll.contentInsetAdjustmentBehavior = .never
        scroll.backgroundColor = .clear
        scroll.decelerationRate = .normal
        addSubview(scroll)
        scroll.addSubview(content)
        pinned.isHidden = true
        pinned.accessibilityIdentifier = "leaderboard.me.pinned"
        addSubview(pinned)
        isAccessibilityElement = false
        accessibilityIdentifier = "social.list.\(spec.kind.rawValue)"
    }

    required init?(coder: NSCoder) { fatalError("SocListView is built in code") }

    override func layoutSubviews() {
        super.layoutSubviews()
        if scroll.frame != bounds { scroll.frame = bounds; updateContentSize() }
        if !didInitialScroll, !data.items.isEmpty, bounds.height > 10 { initialScroll() }
        layoutVisible()
    }

    // MARK: data

    /// Swaps in a new snapshot. Rows keep their views by player id; reordered ones slide, changed numbers count up.
    func apply(_ c: SocListContent) {
        let oldRows = Dictionary(data.rows.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        var oldY: [UInt64: CGFloat] = [:]
        for (i, v) in live { if let r = v.row, i < tops.count { oldY[r.id] = tops[i] } }
        let first = data.items.isEmpty
        let oldMe = data.meIndex
        data = c
        tops = []
        var y = spec.firstTop
        for item in c.items {
            tops.append(y)
            switch item {
            case .row: y += spec.geo.pitch
            case .separator: y += spec.geo.separator
            }
        }
        updateContentSize()
        // recycle everything, then lay out again (a view keeps its id-keyed old value for the count-up)
        let oldValues = oldRows.mapValues(\.value)
        for (_, v) in live { v.isHidden = true; pool.append(v) }
        live.removeAll()
        for (_, s) in separators { s.removeFromSuperlayer() }
        separators.removeAll()
        if !first && bounds.height > 10 && settling && c.meIndex != oldMe {
            // still opening: the player's row moved (the page's refresh landed) — centre on it again, without row slides
            centreOnMe()
            layoutVisible(oldValues: oldValues)
            return
        }
        if !first && bounds.height > 10 { layoutVisible(oldValues: oldValues, oldY: oldY) } else { setNeedsLayout() }
    }

    /// True while an opens-at-me list is still settling on its first snapshots (no finger on it yet).
    private var settling: Bool {
        spec.opensAtMe && !userScrolled && openedAt >= 0 && CACurrentMediaTime() - openedAt < Self.settleWindow
    }

    /// The page (or tab) that shows this list came on screen: an opens-at-me list centres on the player again (the host is
    /// kept across page re-creations, so without this a second open showed wherever the list was left).
    func pageOpened() {
        guard spec.opensAtMe else { return }
        userScrolled = false
        openedAt = CACurrentMediaTime()
        if !data.items.isEmpty && bounds.height > 10 {
            didInitialScroll = true
            centreOnMe()
            layoutVisible()
        } else {
            didInitialScroll = false
            setNeedsLayout()
        }
    }

    private func centreOnMe() {
        guard let m = data.meIndex, m < tops.count else { return }
        let target = tops[m] + spec.geo.faceH / 2 - bounds.height / 2
        scroll.setContentOffset(CGPoint(x: 0, y: clampOffset(target)), animated: false)
    }

    private func updateContentSize() {
        let h = (tops.last.map { $0 + spec.geo.pitch } ?? spec.firstTop) + spec.bottomPad
        let size = CGSize(width: bounds.width, height: max(h, bounds.height + 1))
        if scroll.contentSize != size { scroll.contentSize = size }
        content.frame = CGRect(origin: .zero, size: size)
    }

    private func initialScroll() {
        didInitialScroll = true
        guard spec.opensAtMe, let m = data.meIndex, m < tops.count else { return }
        if openedAt < 0 { openedAt = CACurrentMediaTime() }
        let target = tops[m] + spec.geo.faceH / 2 - bounds.height / 2
        scroll.contentOffset = CGPoint(x: 0, y: clampOffset(target))
    }

    private func clampOffset(_ y: CGFloat) -> CGFloat {
        max(0, min(y, scroll.contentSize.height - bounds.height))
    }

    // MARK: recycling

    private func dequeue() -> SocRowView {
        if let v = pool.popLast() { v.isHidden = false; return v }
        let v = SocRowView(kind: spec.kind, geo: spec.geo, scale: scale)
        content.addSubview(v)
        return v
    }

    private func visibleRange() -> Range<Int> {
        guard !tops.isEmpty else { return 0..<0 }
        let y0 = scroll.contentOffset.y - spec.geo.pitch, y1 = scroll.contentOffset.y + bounds.height + spec.geo.pitch
        var lo = 0, hi = tops.count
        while lo < hi { let mid = (lo + hi) / 2; if tops[mid] < y0 { lo = mid + 1 } else { hi = mid } }
        var end = lo
        while end < tops.count && tops[end] <= y1 { end += 1 }
        return lo..<end
    }

    private func layoutVisible(oldValues: [UInt64: Int] = [:], oldY: [UInt64: CGFloat] = [:]) {
        let range = visibleRange()
        for (i, v) in live where !range.contains(i) {
            v.isHidden = true; pool.append(v); live[i] = nil
        }
        for (i, s) in separators where !range.contains(i) { s.removeFromSuperlayer(); separators[i] = nil }
        var newSlides: [(SocRowView, CGFloat, CGFloat)] = []
        for i in range where live[i] == nil && separators[i] == nil {
            switch data.items[i] {
            case .row(let r):
                let v = dequeue()
                v.configure(r, animateFrom: oldValues[r.id])
                let y = tops[i]
                v.frame = CGRect(x: 0, y: y, width: 393, height: spec.geo.pitch)
                if let y0 = oldY[r.id], abs(y0 - y) > 1 { newSlides.append((v, y0, y)) }
                live[i] = v
            case .separator:
                let s = CALayer()
                s.contentsScale = scale
                s.contents = SocArt.separator(width: 393, scale: scale)
                s.frame = CGRect(x: 0, y: tops[i], width: 393, height: 36)
                s.actions = ["position": NSNull(), "bounds": NSNull()]
                content.layer.addSublayer(s)
                separators[i] = s
            }
        }
        if !newSlides.isEmpty { startSlides(newSlides) }
        updatePin()
        reportPin()
        updateJump()
    }

    // MARK: slides (0.35 s easeInOut, SPEC-motion-audio §9)

    private func startSlides(_ s: [(SocRowView, CGFloat, CGFloat)]) {
        slides = s.map { (view: $0.0, from: $0.1, to: $0.2) }
        for sl in slides { sl.view.frame.origin.y = sl.from }
        slideStart = CACurrentMediaTime()
        slideLink?.invalidate()
        let link = CADisplayLink(target: SocWeakTarget(list: self), selector: #selector(SocWeakTarget.tick))
        link.add(to: .main, forMode: .common)
        slideLink = link
    }

    fileprivate func slideTick() {
        let u = min(1, (CACurrentMediaTime() - slideStart) / 0.35)
        let e = u < 0.5 ? 2 * u * u : 1 - pow(-2 * u + 2, 2) / 2
        for sl in slides { sl.view.frame.origin.y = sl.from + (sl.to - sl.from) * CGFloat(e) }
        if u >= 1 { slideLink?.invalidate(); slideLink = nil; slides = [] }
    }

    // MARK: pinned player row

    private func updatePin() {
        guard let m = data.meIndex, m < tops.count, case .row(let r) = data.items[m],
              spec.pinTop != nil || spec.pinBottom != nil else { pinned.isHidden = true; return }
        let y = tops[m] - scroll.contentOffset.y            // the row's top in list coordinates
        let faceTop = y + spec.geo.meDY, faceBottom = faceTop + spec.geo.meH
        let topEdge = spec.pinTop ?? -.greatestFiniteMagnitude
        let bottomEdge = spec.pinBottom ?? .greatestFiniteMagnitude
        if let pt = spec.pinTop, faceTop < topEdge {
            showPinned(r, top: pt - spec.geo.meDY)
        } else if let pb = spec.pinBottom, faceBottom > bottomEdge {
            showPinned(r, top: pb - spec.geo.meH - spec.geo.meDY)
        } else {
            pinned.isHidden = true
        }
    }

    private func showPinned(_ r: SocRow, top: CGFloat) {
        if pinned.row.map({ !$0.sameContent(r) }) ?? true { pinned.configure(r) }
        pinned.accessibilityIdentifier = spec.kind == .streak ? "event.streakRace.me.pinned" : "leaderboard.me.pinned"
        CATransaction.begin(); CATransaction.setDisableActions(true)
        pinned.frame = CGRect(x: 0, y: top, width: 393, height: spec.geo.pitch)
        CATransaction.commit()
        pinned.isHidden = false
    }

    /// True while the pinned copy is up at the bottom edge (the Country "Top" pill moves above it).
    var pinnedAtBottom: Bool { !pinned.isHidden && pinned.frame.minY > bounds.height / 2 }

    private func reportPin() {
        let b = pinnedAtBottom
        if b != lastPinBottom { lastPinBottom = b; onPinBottom?(b) }
    }

    // MARK: the jump pill

    private func updateJump() {
        var j = SocJump.none
        switch spec.jump {
        case .bottom:
            // World: "Bottom" while scrolled into the list and the player's row is below the viewport (VERIFIED meta-019)
            if userScrolled, let m = data.meIndex, m < tops.count, scroll.contentOffset.y > spec.geo.pitch * 0.5,
               tops[m] > scroll.contentOffset.y + bounds.height { j = .bottom }
        case .top:
            // Country: "Top" once the player has scrolled (not at the open: VERIFIED meta-026 shows none) while rank 1 is off screen
            if userScrolled, let f = tops.first, f + spec.geo.faceH < scroll.contentOffset.y { j = .top }
        case .none: break
        }
        if j != lastJump { lastJump = j; onJump?(j) }
    }

    func jump() {
        switch lastJump {
        case .top: scroll.setContentOffset(.zero, animated: true)
        case .bottom:
            if let m = data.meIndex, m < tops.count {
                let target = tops[m] + spec.geo.faceH / 2 - bounds.height / 2
                scroll.setContentOffset(CGPoint(x: 0, y: clampOffset(target)), animated: true)
            }
        case .none: break
        }
    }

    /// Scrolls so the player's row is centred (tests, the Weekly join).
    func scrollToMe(animated: Bool) {
        guard let m = data.meIndex, m < tops.count else { return }
        let target = tops[m] + spec.geo.faceH / 2 - bounds.height / 2
        scroll.setContentOffset(CGPoint(x: 0, y: clampOffset(target)), animated: animated)
    }

    func scrollViewDidScroll(_ scrollView: UIScrollView) {
        if scrollView.isTracking || scrollView.isDecelerating { userScrolled = true }
        layoutVisible()
    }

    /// Set by the first finger scroll (the pills appear only after the player moved the list).
    private var userScrolled = false

    // MARK: accessibility

    override var accessibilityElements: [Any]? {
        get {
            var out: [Any] = live.sorted { $0.key < $1.key }.map { $0.value }.filter { !$0.isHidden }
            if !pinned.isHidden { out.append(pinned) }
            return out
        }
        set { }
    }
}

/// Hosts a list view scaled from the reference canvas to the live width.
final class SocListHost: UIView {
    let list: SocListView
    var k: CGFloat = 1 { didSet { if k != oldValue { setNeedsLayout() } } }

    init(_ list: SocListView) {
        self.list = list
        super.init(frame: .zero)
        clipsToBounds = true
        addSubview(list)
        isAccessibilityElement = false
    }

    required init?(coder: NSCoder) { fatalError("built in code") }

    override func layoutSubviews() {
        super.layoutSubviews()
        let kk = max(0.1, k)
        list.transform = .identity
        list.bounds = CGRect(x: 0, y: 0, width: 393, height: bounds.height / kk)
        list.center = CGPoint(x: bounds.midX, y: bounds.midY)
        list.transform = CGAffineTransform(scaleX: kk, y: kk)
    }

    override var accessibilityElements: [Any]? {
        get { list.accessibilityElements }
        set { }
    }
}

/// SwiftUI bridge. The host view is owned by the SocialModel (one per list kind), so a tab switch or a page re-creation keeps
/// its scroll position and never rebuilds the rows.
struct SocListRepresentable: UIViewRepresentable {
    let host: SocListHost
    let k: CGFloat

    func makeUIView(context: Context) -> SocListHost {
        host.removeFromSuperview()
        return host
    }

    func updateUIView(_ uiView: SocListHost, context: Context) {
        uiView.k = k
    }

    static func dismantleUIView(_ uiView: SocListHost, coordinator: ()) {}
}
