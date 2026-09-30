// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import SwiftUI
import PathCore

// SHELL S1 debug host (SPEC-architecture §9.5): `-pc.go shelllab -pc.lab <page>`, pages:
//   text        GameText at the measured styles (Paused, Play, Level 32, 3:00, Resume, Quit, ON, Sound, LEVEL, 33, Loading) +
//               the Turkish coverage line and TR samples set verbatim (they draw without the strings catalogue)
//   components  the chrome: square buttons, the HUD heart, Resume/Quit, wide faces (green/red/purple/blue), toggles ON/OFF,
//               the close X, the card, the arched ribbon, pills, tag ribbons, the panel frame
//   puppets     each rig's full render (left) next to its rest-pose recomposition by PuppetStage (right), then the live loops
// Each page writes Documents/lab-ready.json ({screen, t, lang, frozen}) 2 frames after it appears (the capture contract,
// §9.2 / §9.5). S2 / S3 add their pages (HUD states, win panels, unlock overlays) to `ShellDebugScreens`.

@MainActor enum ShellDebugScreens {
    static func make(_ name: String, app: AppModel) -> AnyView? {
        guard name == "shelllab" else { return nil }
        if let s2 = S2Lab.make(app.args.lab, app: app) { return s2 }                // S2 hook (Popups/ShellLab+Popups.swift)
        if let s3 = S3Lab.make(app.args.lab, app: app) { return s3 }                // S3 hook (Home/ShellLab+Home.swift)
        let page = ShellLab.Page(rawValue: app.args.lab ?? "text") ?? .text
        return AnyView(ShellLab(page: page))
    }
}

extension ShellEntry {
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { ShellDebugScreens.make(name, app: app) }
}

