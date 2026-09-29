// POLISH LANE r3 prototypes of the shell's popup chrome (App/Shell/Popups/PopupChrome.swift is NOT edited; these are the
// replacements proposed in art/lanes/polish.md, rendered by build/ui-art/polish/chromerender for the 007 comparisons).
import SwiftUI

// MARK: - panel frame: 21 pt bar with its own outlines, corner bumpers with royal-blue + light edge bands, groove + rim line
struct PolishPanelFrame: View {
    var n: CGFloat = 5.8                                     // 007: corner rounder than 6.3 (dy 10-20 pt: 6 pt closer), sides flat
    let t: Tokens
    var bumperArm = CGSize(width: 83.4, height: 90.4)          // 007: legs end 83.4 pt along the bottom, 90.4 down from the top,
    var bumperArmBottom: CGFloat = 93.5                        //      93.5 up from the bottom
    var rivetTop = CGPoint(x: 12.0, y: 79.8)                   // rivet centres (VERIFIED 007 blob centres)
    var rivetLowSide: CGFloat = 83.7                           // side rivets of the bottom bumpers, from the bottom
    var rivetBottom = CGPoint(x: 72.5, y: 15.7)                // bottom-row rivets: from the side / from the bottom
    var body: some View { GeometryReader { geo in art(geo.size) } }

    private func ring(_ s: CGSize, _ inset: CGFloat) -> Path {
        Superellipse(n: n).path(in: CGRect(origin: .zero, size: s).insetBy(dx: inset, dy: inset))
    }

    @ViewBuilder private func art(_ s: CGSize) -> some View {
        let r = CGRect(origin: .zero, size: s)
        let outer = Superellipse(n: n)
        let barOut: CGFloat = 21.0                              // outer edge -> groove (both outlines included)
        let groove: CGFloat = 9.8                               // groove width to the field's rim line
        let bumper = PolishBumper(n: n, width: barOut, arm: bumperArm, armBottom: bumperArmBottom)
        ZStack(alignment: .topLeading) {
            // bar: #13349E outline 1.6 pt (#152C74 hairline outside), flat face #005EEE -> #006AFD low, a 0.6 pt light line
            // #0169EE inside each outline, and its own inner outline #13349E 1.7 pt before the groove
            outer.fill(Color(hex: 0x152C74))
            outer.fill(Color(hex: 0x13349E)).padding(0.35)
            outer.fill(Color(hex: 0x0169EE)).padding(1.6)
            outer.fill(LinearGradient(colors: [Color(hex: 0x0060EE), Color(hex: 0x005EEE), Color(hex: 0x006AFD)], startPoint: .top, endPoint: .bottom))
                .padding(2.2)
            outer.fill(Color(hex: 0x0169EE)).padding(barOut - 2.3)
            outer.fill(Color(hex: 0x13349E)).padding(barOut - 1.7)
            // the bar darkens for ~6 pt next to each bumper end (the bumper's shadow on it)
            // corner bumpers: flat #00B4FF (a touch darker #00A8EF at the top), edge bands clipped inside: navy hairline,
            // royal #1D53FF 1.2 pt, light #4AC8FF 1.4 pt
            ZStack {
                bumper.fill(LinearGradient(stops: [.init(color: Color(hex: 0x00A7EE), location: 0), .init(color: Color(hex: 0x00B4FF), location: 0.05),
                                                   .init(color: Color(hex: 0x00B4FF), location: 1)], startPoint: .top, endPoint: .bottom))
                ZStack {
                    bumper.stroke(Color(hex: 0x4AC8FF), lineWidth: 6.0)
                    bumper.stroke(Color(hex: 0x1D53FF), lineWidth: 3.2)
                    bumper.stroke(Color(hex: 0x13349E), lineWidth: 0.9)
                }
                .clipShape(bumper)
            }
            // groove: dark #0C2794 at the bar, lightening to #1A53DF over 9.8 pt; the field's bright rim line #257DF7, field #226DF5
            ZStack {
                Superellipse(n: n).fill(Color(hex: 0x1A53DF))
                Superellipse(n: n).stroke(Color(hex: 0x0C2794), lineWidth: 13).blur(radius: 3.4).clipShape(Superellipse(n: n))
            }
            .padding(barOut)
            ZStack {
                Superellipse(n: n).fill(Color(hex: 0x257DF7))
                Superellipse(n: n).fill(Color(hex: 0x226DF5)).padding(1.0)
            }
            .padding(barOut + groove)
            ForEach(Array(PolishRivet.all(in: r, top: rivetTop, lowSide: rivetLowSide, bottom: rivetBottom).enumerated()), id: \.offset) { _, p in
                PolishRivet().frame(width: 11.6, height: 11.6).position(p)
            }
        }
        .accessibilityHidden(true)
    }
}

