import Foundation
import UIKit
import AppTrackingTransparency
import FacebookCore
import PathCore

// META (OWNER 2026-09-29 19:33: "why not implement it now and submit it with version 1.0"; memory meta-ads-sdk: the owner's
// standing choice for advertised apps, which overrides the factory's no-analytics default for THIS app). Meta install
// attribution for the owner's app-install ads, adapted from template/App/Support/MetaAds.swift (built for subscription apps)
// to a coin game:
//   - the SDK (FacebookCore 18.1.1, project.yml) starts behind Loading with IDFA collection OFF; iOS 17+ makes the SDK read
//     App Tracking Transparency itself (its old `isAdvertiserTrackingEnabled` setter is ignored there, so it is not called);
//     `isAdvertiserIDCollectionEnabled` follows ATT: true only while ATT says .authorized (at start, on every activation, and
//     when the prompt is answered);
//   - activateApp on every `.active` (auto-log is OFF since RFIX, so this is the SDK's only activation call; the install
//     ping and the session events come from activateApp, not from auto-log);
//   - fb_mobile_purchase for EVERY completed coin / bundle transaction, once (PurchasePipeline reports a GRANTED transaction:
//     a replay grants nothing and reports nothing), with StoreKit's own price and currency from the transaction — and ONLY a
//     `.production` transaction (RFIX 2026-09-29): a sandbox purchase (TestFlight, App Review's test purchases) or an Xcode
//     StoreKit-test one is test money and is logged, never reported as revenue. The Meta dashboard's "Log in-app events
//     automatically" is OFF: the SDK's own purchase logging needs that server switch (app_events_feature_bitmask bit 1) AND
//     auto-log, and auto-log is OFF in the app (Info.plist + FacebookSink.start), so a purchase is logged once, here. That switch lives on Meta's server, so tools/meta_dashboard_check.py reads
//     it (the same unauthenticated app-settings request the SDK makes) and the fastlane store lanes refuse to build while it is ON;
//   - events that arrive before the SDK has started (a purchase delivered by Transaction.updates before boot step 4 decided
//     the mode, or in the 3 frames before FacebookSink starts) are QUEUED and handed on once the mode is known and the sink has
//     started (RFIX 2026-09-29: they used to be dropped as "not sent");
//   - fb_mobile_tutorial_completion when the FTUE ends: the first home arrival after the "Levels 1-4" → 5 → 6 chain
//     (`homeSeen`; once per install, `flags.seen "metaFTUE"`);
//   - fb_mobile_level_achieved for EVERY level won, fb_level = the number of the level just won (the "Levels 1-4" session
//     reports 1, 2, 3 and 4). Every level, not milestones: a campaign can then optimise on any depth ("reached level 10")
//     through a custom conversion on fb_level, and the volume is one small event per win;
//   - the ATT prompt (`TrackingPrompt`): ONCE, after the FTUE, at the end of a calm home visit; no primer screen.
// Which builds talk to Meta (`MetaAds.mode`): only a Release build on a real device run ("live"). DEBUG builds, the unit-test
// host, Release runs under -pc.uitest / -pc.capture / -pc.autoplay, and (RFIX 2026-09-29) EVERY Simulator run and EVERY
// Measure build (PC_MEASURE: the owner's phone-test build, bench.py, frame-watch runs) never initialise the SDK: their events
// go to the log ("log only") — test runs never put fake installs or level events into the app's Meta dataset. `-pc.meta live`
// forces live (a person checking Events Manager on purpose); `-pc.att 1` lets UI tests reach the ATT prompt.
// The client token: FacebookClientToken in the BUILT Info.plist (tools/meta_token.py, from the factory .env); a Release /
// Measure build without it fails at its first build phase, so a live mode with an empty token cannot ship.
// Log: `[PC][meta] …` (never the token).

// MARK: - what the store reports

/// A completed purchase as the attribution event needs it: StoreKit's recorded price and currency, never a hard-coded price
/// (the same coin pack is a different number in every storefront).
struct PurchaseValue: Equatable, Sendable {
    let productID: String
    let transactionID: String
    let amount: Decimal
    let currency: String                  // ISO 4217, from the transaction
    let quantity: Int
    /// Where StoreKit says the money came from (`Transaction.environment`). Only `.production` is revenue.
    let environment: StoreEnvironment
}