struct ShellLab: View {
    enum Page: String, CaseIterable { case text, components, puppets }
    let page: Page
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        ZStack(alignment: .topLeading) {
            (page == .puppets ? Color(hex: Skin.shellShellLabShellLab) : Color(hex: Skin.shellShellLabShellLabV2))
            ReferenceCanvas {
                // text / components: scaled 0.9 about the bottom so nothing sits under the Dynamic Island
                switch page {
                case .text: textPage(t).frame(width: 393, height: 852, alignment: .topLeading).scaleEffect(0.9, anchor: .bottom)
                case .components: componentsPage(t).frame(width: 393, height: 852, alignment: .topLeading).scaleEffect(0.9, anchor: .bottom)
                case .puppets: PuppetsPage()
                }
            }
        }
        .frame(width: m.size.width, height: m.size.height)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            if page == .components { app.toasts.show("Allow notifications in iOS Settings.") }   // the toast plate (SPEC-ui §2.20)
            await FrameWaiter.frames(3)
            CaptureReady.mark(screen: "shelllab:\(page.rawValue)", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:\(page.rawValue) done")
        }
    }

    // MARK: text

    @ViewBuilder private func textPage(_ t: Tokens) -> some View {
        let title = t.text("popup.title", GameTextStyle(size: 49.2, tracking: -1.0, fill: [.white], outline: Color(hex: Skin.shellShellLabPopupTitleOutline),
                                                         outlineWidth: 1.87, drop: 3.15, band: Color(hex: Skin.shellShellLabPopupTitleBand), bandDY: 1.5))
        let play = t.text("home.play", GameTextStyle(size: 48.8, tracking: -3.25, fill: [Color(hex: Skin.shellShellLabHomePlayFill0)], outline: Color(hex: Skin.shellShellLabHomePlayOutline),
                                                     outlineWidth: 2.2, drop: 2.2))
        let tab = GameTextStyle(size: 17.9, tracking: -0.5, fill: [Color(hex: Skin.shellShellLabShellLabTextPageTabFill0), Color(hex: Skin.shellShellLabShellLabTextPageTabFill1), Color(hex: Skin.shellShellLabShellLabTextPageTabFill2)],
                                outline: Color(hex: Skin.shellShellLabShellLabTextPageTabOutline), outlineWidth: 0.65, drop: 0.73)
        let timer = GameTextStyle(size: 23.3, tracking: 0.25, fill: [Color(hex: Skin.shellShellLabShellLabTextPageTimerFill0), Color(hex: Skin.shellShellLabShellLabTextPageTimerFill1), Color(hex: Skin.shellShellLabShellLabTextPageTimerFill2)],
                                  outline: Color(hex: Skin.shellShellLabShellLabTextPageTimerOutline), outlineWidth: 0.67, drop: 1.13)
        let resume = t.text("pause.resume", GameTextStyle(size: 30.5, tracking: -1))
        let quit = t.text("pause.quit", GameTextStyle(size: 30.5, tracking: -0.5))
        let row = t.text("pause.rowLabel", GameTextStyle(size: 25.5, fill: [Color(hex: Skin.shellShellLabPauseRowLabelFill0)]))
        let on = t.text("pause.toggleOn", GameTextStyle(size: 21, tracking: -0.75))
        let caption = t.text("home.levelCaption", GameTextStyle(size: 14.1, tracking: -1.5))
        let number = t.text("home.levelNumber", GameTextStyle(size: 30.6, tracking: -1.5))
        let loading = t.text("loading.label", GameTextStyle(size: 26.8, tracking: -0.5))
        ZStack(alignment: .topLeading) {
            Color(hex: Skin.shellShellLabShellLabTextPage).placed(CGRect(0, 0, 393, 150))
            GameText(verbatim: "Paused", style: title, maxWidth: 228).at(196.5, title.capCentre(baseline: 60)).accessibilityIdentifier("lab.paused")
            GameText(verbatim: "Play", style: play, maxWidth: 175).at(196.5, play.capCentre(baseline: 128)).accessibilityIdentifier("lab.play")
            GameText(verbatim: "Level 32", style: tab).at(80, tab.capCentre(baseline: 190))
            GameText(verbatim: "3:00", style: timer).at(200, timer.capCentre(baseline: 192))
            GameText(verbatim: "LEVEL", style: caption).at(290, caption.capCentre(baseline: 180))
            GameText(verbatim: "33", style: number).at(290, number.capCentre(baseline: 212))
            GameText(verbatim: "Resume", style: resume, maxWidth: 100).at(80, resume.capCentre(baseline: 250))
            GameText(verbatim: "Quit", style: quit, maxWidth: 100).at(200, quit.capCentre(baseline: 250))
            GameText(verbatim: "ON", style: on).at(300, on.capCentre(baseline: 250))
            Color(hex: Skin.shellShellLabShellLabTextPage).placed(CGRect(0, 270, 393, 50))
            GameText(verbatim: "Sound", style: row).at(90, row.capCentre(baseline: 305))
            GameText(verbatim: "Haptic", style: row).at(250, row.capCentre(baseline: 305))
            GameText(verbatim: "Loading...", style: loading).at(196.5, loading.capCentre(baseline: 360))
            // Turkish: coverage + samples at the same styles (shrink-to-fit at min 0.7)
            GameText(verbatim: "ıİşŞğĞüÜöÖçÇ 0123456789", style: row.sized(24)).at(196.5, row.capCentre(baseline: 430))
                .accessibilityIdentifier("lab.coverage")
            GameText(verbatim: "Duraklatıldı", style: title, maxWidth: 228).at(196.5, title.capCentre(baseline: 500))
            GameText(verbatim: "Oyna", style: play, maxWidth: 175).at(110, play.capCentre(baseline: 570))
            GameText(verbatim: "Devam", style: resume, maxWidth: 100).at(290, resume.capCentre(baseline: 570))
            GameText(verbatim: "Çıkılsın mı?", style: title, maxWidth: 228).at(196.5, title.capCentre(baseline: 640))
            GameText(verbatim: "Bir can kaybedeceksin!", style: t.text("quit.message", GameTextStyle(size: 25.4)), maxWidth: 340)
                .at(196.5, row.capCentre(baseline: 690))
            GameText(verbatim: "Yükleniyor...", style: loading).at(196.5, loading.capCentre(baseline: 740))
            GameText("Paused", style: title.sized(30)).at(196.5, title.capCentre(baseline: 800))
                .accessibilityIdentifier("lab.pausedLocalized")
        }
    }

    // MARK: components

    @ViewBuilder private func componentsPage(_ t: Tokens) -> some View {
        ZStack(alignment: .topLeading) {
            BlueSquareButton { PauseGlyph() }.at(40, 40)
            BlueSquareButton { ArtImage(art: .glyphGear).frame(width: 26, height: 26) }.at(95, 40)
            HeartHUD().at(145, 40)
            ArtImage(art: .heartLives).placed(CGRect(170, 22, 39, 33))
            TopPill(t: t).placed(CGRect(220, 26, 76.7, 27.4))
            PopupCloseButton(id: "lab.close", t: t) {}.placed(CGRect(320, 17, 45.4, 45))
            PanelButton(colors: .green).at(80, 120)
            PanelButton(colors: .red).at(215, 120)
            ChromeButtonFace(colors: .green, n: 4.7).placed(CGRect(290, 80, 90, 40))
            ChromeButtonFace(colors: .red, n: 4.6).placed(CGRect(290, 125, 90, 40))
            ChromeButtonFace(colors: ChromePalette.purple, n: 4.6).placed(CGRect(20, 175, 170, 50))
            ChromeButtonFace(colors: ChromePalette.blue, n: 4.0).placed(CGRect(205, 175, 90, 50))
            PopupToggle(id: "lab.toggle.on", isOn: true, t: t) {}.placed(CGRect(20, 245, 116.1, 37.4))
            PopupToggle(id: "lab.toggle.off", isOn: false, t: t) {}.placed(CGRect(150, 245, 116.1, 37.4))
            BlueCard(t: t).placed(CGRect(275, 232, 110, 64))
            PopupToggle(id: "lab.toggle.offBlue", isOn: false, t: t, well: .blue) {}.placed(CGRect(283, 245, 94, 34))
            PopupCard(t: t).placed(CGRect(20, 300, 160, 110))
            PopupRibbon(t: t).placed(CGRect(190, 300, 190, 70))
            DifficultyTag(tag: .hard).placed(CGRect(20, 425, 120.1, 30))
            DifficultyTag(tag: .superHard).placed(CGRect(150, 425, 120.1, 30))
            ShellSquareToggle(id: "lab.square.on", glyph: .glyphSound, isOn: true, t: t) {}.placed(CGRect(290, 410, 66.1, 65.7))
            ShellSquareToggle(id: "lab.square.off", glyph: .glyphMusic, isOn: false, t: t) {}.placed(CGRect(290, 490, 66.1, 65.7))
            PillLinkButton(id: "lab.pill", title: "Terms", style: t.text("settings.link", GameTextStyle(size: 22.3)), t: t) {}
                .placed(CGRect(150, 480, 121.8, 49))
            BandPopupFrame(t: t).placed(CGRect(0, 545, 393, 280))
            PopupCloseButton(id: "lab.close.halo", t: t, halo: true) {}.placed(CGRect(30, 480, 45, 45))
        }
    }
}

