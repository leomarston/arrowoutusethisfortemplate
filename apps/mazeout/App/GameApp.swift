import SwiftUI
import UIKit
import PathCore

// LEAD, WP0, frozen (SPEC-architecture §2.1, §3.2, §6.1). Builds the one AppModel, injects it, runs the boot sequence
// behind the first frame, and forwards scene-phase changes. The root view is SHELL's (`ShellEntry.makeRoot`); until
// SHELL plugs in, it is the WP0 placeholder below (Debug builds only since F3-A, ruling 52(a)). No NavigationStack; a
// fixed light palette; no status bar.

@main
struct GameApp: App {
    @State private var app = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            app.rootView
                .environment(app)
                .environment(app.anchors)
                .environment(app.store)
                .environment(app.clock)
                .environment(app.hud)
                .preferredColorScheme(.light)          // the game has a fixed palette (§6.1)
                .statusBarHidden(true)                 // the original hides it on every screen (§0.3)
                .task { await app.boot() }
        }
        .onChange(of: scenePhase) { _, phase in app.scenePhaseChanged(phase) }
    }
}

// MARK: - WP0 placeholders (the default root until SHELL's RootView lands; never game content)
// F3-A (SPEC.md ruling 52(a), N-02): unreachable once SHELL is installed, so compiled into Debug only — a Release or
// Measure build has no placeholder screen to fall back to (ShellContract's makeRoot default is Debug-only too).

#if DEBUG

/// Shows the Loading placeholder while booting, then the boot placeholder: the brand from Info.plist, the fonts
/// resolved by PostScript name, the bundled folders, the player store, the current screen. `-pc.go <lab>` opens the
/// owners' debug hosts (BoardLab, SoundBoard, …) so BOARD and AUDIO can work before SHELL lands.
struct BootPlaceholderView: View {
    let app: AppModel

    var body: some View {
        let screen = app.router.screen
        Group {
            if screen == .loading {
                LoadingPlaceholderView()
            } else if case .lab(let id) = screen, let lab = DebugScreens.make(id.rawValue, app: app) {
                lab
            } else {
                diagnostics(screen)
                    .onAppear { Log.mark("launch", "\(screen.logName) fully visible") }
            }
        }
    }

    private func diagnostics(_ screen: Screen) -> some View {
        ZStack {
            Color.white.ignoresSafeArea()
            VStack(spacing: 16) {
                Text(verbatim: Brand.name)
                    .font(.custom(GameText.blackPostScript, fixedSize: 44))
                    .foregroundStyle(Color(.sRGB, red: 0x43 / 255.0, green: 0xAA / 255.0, blue: 0x99 / 255.0))
                    .accessibilityIdentifier("boot.brand")
                #if DEBUG
                VStack(alignment: .leading, spacing: 5) {
                    row("screen", screen.logName)
                    row("fonts", AppModel.fontNames.map { "\($0) \(app.fonts[$0] == true ? "ok" : "MISSING")" }
                        .joined(separator: "\n"))
                    Text(verbatim: GameText.italicPostScript + " sample")
                        .font(.custom(GameText.italicPostScript, fixedSize: 18))
                    row("tuning", app.tuning.loadedFiles.joined(separator: ", "))
                    row("bundle", AppModel.bundleSummary(app.bundle).map { "\($0.0) \($0.1)" }.joined(separator: " · "))
                    row("player", "level \(app.store.state.level) · coins \(app.store.state.coins) · lives \(app.store.state.lives.count)")
                    row("store", "\(app.store.loadSource.rawValue) · seed \(app.store.state.installSeed)")
                }
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(.black.opacity(0.75))
                .padding(12)
                .background(Color.black.opacity(0.05), in: RoundedRectangle(cornerRadius: 10))
                Text(verbatim: "WP0 scaffold: boot placeholder")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.black.opacity(0.45))
                #endif
            }
            .padding(.horizontal, 16)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("boot.placeholder")
    }

    private func row(_ key: String, _ value: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(verbatim: key).frame(width: 52, alignment: .leading).opacity(0.6)
            Text(verbatim: value)
        }
    }
}

/// A plain Loading stand-in (the LaunchBackground colour + "Loading" with cycling dots in PCDisplay-Black); SHELL's
/// LoadingScreen (the loading art, our logo, the characters) replaces it.
struct LoadingPlaceholderView: View {
    var body: some View {
        ZStack(alignment: .bottom) {
            Color("LaunchBackground").ignoresSafeArea()
            TimelineView(.periodic(from: .now, by: 0.4)) { ctx in
                let n = Int(ctx.date.timeIntervalSinceReferenceDate / 0.4) % 3 + 1
                Text(verbatim: "Loading" + String(repeating: ".", count: n))
                    .font(.custom(GameText.blackPostScript, fixedSize: 26.8))
                    .foregroundStyle(Color(.sRGB, red: 0xCC / 255.0, green: 0xCC / 255.0, blue: 0xCC / 255.0))
                    .frame(width: 160, alignment: .leading)
            }
            .padding(.bottom, 46)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("loading.placeholder")
    }
}
#endif
