import SwiftUI
import PathCore

// Kit component `home` (kit/screens/home): the home screen for the router's `.home` layers, the hooks the router, the root
// view and the social / Shop tabs use to reach home's parked state (HomeLive, HomeTabStrip, HomeBuild, HomeScene,
// PayoutSequence, HomeLevelInfo — named directly by Router.swift and RootView.swift until the kit decoupling step), and home's
// art (kept by the event-art policy; decoded off the main thread from the router's creation, after the Shop page's).
// GameComponents.swift lists it.

@MainActor enum HomeRegistration {
    static func register() {
        ShellScreens.registerHome(HomeScreenAdapter())
        ShellArt.registerKept { HomeView.art }
        ShellArt.registerPreload(order: 20) { HomeView.art }
    }
}

/// `HomeScreenHooks` over home's own singletons: every member is the call the router / root view / pages made before.
@MainActor final class HomeScreenAdapter: HomeScreenHooks {
    func makeView(tab: HomeTab, refill: Int) -> AnyView { AnyView(HomeView(tab: tab, refill: refill)) }
    func state(_ app: AppModel) -> PlayerState { HomeLive.read(app) }
    var isActive: Bool { HomeLive.shared.active }
    var eventsDrawnAt: Date? { HomeLive.shared.eventsDrawnAt }
    func isTabShown(_ tab: HomeTab) -> Bool { HomeTabStrip.shared.shown.contains(tab) }
    func syncState() { HomeLive.shared.sync() }
    func requestRefill() { HomeScene.requestRefill() }
    func takeRefill() -> Bool { HomeScene.takeRefill() }
    func attach(_ store: PlayerStore) { HomeLive.shared.attach(store) }
    var arrivalStale: Bool { HomeLive.shared.arrivalStale }
    @discardableResult func prepareArrival() -> Bool { HomeLive.shared.prepareArrival() }
    func mountTabs() { HomeLive.shared.mountTabs() }
    func arrive(_ entry: HomeEntry, arrival: Int) { HomeLive.shared.arrive(entry, arrival: arrival) }
    func park() { HomeLive.shared.park() }
    func resume() { HomeLive.shared.resume() }
    func slideTab(to tab: HomeTab, ui: UITuning) { HomeTabStrip.shared.slide(to: tab, ui: ui) }
    func jumpTab(to tab: HomeTab) { HomeTabStrip.shared.jump(to: tab) }
    func beginBuild() { HomeBuild.shared.begin() }
    var isBuilding: Bool { HomeBuild.shared.building }
    func buildStep() { HomeBuild.shared.step() }
    func finishBuild() { HomeBuild.shared.finish() }
    func cancelPayout() { PayoutSequence.cancel() }
    func prefetchLevel(_ level: Int, args: LaunchArgs) { HomeLevelInfo.prefetch(level, args: args) }
    func rigLayerPaths() -> [String] { HomeView.rigLayerPaths() }
    func probeTabCommits() { HomeTabStrip.shared.probeCommits = true }
}