/// The ring between the outer superellipse and the bar's inner edge, cut to the four corner arms.
struct PolishBumper: Shape {
    var n: CGFloat, width: CGFloat, arm: CGSize, armBottom: CGFloat
    func path(in r: CGRect) -> Path {
        let o = Superellipse(n: n).path(in: r).cgPath
        let i = Superellipse(n: n).path(in: r.insetBy(dx: width, dy: width)).cgPath
        let a = PolishArms(arm: arm, armBottom: armBottom).path(in: r).cgPath
        return Path(o.subtracting(i).intersection(a))
    }
}

private struct PolishArms: Shape {
    var arm: CGSize
    var armBottom: CGFloat
    func path(in r: CGRect) -> Path {
        var p = Path()
        let w = arm.width, h = arm.height, hb = armBottom
        // the corner rectangles: both legs of each bumper end square (a 1.2 pt rounding)
        for rc in [CGRect(x: r.minX, y: r.minY, width: w, height: h), CGRect(x: r.maxX - w, y: r.minY, width: w, height: h),
                   CGRect(x: r.minX, y: r.maxY - hb, width: w, height: hb), CGRect(x: r.maxX - w, y: r.maxY - hb, width: w, height: hb)] {
            p.addRoundedRect(in: rc, cornerSize: CGSize(width: 1.2, height: 1.2))
        }
        return p
    }
}

private struct PolishRivet: View {
    var body: some View {
        ZStack {
            Circle().fill(Color(hex: 0x1A46C0))
            Circle().fill(RadialGradient(colors: [Color(hex: 0x4CA8EE), Color(hex: 0x3B8AE4), Color(hex: 0x2256C8)],
                                         center: UnitPoint(x: 0.5, y: 0.45), startRadius: 0, endRadius: 5.4)).padding(1.0)
        }
    }
    static func all(in r: CGRect, top: CGPoint, lowSide: CGFloat, bottom: CGPoint) -> [CGPoint] {
        [CGPoint(x: r.minX + top.x, y: r.minY + top.y), CGPoint(x: r.maxX - top.x, y: r.minY + top.y),
         CGPoint(x: r.minX + top.x, y: r.maxY - lowSide), CGPoint(x: r.maxX - top.x, y: r.maxY - lowSide),
         CGPoint(x: r.minX + bottom.x, y: r.maxY - bottom.y), CGPoint(x: r.maxX - bottom.x, y: r.maxY - bottom.y)]
    }
}

// MARK: - ribbon: a TRUE arch (polar warp about a centre bendRadius below the top: radial ends that lean in ~7 deg),
// top corners r 16, bottom corners r 27, body 84.5 pt thick; layered bands that follow the arch
struct PolishArched: Shape {
    var bendRadius: CGFloat = 1100
    var thickness: CGFloat = 84.5
    var inset: EdgeInsets = EdgeInsets()                     // bands: inset from the full body (pt)
    var topR: CGFloat = 16, bottomR: CGFloat = 20
    var widen: CGFloat = 2.2                                 // the flat body is 2.2 pt wider each side than the frame:
                                                             // after the lean its widest row (~25 pt down) spans the frame