/// `AppStore.Environment` as the reporter needs it (RFIX 2026-09-29): production = real money; sandbox = TestFlight and App
/// Review's test purchases; xcode = a local StoreKit configuration / SKTestSession.
enum StoreEnvironment: String, Equatable, Sendable {
    case production, sandbox, xcode, unknown
}

/// Where the purchase pipeline reports a GRANTED purchase (MetaAds in the app, a recorder in the tests).
@MainActor protocol PurchaseReporting: AnyObject {
    func purchaseCompleted(_ value: PurchaseValue)
}

// MARK: - the events (pure; Tests/AppTests/MetaEventsTests.swift)

/// One app event as Meta receives it: the name, the value to sum and the parameters.
struct MetaEvent: Equatable {
    enum Value: Equatable {
        case text(String)
        case number(Int)
        var object: Any { switch self { case .text(let s): return s; case .number(let n): return NSNumber(value: n) } }
    }
    let name: String
    let valueToSum: Double?
    let parameters: [String: Value]
}

enum MetaEvents {
    static let purchaseName = "fb_mobile_purchase"                    // AppEvents.Name.purchased
    static let tutorialName = "fb_mobile_tutorial_completion"         // AppEvents.Name.completedTutorial
    static let levelName = "fb_mobile_level_achieved"                 // AppEvents.Name.achievedLevel
    static let currencyKey = "fb_currency"

    /// Real money? Only a `.production` transaction (RFIX 2026-09-29): sandbox / Xcode purchases are never revenue.
    static func isRevenue(_ v: PurchaseValue) -> Bool { v.environment == .production }

    /// A coin / bundle purchase: value = the transaction's price, currency = its ISO code. nil for a free or unpriced
    /// transaction (never revenue) and for a currency that is not a 3-letter code. (The environment is MetaAds' check.)
    static func purchase(_ v: PurchaseValue) -> MetaEvent? {
        let code = v.currency.uppercased()
        guard v.amount > 0, code.count == 3, code.allSatisfy({ $0.isASCII && $0.isLetter }) else { return nil }
        return MetaEvent(name: purchaseName, valueToSum: NSDecimalNumber(decimal: v.amount).doubleValue, parameters: [
            currencyKey: .text(code),
            "fb_content_id": .text(v.productID),
            "fb_content_type": .text("product"),
            "fb_num_items": .number(max(1, v.quantity)),
        ])
    }

    /// The FTUE is over (the first home after "Levels 1-4" → 5 → 6).
    static func tutorialCompleted() -> MetaEvent {
        MetaEvent(name: tutorialName, valueToSum: nil, parameters: ["fb_success": .text("1"), "fb_content_id": .text("ftue")])
    }

    /// One won level (its number).
    static func levelAchieved(_ level: Int) -> MetaEvent {
        MetaEvent(name: levelName, valueToSum: nil, parameters: ["fb_level": .text(String(level))])
    }
}

// MARK: - which runs talk to Meta

enum MetaMode: String, Equatable {
    case live           // the SDK is initialised and receives the events
    case logOnly        // nothing leaves the device; the events are logged (DEBUG, tests, captures, the bot)
    case off            // no credentials in this build (a DEBUG build without the token, a verification build)
}

/// The Meta credentials of THIS build, read from its Info.plist (the token's value is never kept here, only whether it is
/// well formed).
struct MetaCredentials: Equatable {
    let appID: String
    let tokenWellFormed: Bool

    init(appID: String, tokenWellFormed: Bool) { self.appID = appID; self.tokenWellFormed = tokenWellFormed }

    init(info: [String: Any]?) {
        appID = info?["FacebookAppID"] as? String ?? ""
        let token = info?["FacebookClientToken"] as? String ?? ""
        tokenWellFormed = token.count == 32 && token.allSatisfy { $0.isHexDigit && !$0.isUppercase }
    }

    var isValid: Bool { appID.count >= 10 && appID.allSatisfy(\.isNumber) && tokenWellFormed }
}