/// Each rig's full render next to PuppetStage's rest-pose recomposition, then the live idle loops.
private struct PuppetsPage: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        let rigs = [HomeView.bossRig, HomeView.diggerLeftRig, HomeView.diggerRightRig].compactMap { PuppetCache.rig($0) }   // A4: the D1 rigs
        ZStack(alignment: .topLeading) {
            ForEach(Array(rigs.enumerated()), id: \.offset) { i, rig in
                let y = 20 + CGFloat(i) * 175
                let k = min(1, 160 / rig.frame.height, 180 / rig.frame.width)
                if let full = rig.fullPath {
                    PathImage(path: full).frame(width: rig.frame.width * k, height: rig.frame.height * k).at(100, y + 80)
                }
                PuppetStage(rig: rig, motion: .none, clock: app.clock, animate: false, freezeAt: nil)
                    .frame(width: rig.frame.width, height: rig.frame.height)
                    .scaleEffect(k)
                    .at(290, y + 80)
            }
            // the live loops, at scene scale
            ForEach(Array(rigs.enumerated()), id: \.offset) { i, rig in
                PuppetStage(rig: rig, motion: PuppetMotion(app.tuning.ui.file, rig: rig.name), clock: app.clock, animate: true, freezeAt: nil)
                    .frame(width: rig.frame.width, height: rig.frame.height)
                    .scaleEffect(0.5)
                    .at(70 + CGFloat(i) * 125, 610 + 110)
            }
        }
    }
}
#endif