    func path(in r: CGRect) -> Path {
        let cx = r.midX, top = r.minY
        let x0 = r.minX - widen + inset.leading, x1 = r.maxX + widen - inset.trailing
        let y0 = top + inset.top, y1 = top + thickness - inset.bottom
        let tr = max(0, topR - inset.top), br = max(0, bottomR - inset.bottom)
        // flat outline with separate top / bottom radii, sampled densely
        var pts: [CGPoint] = []
        func arc(_ c: CGPoint, _ rad: CGFloat, _ a0: CGFloat, _ a1: CGFloat) {
            for k in 0...10 { let a = (a0 + (a1 - a0) * CGFloat(k) / 10) * .pi / 180; pts.append(CGPoint(x: c.x + rad * cos(a), y: c.y + rad * sin(a))) }
        }
        func line(_ a: CGPoint, _ b: CGPoint) {
            let n = max(2, Int(abs(b.x - a.x) / 3)); for k in 1..<n { let t = CGFloat(k) / CGFloat(n); pts.append(CGPoint(x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t)) }
        }
        arc(CGPoint(x: x0 + tr, y: y0 + tr), tr, 180, 270)
        line(CGPoint(x: x0 + tr, y: y0), CGPoint(x: x1 - tr, y: y0))
        arc(CGPoint(x: x1 - tr, y: y0 + tr), tr, 270, 360)
        arc(CGPoint(x: x1 - br, y: y1 - br), br, 0, 90)
        line(CGPoint(x: x1 - br, y: y1), CGPoint(x: x0 + br, y: y1))
        arc(CGPoint(x: x0 + br, y: y1 - br), br, 90, 180)
        // polar warp: x along the top arc, y down toward the centre (cx, top + R)
        let R = bendRadius
        var p = Path()
        for (i, q) in pts.enumerated() {
            let th = (q.x - cx) / R, rad = R - (q.y - top)
            let w = CGPoint(x: cx + rad * sin(th), y: top + R - rad * cos(th))
            if i == 0 { p.move(to: w) } else { p.addLine(to: w) }
        }
        p.closeSubpath()
        return p
    }
}

struct PolishRibbon: View {
    let t: Tokens
    var body: some View {
        GeometryReader { _ in
            ZStack(alignment: .topLeading) {
                // outline hairline #642806, a 1.7 pt brown band #963804 -> #B94907 at the top; the bottom shade darkens from
                // #FBAC00 through #D24E01 / #A63F04 to #672200 over 7.7 pt
                PolishArched().fill(Color(hex: 0x642806))
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 0.3, bottom: 0.0, trailing: 0.3)).fill(Color(hex: 0x6A2400))
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 0.5, bottom: 1.4, trailing: 0.5)).fill(Color(hex: 0x8D3403)).blur(radius: 0.5)
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 0.8, bottom: 3.2, trailing: 0.8)).fill(Color(hex: 0xB04405)).blur(radius: 0.7)
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 1.1, bottom: 5.0, trailing: 1.1)).fill(Color(hex: 0xD35001)).blur(radius: 0.7)
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 1.3, bottom: 6.6, trailing: 1.3)).fill(Color(hex: 0xEF8C00)).blur(radius: 0.6)
                // the top brown band, then the highlight line #FFFC4B, then the face #FFD500 -> #FFB600
                PolishArched(inset: EdgeInsets(top: 0.3, leading: 1.4, bottom: 7.6, trailing: 1.4))
                    .fill(LinearGradient(colors: [Color(hex: 0x963804), Color(hex: 0xB94907)], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.03)))
                PolishArched(inset: EdgeInsets(top: 2.0, leading: 1.9, bottom: 7.7, trailing: 1.9)).fill(Color(hex: 0xFFFA4A)).blur(radius: 0.5)
                PolishArched(inset: EdgeInsets(top: 4.4, leading: 2.4, bottom: 7.7, trailing: 2.4))
                    .fill(LinearGradient(colors: [Color(hex: 0xFFD500), Color(hex: 0xFFC800), Color(hex: 0xFFB600)], startPoint: .top, endPoint: .bottom))
                    .blur(radius: 0.4)
            }
        }
        .accessibilityHidden(true)
    }
}