extension MetaMode {
    /// `release` = a Release / Measure build; `quiet` = -pc.uitest / -pc.capture; `metaArg` = -pc.meta; `simulator` = a
    /// Simulator process (targetEnvironment(simulator)); `measure` = the Measure configuration (PC_MEASURE).
    static func choose(release: Bool, credentials: MetaCredentials, quiet: Bool, autoplay: Bool, metaArg: String?,
                       unitTestHost: Bool, simulator: Bool, measure: Bool) -> MetaMode {
        if unitTestHost { return .logOnly }                                  // never the SDK inside the unit-test host
        guard credentials.isValid else { return release ? .off : .logOnly }
        if metaArg == "live" { return .live }
        if metaArg == "off" { return .logOnly }
        if !release { return .logOnly }                                      // DEBUG: developer devices, UI tests
        // RFIX 2026-09-29: with the real token in every Release / Measure product, flags alone decided "live": a bench.py
        // Measure launch on the Simulator, an argument-free Release smoke launch, the owner's PH-2/PH-3 Measure runs all fed
        // fake installs and level events into the dataset. A Simulator is never a person's install; a Measure build is the
        // test build by definition (the store build is Release).
        if simulator || measure { return .logOnly }
        if quiet || autoplay { return .logOnly }                             // store captures, the bot
        return .live
    }
}

// MARK: - the SDK behind a protocol

@MainActor protocol MetaEventSink: AnyObject {
    /// Initialises the SDK (idempotent). `idfa`: collect the advertising identifier (ATT .authorized).
    func start(idfa: Bool)
    func activate()
    func log(_ event: MetaEvent)
    func setIDFACollection(_ on: Bool)
}

/// The Facebook SDK (FacebookCore). Only ever created in `.live` mode.
@MainActor final class FacebookSink: MetaEventSink {
    private(set) var started = false

    func start(idfa: Bool) {
        guard !started else { return }
        started = true
        let s = Settings.shared
        // before the SDK initialises: no IDFA unless ATT already said yes (the Info.plist says false too)
        s.isAdvertiserIDCollectionEnabled = idfa
        // RFIX 2026-09-29 (orchestrator 23:49): auto-log OFF (Info.plist says the same), so the SDK never starts its own
        // StoreKit purchase logging next to fb_mobile_purchase, whatever the dashboard's "Log in-app events automatically"
        // says. Installs and sessions do not depend on it: activate() calls activateApp on every activation. (A server-sent
        // auto_log_app_events_enabled overrides this: tools/meta_dashboard_check.py gates the store lanes on it.)
        s.isAutoLogAppEventsEnabled = false
        ApplicationDelegate.shared.application(UIApplication.shared, didFinishLaunchingWithOptions: nil)
    }

    func activate() {
        guard started else { return }
        AppEvents.shared.activateApp()
    }

    func log(_ event: MetaEvent) {
        guard started else { return }
        var params: [AppEvents.ParameterName: Any] = [:]
        for (k, v) in event.parameters where k != MetaEvents.currencyKey { params[AppEvents.ParameterName(k)] = v.object }
        if event.name == MetaEvents.purchaseName, let amount = event.valueToSum,
           case .text(let currency)? = event.parameters[MetaEvents.currencyKey] {
            AppEvents.shared.logPurchase(amount: amount, currency: currency, parameters: params)
        } else if let v = event.valueToSum {
            AppEvents.shared.logEvent(AppEvents.Name(event.name), valueToSum: v, parameters: params)
        } else {
            AppEvents.shared.logEvent(AppEvents.Name(event.name), parameters: params)
        }
    }

    func setIDFACollection(_ on: Bool) {
        guard started else { return }
        Settings.shared.isAdvertiserIDCollectionEnabled = on
    }
}

/// Nothing leaves the device: the event is logged.
@MainActor final class LogSink: MetaEventSink {
    func start(idfa: Bool) {}
    func activate() {}
    func log(_ event: MetaEvent) {}
    func setIDFACollection(_ on: Bool) {}
}

// MARK: - the app's Meta reporter

@MainActor final class MetaAds: PurchaseReporting {
    static let shared = MetaAds()

