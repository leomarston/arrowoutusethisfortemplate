import SwiftUI
import PathCore

// GAME G1 (SPEC-architecture §6.5 z-order). The level screen: the one app-lifetime board (z 0, edge to edge, ignoring the
// safe area), S2's HUD (z 1: coin group, back, the panel with the level tab + timer pill + hearts, pause, the two booster
// corners; it reads only HUDModel), S2's TutorialLayer (z 2: the "Tap to move!" caption + hand, driven by G2). The FX host
// (z 3), the popup host (z 4) and the toasts (z 5) are the root's (RootView), above every screen. The probe element and the
// debug overlay are the board's (`-pc.uitest 1`, `-pc.hud debug`).

struct GameScreen: View {
    let game: GameController
    @Environment(AppModel.self) private var app

    var body: some View {
        // FIX-2 A (V3-05): a LayerStack (RootView.swift), not a ZStack(alignment: .topLeading) — the same placement (each layer at
        // the origin, the full size proposed) without the explicit-alignment walk of the whole HUD subtree that the ZStack's
        // sizing ran inside the Play cut's commit (Time Profiler build/p/FIX2/A/tp/v2-tp1: 10 of the cut's 26 ms under
        // `_ZStackLayout.sizeThatFits` → `explicitAlignment`). A3 tried it once under host load and saw no change; re-measured
        // here by the cut's own main-thread CPU (CutProbe), A/B on one build machine state.
        LayerStack {
            PuzzleBoardHost(board: game.board)                  // the active module's board (ArrowEscape: the BoardEngine)
                .ignoresSafeArea()
            HUDView(model: app.hud, actions: HUDActions(back: { game.flow.back() }, pause: { game.flow.pause() },
                                                        booster: { game.boosterTapped($0) }))
            TutorialLayer(hint: game.hint)
        }
    }
}