// MARK: - close: red disc 46.2 pt (the frame's 45 x 1.027) with a dark-red rim (3.3 pt on the sides, 2 pt on top), a lighter
// top band #FF7A7F, face #FF5155 -> #FF3C3D; a 4.8 pt RADIAL blue ring (light #1897DD inside -> #0848A3 outside, outer ⌀ 56.3)
struct PolishCloseButton: View {
    let t: Tokens
    var body: some View {
        GeometryReader { geo in
            let d = min(geo.size.width, geo.size.height)
            let disc = d * 46.2 / 45, ring = d * 56.3 / 45
            ZStack {
                Circle().fill(Color(hex: 0x081B66)).frame(width: ring, height: ring)
                Circle().fill(RadialGradient(stops: [.init(color: Color(hex: 0x1A98DD), location: 0), .init(color: Color(hex: 0x127ECA), location: 0.35),
                                                     .init(color: Color(hex: 0x0B5EB3), location: 0.7), .init(color: Color(hex: 0x0848A3), location: 1)],
                                             center: .center, startRadius: disc / 2, endRadius: ring / 2 - 0.4))
                    .frame(width: ring - 0.8, height: ring - 0.8)
                Circle().fill(Color(hex: 0x2A3550)).frame(width: disc + 0.8, height: disc + 0.8)
                Circle().fill(RadialGradient(stops: [.init(color: Color(hex: 0xBA0000), location: 0), .init(color: Color(hex: 0x9E0000), location: 0.5),
                                                     .init(color: Color(hex: 0x4D0000), location: 1)],
                                             center: .center, startRadius: disc / 2 - 3.3, endRadius: disc / 2))
                    .frame(width: disc, height: disc)
                ZStack {
                    Circle().fill(LinearGradient(stops: [.init(color: Color(hex: 0xFF7A7F), location: 0), .init(color: Color(hex: 0xFF5A5E), location: 0.08),
                                                         .init(color: Color(hex: 0xFF5155), location: 0.16), .init(color: Color(hex: 0xFF4447), location: 0.5),
                                                         .init(color: Color(hex: 0xFF3C3D), location: 1)], startPoint: .top, endPoint: .bottom))
                }
                .frame(width: disc - 6.6, height: disc - 5.4).offset(y: -0.6)
                PolishCross().frame(width: d * 0.60, height: d * 0.60).offset(y: -d * 0.01)
            }
            .frame(width: d, height: d)
        }
    }
}

private struct PolishCross: View {
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let bar = RoundedRectangle(cornerRadius: w * 0.13)
            ZStack {
                ForEach([45.0, -45.0], id: \.self) { a in bar.fill(Color(hex: 0x670202)).frame(width: w * 1.04, height: w * 0.4).rotationEffect(.degrees(a)).offset(y: w * 0.06) }
                ForEach([45.0, -45.0], id: \.self) { a in bar.fill(Color(hex: 0x730606)).frame(width: w * 1.04, height: w * 0.4).rotationEffect(.degrees(a)) }
                ForEach([45.0, -45.0], id: \.self) { a in bar.fill(Color(hex: 0xFFE9E9)).frame(width: w * 0.93, height: w * 0.29).rotationEffect(.degrees(a)) }
            }
            .frame(width: w, height: w)
        }
    }
}

// MARK: - wide button: body = the frame (as the shell); a recessed WELL outside it; side rim = the face darkened (not dark
// green); lip gradient at the bottom only; a thin light edge on the sides; the glare only across the top
struct PolishButtonColors {
    var outline: UInt32, rim: [(UInt32, Double)], face: [(UInt32, Double)], edge: UInt32, glare: UInt32
    static let green = PolishButtonColors(outline: 0x0B3A00,
        rim: [(0x029A0A, 0), (0x02A80A, 0.45), (0x02A00A, 0.7), (0x01980A, 0.8), (0x018C01, 0.88), (0x007D00, 0.92), (0x006600, 0.955), (0x004900, 1)],
        face: [(0x02E110, 0), (0x02E110, 0.06), (0x00E900, 0.12), (0x00E700, 0.18), (0x00E300, 0.3), (0x00DF00, 0.42), (0x00D500, 0.75), (0x00CF00, 0.9), (0x00CB00, 1)],
        edge: 0x8CF88C, glare: 0x91FC92)
    static let red = PolishButtonColors(outline: 0x4E0103,
        rim: [(0xE02628, 0), (0xF22E30, 0.4), (0xE8202A, 0.7), (0xD0101A, 0.8), (0xB00203, 0.88), (0xA00000, 0.92), (0x8D0000, 0.96), (0x6A0001, 1)],
        face: [(0xFF5357, 0), (0xFD4D51, 0.14), (0xFA3E41, 0.3), (0xF83133, 0.43), (0xF4161C, 0.62), (0xF10A16, 0.73), (0xEE0A13, 0.85), (0xEA060F, 1)],
        edge: 0xFD6F74, glare: 0xFF7378)
}