    private(set) var mode: MetaMode = .off
    private var sink: MetaEventSink = LogSink()
    private var configured = false
    /// The last events handed on (tests and the log; at most 50).
    private(set) var recent: [MetaEvent] = []
    /// Live mode waits this long after an event before calling the SDK, so a win's banking frame or a purchase's grant
    /// frame never pays for it (0 in tests).
    var deferral: Double = 0.4

    init() {}

    /// Tests: a chosen mode and a sink that is already started.
    init(mode: MetaMode, sink: MetaEventSink) {
        deferral = 0
        configure(mode: mode, sink: sink, started: true)
    }

    /// Boot step 4 (G2App.bootBegan, behind Loading): decides the mode and, when live, starts the SDK a few frames later,
    /// off the boot's own frames. Once per run. Events that arrived earlier are queued and handed on (`sinkStarted`).
    func boot(_ app: AppModel) {
        guard !configured else { return }
        let args = app.args
        let release: Bool = {
            #if DEBUG
            return false
            #else
            return true
            #endif
        }()
        let simulator: Bool = {
            #if targetEnvironment(simulator)
            return true
            #else
            return false
            #endif
        }()
        let measure: Bool = {
            #if PC_MEASURE
            return true
            #else
            return false
            #endif
        }()
        let creds = MetaCredentials(info: Bundle.main.infoDictionary)
        let chosen = MetaMode.choose(release: release, credentials: creds, quiet: args.quietUI, autoplay: args.autoplay,
                                     metaArg: args.raw["pc.meta"], unitTestHost: NotificationPrompt.isUnitTestHost,
                                     simulator: simulator, measure: measure)
        Log.mark("meta", "mode \(chosen.rawValue) (\(release ? (measure ? "measure" : "release") : "debug") build"
                 + "\(simulator ? ", no device" : ""), app id \(creds.appID.isEmpty ? "none" : "set"), "
                 + "client token \(creds.tokenWellFormed ? "present" : "absent"), ATT \(TrackingPrompt.statusName(TrackingPrompt.status)))")
        guard chosen == .live else {
            configure(mode: chosen, sink: LogSink(), started: true)
            return
        }
        let live = FacebookSink()
        configure(mode: .live, sink: live, started: false)
        Task { @MainActor in
            await FrameWaiter.frames(3)
            let t0 = ProcessInfo.processInfo.systemUptime
            live.start(idfa: TrackingPrompt.status == .authorized)
            live.activate()
            Log.mark("meta", String(format: "SDK started in %.1f ms (IDFA collection %@)", (ProcessInfo.processInfo.systemUptime - t0) * 1000,
                                    TrackingPrompt.status == .authorized ? "on" : "off"))
            self.sinkStarted()
        }
    }

    /// The mode is decided (boot, or a test). `started`: the sink can take events now (log-only / off / a test sink);
    /// false for the live FacebookSink until `sinkStarted()`.
    func configure(mode: MetaMode, sink: MetaEventSink, started: Bool) {
        self.mode = mode
        self.sink = sink
        configured = true
        if started { sinkStarted() }
    }

    /// The sink has started: the queued events go on, in order (live: to Meta; log-only: the log; off: nowhere).
    func sinkStarted() {
        sinkReady = true
        guard !pending.isEmpty else { return }
        let queued = pending
        pending = []
        Log.mark("meta", "\(queued.count) event(s) queued before Meta started: handed on now")
        for (e, what) in queued { deliver(e, what + " (queued)") }
    }

    /// RFIX 2026-09-29: before the mode is known (ShopStore listens to Transaction.updates from AppModel's init, before boot
    /// step 4) and before the live sink has started (FacebookSink drops events until `start`), events wait here instead of
    /// being dropped. Bounded: a run that never boots (a unit-test host) keeps only the newest.
    private var pending: [(MetaEvent, String)] = []
    private var sinkReady = false
    static let pendingLimit = 100

    /// Every `.active` scene phase: a session for Meta, and the IDFA switch re-read from ATT (the person may have changed it
    /// in the iOS Settings app meanwhile).
    func activate() {
        guard mode == .live else { return }
        sink.setIDFACollection(TrackingPrompt.status == .authorized)
        sink.activate()
    }