struct PolishButtonFace: View {
    var colors: PolishButtonColors = .green
    var n: CGFloat = 4.6
    var body: some View { GeometryReader { geo in art(geo.size) } }

    @ViewBuilder private func art(_ s: CGSize) -> some View {
        let W = s.width, H = s.height
        let shape = Superellipse(n: n), face = Superellipse(n: 3.9)
        let grad = { (st: [(UInt32, Double)]) in
            LinearGradient(stops: st.map { .init(color: Color(hex: $0.0), location: $0.1) }, startPoint: .top, endPoint: .bottom)
        }
        let u = H / 89
        // face inset from the body (007): sides 6.0, top 1.6, bottom 10.8 (at 89 pt)
        let fx = 6.0 * u, top = 1.6 * u, bottom = 10.8 * u
        ZStack(alignment: .topLeading) {
            shape.fill(Color(hex: colors.outline))
            ZStack {
                shape.fill(grad(colors.rim))
                shape.stroke(Color(hex: colors.outline, 0.55), lineWidth: 2.4).blur(radius: 0.8).clipShape(shape)
            }
            .padding(0.8)
            ZStack {
                face.fill(grad(colors.face))
                // thin light edge down the sides only (none on top: the glare is there; none at the bottom)
                face.stroke(Color(hex: colors.edge), lineWidth: 2.6).blur(radius: 0.7).clipShape(face)
                    .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .white, location: 0.14),
                                                 .init(color: .white, location: 0.7), .init(color: .clear, location: 0.95)], startPoint: .top, endPoint: .bottom))
                // glare: 0.8 pt core 4.7 pt under the face top, following the top contour, soft 2 pt falloff below it
                face.stroke(Color(hex: colors.glare, 0.55), lineWidth: 2.2).blur(radius: 0.9)
                    .padding(EdgeInsets(top: 5.6 * u, leading: 2.0, bottom: H * 0.05, trailing: 2.0))
                    .mask(LinearGradient(stops: [.init(color: .white, location: 0), .init(color: .white, location: 0.1),
                                                 .init(color: .clear, location: 0.2)], startPoint: .top, endPoint: .bottom))
                face.stroke(Color(hex: colors.glare), lineWidth: 0.9)
                    .padding(EdgeInsets(top: 4.7 * u, leading: 1.6, bottom: H * 0.05, trailing: 1.6))
                    .mask(LinearGradient(stops: [.init(color: .white, location: 0), .init(color: .white, location: 0.08),
                                                 .init(color: .clear, location: 0.17)], startPoint: .top, endPoint: .bottom))
            }
            .frame(width: W - 2 * fx, height: H - top - bottom)
            .offset(x: fx, y: top)
        }
        .frame(width: W, height: H, alignment: .topLeading)
        // the well OUTSIDE the frame (negative padding: no layout change; the shell's Rasterized needs overflow: 4):
        // a 1.2 pt light rim #2A8BF9 and a 2.3 pt dark ring #1036AE -> #1848CE around the body
        .background {
            ZStack {
                shape.fill(Color(hex: 0x2A8BF9)).padding(-3.5).blur(radius: 0.5)
                shape.fill(LinearGradient(colors: [Color(hex: 0x1036AE), Color(hex: 0x1848CE)], startPoint: .top, endPoint: .bottom)).padding(-2.3)
            }
        }
        .accessibilityHidden(true)
    }
}