    /// The ATT prompt was answered.
    func trackingAnswered(_ status: ATTrackingManager.AuthorizationStatus) {
        sink.setIDFACollection(status == .authorized)
        Log.mark("meta", "ATT answered: \(TrackingPrompt.statusName(status)); IDFA collection \(status == .authorized ? "on" : "off")")
    }

    // MARK: events

    func purchaseCompleted(_ value: PurchaseValue) {
        guard MetaEvents.isRevenue(value) else {
            Log.mark("meta", "purchase \(value.productID) tx \(value.transactionID) in the \(value.environment.rawValue) environment: "
                     + "test money (TestFlight / App Review / StoreKit testing), not reported to Meta")
            return
        }
        guard let e = MetaEvents.purchase(value) else {
            Log.error("meta", "purchase \(value.productID) tx \(value.transactionID): no price / currency, not reported")
            return
        }
        send(e, "purchase \(value.productID) \(value.amount) \(value.currency.uppercased()) tx \(value.transactionID)")
    }

    /// The first home arrival after the FTUE (HomeQueue, every arrival; logs once per install).
    func ftueEndedIfNeeded(_ store: PlayerStore) {
        let s = store.state
        guard s.homeSeen, !s.flags.seen.contains(Self.ftueKey) else { return }
        store.mutateAndSave { _ = $0.flags.seen.insert(Self.ftueKey) }
        send(MetaEvents.tutorialCompleted(), "tutorial completed (the FTUE's first home, level \(s.level))")
    }

    static let ftueKey = "metaFTUE"

    /// A won Play (MetaDirector, when the win is banked): one event per level of the session.
    func levelsWon(_ levels: [Int]) {
        for n in levels where n > 0 { send(MetaEvents.levelAchieved(n), "level achieved \(n)") }
    }

    private func send(_ e: MetaEvent, _ what: String) {
        recent.append(e)
        if recent.count > 50 { recent.removeFirst(recent.count - 50) }
        guard configured, sinkReady else {
            pending.append((e, what))
            if pending.count > Self.pendingLimit {
                Log.error("meta", "\(pending.count - Self.pendingLimit) queued event(s) dropped: Meta never started in this run")
                pending.removeFirst(pending.count - Self.pendingLimit)
            }
            Log.mark("meta", "\(what): queued until Meta starts (\(configured ? "the SDK is starting" : "the mode is not decided yet"))")
            return
        }
        deliver(e, what)
    }

    /// Hands one event on in the decided mode, to a started sink.
    private func deliver(_ e: MetaEvent, _ what: String) {
        switch mode {
        case .off:
            Log.mark("meta", "\(what): not sent (no Meta credentials in this build)")
            return
        case .logOnly:
            Log.mark("meta", "\(what): log only (\(e.name))")
            sink.log(e)                                   // a test sink records it; LogSink drops it
            return
        case .live:
            Log.mark("meta", "\(what) → Meta (\(e.name))")
        }
        let sink = self.sink
        if deferral <= 0 { sink.log(e); return }
        let delay = UInt64(deferral * 1_000_000_000)
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: delay)
            sink.log(e)
        }
    }
}

// MARK: - level wins

/// Reports every banked win (the session's levels) to MetaAds. Installed with G2's directors.
@MainActor final class MetaDirector: GameDirector {
    unowned let game: GameController

    init(_ game: GameController) { self.game = game }

    func handle(_ events: [SessionEvent], game: GameController) {
        for e in events {
            if case .won = e { MetaAds.shared.levelsWon(game.plan.levels) }
        }
    }
}

// MARK: - the App Tracking Transparency prompt

/// ONCE per install — iOS's own one-shot is the guard: the status leaves .notDetermined when the person answers — after the
/// FTUE (home seen, level ≥ the FTUE chain's end), at the END of a calm home visit (HomeQueue: after the payout, the claims,
/// the pages and the rating step), never in the visit that showed the rating sheet, never over a popup, never while the
/// Loading / a level / the tutorial is on screen. No primer screen: the system alert with NSUserTrackingUsageDescription
/// (neutral, 13 languages). It never blocks play: the home queue does not wait for the answer; the answer only switches IDFA
/// collection. If iOS returns .notDetermined (the app was not active, so no alert appeared) the next calm visit asks again.
/// RFIX 2026-09-29: no marker is saved any more. The old `flags.seen "attAsked"` was written BEFORE the request, so a process
/// that died with the alert up (killed from the app switcher, a crash) kept the marker while iOS still said .notDetermined:
/// the person was never asked again and IDFA stayed off for good. A marker left by an earlier build is ignored; one request
/// per process (`requestedThisRun`) keeps a second visit of the same run from asking while the first alert is up.
@MainActor enum TrackingPrompt {
    /// The key older builds saved before asking. Ignored (see above); kept only so the tests can prove it no longer silences iOS.
    static let legacyAskedKey = "attAsked"

    /// A request is in flight or was made in this process (reset when iOS showed nothing because the app was not active).
    private(set) static var requestedThisRun = false

    static var status: ATTrackingManager.AuthorizationStatus { ATTrackingManager.trackingAuthorizationStatus }

    static func statusName(_ s: ATTrackingManager.AuthorizationStatus) -> String {
        switch s {
        case .notDetermined: return "not determined"
        case .restricted: return "restricted"
        case .denied: return "denied"
        case .authorized: return "authorized"
        @unknown default: return "unknown"
        }
    }

    struct Inputs: Equatable {
        var allowed: Bool               // live mode, or -pc.att 1 (UI tests); never in the unit-test host
        var homeSeen: Bool
        var level: Int
        var ftueEndsAtLevel: Int        // game.json ftue.chainUntilLevel (7): the first level played from home
        var askedThisRun: Bool          // a request already made in this process
        var notDetermined: Bool         // iOS has no answer yet: the once-per-install guard
        var ratedThisVisit: Bool
    }

    /// Pure: is the prompt due now?
    static func isDue(_ i: Inputs) -> Bool {
        i.allowed && i.homeSeen && i.level >= i.ftueEndsAtLevel && !i.askedThisRun && i.notDetermined && !i.ratedThisVisit
    }

    /// Pure: the inputs from the saved player state (nothing in it but the FTUE progress counts: no saved marker).
    static func inputs(_ s: PlayerState, allowed: Bool, ftueEndsAtLevel: Int, askedThisRun: Bool, notDetermined: Bool,
                       ratedThisVisit: Bool) -> Inputs {
        Inputs(allowed: allowed, homeSeen: s.homeSeen, level: s.level, ftueEndsAtLevel: ftueEndsAtLevel, askedThisRun: askedThisRun,
               notDetermined: notDetermined, ratedThisVisit: ratedThisVisit)
    }

    /// Pure: live mode, or -pc.att 1 (UI tests reach the prompt without sending anything); never in the unit-test host.
    static func allowed(mode: MetaMode, attArg: String?, unitTestHost: Bool) -> Bool {
        guard !unitTestHost else { return false }
        return mode == .live || attArg == "1"
    }

    static func allowed(_ app: AppModel) -> Bool {
        allowed(mode: MetaAds.shared.mode, attArg: app.args.raw["pc.att"], unitTestHost: NotificationPrompt.isUnitTestHost)
    }

    /// The home queue's last step. `note` = the queue's trail.
    static func askIfDue(_ app: AppModel, ratedThisVisit: Bool, note: (String) -> Void) {
        let s = app.store.state
        let i = inputs(s, allowed: allowed(app), ftueEndsAtLevel: app.tuning.game.ftueChainUntilLevel, askedThisRun: requestedThisRun,
                       notDetermined: status == .notDetermined, ratedThisVisit: ratedThisVisit)
        guard isDue(i) else { return }
        guard UIApplication.shared.applicationState == .active else {
            note("tracking prompt due, the app is not active: the next calm visit asks")
            return
        }
        requestedThisRun = true
        note("tracking prompt (ATT) at the end of the visit, level \(s.level)")
        Log.mark("meta", "ATT prompt requested (once per install: iOS keeps the answer), after the FTUE, level \(s.level)")
        Task { @MainActor in
            let answer = await ATTrackingManager.requestTrackingAuthorization()
            if answer == .notDetermined {
                requestedThisRun = false
                Log.mark("meta", "ATT: iOS showed no alert (not active); asked again at a later calm visit")
            }
            MetaAds.shared.trackingAnswered(answer)
        }
    }
}
