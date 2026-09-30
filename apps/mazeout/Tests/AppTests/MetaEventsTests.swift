import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// META (OWNER 2026-09-29 19:33, the Meta SDK in 1.0). What the game reports to Meta, with the SDK behind `MetaEventSink`
/// (a recording sink here; FacebookSink in a live Release run):
///  1. the purchase event carries the TRANSACTION's price and currency (fb_mobile_purchase, valueToSum, fb_currency), never a
///     catalogue price; a free / unpriced / oddly-coded transaction is not revenue and reports nothing;
///  2. the purchase pipeline reports a GRANTED transaction exactly once, after the grant is on disk and after RevenueCat's
///     record, before finish — never a replay, an unknown product, an unverified transaction or one without a recorded price;
///  3. the FTUE's end (fb_mobile_tutorial_completion) once per install, at the first home; every won level
///     (fb_mobile_level_achieved, fb_level = its number; the "Levels 1-4" session = four events);
///  4. which runs talk to Meta (`MetaMode.choose`): only a Release run with credentials and no test / capture / bot flag, on a
///     device, in the Release (not Measure) configuration;
///  5. the ATT prompt's moment (`TrackingPrompt.isDue`): after the FTUE, once, only while iOS has not been answered, never in
///     the visit that showed the rating sheet, never without live mode or -pc.att 1;
///  6. (RFIX 2026-09-29) only production money is revenue (sandbox / Xcode purchases are logged, never sent), and events that
///     arrive before the mode is decided or before the live SDK has started are queued and handed on, never dropped.
@MainActor final class MetaEventsTests: XCTestCase {

    // MARK: helpers

    final class RecordingSink: MetaEventSink {
        var starts: [Bool] = []
        var activations = 0
        var events: [MetaEvent] = []
        var idfa: [Bool] = []
        func start(idfa: Bool) { starts.append(idfa) }
        func activate() { activations += 1 }
        func log(_ event: MetaEvent) { events.append(event) }
        func setIDFACollection(_ on: Bool) { idfa.append(on) }
    }

    private final class Reporter: PurchaseReporting {
        var values: [PurchaseValue] = []
        let log: Log
        init(log: Log) { self.log = log }
        func purchaseCompleted(_ value: PurchaseValue) { values.append(value); log.events.append("report \(value.transactionID)") }
    }

    private final class Log { var events: [String] = [] }

    private final class Tx: DeliveredTransaction {
        let productID: String
        let transactionID: String
        let isVerified: Bool
        let value: PurchaseValue?
        let log: Log
        init(_ pid: String, _ tid: String, verified: Bool = true, value: PurchaseValue?, log: Log) {
            productID = pid; transactionID = tid; isVerified = verified; self.value = value; self.log = log
        }
        func finish() async { log.events.append("finish \(transactionID)") }
    }

    private final class Recorder: PurchaseRecording {
        let log: Log
        init(log: Log) { self.log = log }
        func record(_ purchase: RecordablePurchase) async { log.events.append("record \(purchase.transactionID)") }
    }

    private func value(_ pid: String = "com.manycode.arrowout.bundle.mini", _ tid: String = "7001", _ amount: String = "4.99",
                       _ currency: String = "USD", quantity: Int = 1, env: StoreEnvironment = .production) -> PurchaseValue {
        PurchaseValue(productID: pid, transactionID: tid, amount: Decimal(string: amount)!, currency: currency, quantity: quantity,
                      environment: env)
    }

    private func grant() -> Grant { Grant(coins: 2000) }

    // MARK: 1. the purchase event

    func testPurchaseCarriesTheTransactionsPriceAndCurrency() throws {
        for (amount, cur, want) in [("4.99", "USD", 4.99), ("249.99", "TRY", 249.99), ("160", "JPY", 160.0), ("0.99", "eur", 0.99)] {
            let e = try XCTUnwrap(MetaEvents.purchase(value(amount: amount, cur)), "\(amount) \(cur)")
            XCTAssertEqual(e.name, "fb_mobile_purchase")
            XCTAssertEqual(try XCTUnwrap(e.valueToSum), want, accuracy: 0.000_001, "\(amount) \(cur)")
            XCTAssertEqual(e.parameters["fb_currency"], .text(cur.uppercased()), "ISO code, upper case")
            XCTAssertEqual(e.parameters["fb_content_id"], .text("com.manycode.arrowout.bundle.mini"))
            XCTAssertEqual(e.parameters["fb_content_type"], .text("product"))
            XCTAssertEqual(e.parameters["fb_num_items"], .number(1))
            XCTAssertEqual(Set(e.parameters.keys), ["fb_currency", "fb_content_id", "fb_content_type", "fb_num_items"])
        }
        XCTAssertEqual(MetaEvents.purchase(value(quantity: 3))?.parameters["fb_num_items"], .number(3))
    }

    private func value(amount: String, _ currency: String) -> PurchaseValue { value("com.manycode.arrowout.bundle.mini", "7001", amount, currency) }

    func testNoRevenueEventWithoutARealPriceAndCurrency() {
        XCTAssertNil(MetaEvents.purchase(value(amount: "0", "USD")), "a free transaction is not revenue")
        XCTAssertNil(MetaEvents.purchase(value(amount: "-1", "USD")))
        XCTAssertNil(MetaEvents.purchase(value(amount: "4.99", "")), "no currency")
        XCTAssertNil(MetaEvents.purchase(value(amount: "4.99", "US")))
        XCTAssertNil(MetaEvents.purchase(value(amount: "4.99", "U$D")))
        XCTAssertNil(MetaEvents.purchase(value(amount: "4.99", "USDT")))
    }

    // MARK: 2. the pipeline reports a granted purchase once

    func testPipelineReportsAGrantedPurchaseOnceAfterTheGrantAndBeforeFinish() async {
        let log = Log()
        let reporter = Reporter(log: log), recorder = Recorder(log: log)
        var persisted = 0
        let v = value("com.manycode.arrowout.bundle.mini", "7001", "4.99", "USD")
        let tx = Tx(v.productID, v.transactionID, value: v, log: log)
        let g = await PurchasePipeline.complete(tx, apply: { _, _ in log.events.append("grant"); return self.grant() },
                                                persist: { persisted += 1; log.events.append("persist"); return true },
                                                record: RecordablePurchase(productID: v.productID, transactionID: v.transactionID, result: nil),
                                                recorder: recorder, report: reporter)
        XCTAssertNotNil(g)
        XCTAssertEqual(reporter.values, [v], "the transaction's own value, once")
        XCTAssertEqual(log.events, ["grant", "persist", "record 7001", "report 7001", "finish 7001"],
                       "reported after the grant is on disk and RevenueCat recorded it, before finish")
        XCTAssertEqual(persisted, 1)
    }

    func testPipelineReportsNothingForAReplayAnUnknownProductOrAnUnverifiedTransaction() async {
        let log = Log()
        let reporter = Reporter(log: log)
        let v = value()
        // a replay / an unknown product: apply grants nothing
        _ = await PurchasePipeline.complete(Tx(v.productID, v.transactionID, value: v, log: log), apply: { _, _ in nil }, report: reporter)
        // unverified: never applied
        _ = await PurchasePipeline.complete(Tx(v.productID, "7002", verified: false, value: v, log: log),
                                            apply: { _, _ in XCTFail("an unverified transaction is never applied"); return nil }, report: reporter)
        // granted, but StoreKit recorded no price: not reported (logged), still finished
        _ = await PurchasePipeline.complete(Tx(v.productID, "7003", value: nil, log: log), apply: { _, _ in self.grant() }, report: reporter)
        XCTAssertEqual(reporter.values, [], "nothing to report in any of the three")
        XCTAssertEqual(log.events, ["finish 7001", "finish 7002", "finish 7003"], "every one is still finished")
    }

    func testTheGameReporterTurnsAGrantedPurchaseIntoOnePurchaseEvent() {
        let sink = RecordingSink()
        let meta = MetaAds(mode: .live, sink: sink)
        meta.purchaseCompleted(value("com.manycode.arrowout.coins.1000", "8001", "0.99", "USD"))
        meta.purchaseCompleted(value("com.manycode.arrowout.coins.1000", "8002", "0", "USD"))       // not revenue: dropped
        XCTAssertEqual(sink.events.map(\.name), ["fb_mobile_purchase"])
        XCTAssertEqual(sink.events.first?.valueToSum ?? 0, 0.99, accuracy: 0.000_001)
        XCTAssertEqual(sink.events.first?.parameters["fb_content_id"], .text("com.manycode.arrowout.coins.1000"))
    }

    // MARK: 3. tutorial and levels

    func testTutorialAndLevelEventNames() {
        let t = MetaEvents.tutorialCompleted()
        XCTAssertEqual(t.name, "fb_mobile_tutorial_completion")
        XCTAssertNil(t.valueToSum)
        XCTAssertEqual(t.parameters, ["fb_success": .text("1"), "fb_content_id": .text("ftue")])
        let l = MetaEvents.levelAchieved(34)
        XCTAssertEqual(l.name, "fb_mobile_level_achieved")
        XCTAssertNil(l.valueToSum)
        XCTAssertEqual(l.parameters, ["fb_level": .text("34")])
    }

    func testEveryWonLevelIsReportedWithItsNumber() {
        let sink = RecordingSink()
        let meta = MetaAds(mode: .live, sink: sink)
        meta.levelsWon([1, 2, 3, 4])            // the "Levels 1-4" session
        meta.levelsWon([5])
        meta.levelsWon([0])                     // not a level
        XCTAssertEqual(sink.events.map(\.name), Array(repeating: "fb_mobile_level_achieved", count: 5))
        XCTAssertEqual(sink.events.compactMap { $0.parameters["fb_level"] }, ["1", "2", "3", "4", "5"].map { MetaEvent.Value.text($0) })
    }

    func testTheFTUEEndIsReportedOnceAtTheFirstHome() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("meta-ftue-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: dir) }
        let args = LaunchArgs(arguments: [])
        let store = PlayerStore(args: args, now: Date(), bundle: .main, directory: dir)
        let sink = RecordingSink()
        let meta = MetaAds(mode: .live, sink: sink)
        store.mutateAndSave { $0.homeSeen = false; $0.flags.seen.remove(MetaAds.ftueKey) }
        meta.ftueEndedIfNeeded(store)
        XCTAssertEqual(sink.events, [], "the FTUE chain is still running: no home seen")
        store.mutateAndSave { $0.homeSeen = true; $0.level = 7 }
        meta.ftueEndedIfNeeded(store)
        meta.ftueEndedIfNeeded(store)           // the next home arrivals
        XCTAssertEqual(sink.events.map(\.name), ["fb_mobile_tutorial_completion"], "once per install")
        XCTAssertTrue(store.state.flags.seen.contains(MetaAds.ftueKey), "the marker is saved")
    }

    func testLogOnlyAndOffNeverReachTheSDK() {
        let quietSink = RecordingSink(), offSink = RecordingSink()
        let quiet = MetaAds(mode: .logOnly, sink: quietSink), off = MetaAds(mode: .off, sink: offSink)
        for m in [quiet, off] { m.levelsWon([9]); m.purchaseCompleted(value()); m.activate() }
        // log-only hands the event to its sink (the app's LogSink drops it; this recorder proves the mapping still ran)
        XCTAssertEqual(quietSink.events.count, 2)
        XCTAssertEqual(quietSink.activations, 0, "no session is started outside live mode")
        XCTAssertEqual(offSink.events, [], "a build without credentials sends nothing anywhere")
        XCTAssertEqual(offSink.activations, 0)
    }

    // MARK: 4. which runs talk to Meta

    func testOnlyARealReleaseRunIsLive() {
        let ok = MetaCredentials(appID: "2657116281470019", tokenWellFormed: true)
        let none = MetaCredentials(appID: "2657116281470019", tokenWellFormed: false)
        // sim / measure: false = the store build on a device (the case every pre-RFIX assertion below describes)
        func m(_ release: Bool, _ c: MetaCredentials, quiet: Bool = false, bot: Bool = false, arg: String? = nil, host: Bool = false,
               sim: Bool = false, measure: Bool = false) -> MetaMode {
            MetaMode.choose(release: release, credentials: c, quiet: quiet, autoplay: bot, metaArg: arg, unitTestHost: host,
                            simulator: sim, measure: measure)
        }
        XCTAssertEqual(m(true, ok), .live, "the store build on a real run")
        XCTAssertEqual(m(true, ok, quiet: true), .logOnly, "store captures (-pc.capture) / UI tests never reach Meta")
        XCTAssertEqual(m(true, ok, bot: true), .logOnly, "the bot never reaches Meta")
        XCTAssertEqual(m(true, ok, quiet: true, arg: "live"), .live, "-pc.meta live forces it")
        XCTAssertEqual(m(true, none), .off, "a verification build without the token sends nothing")
        XCTAssertEqual(m(true, none, arg: "live"), .off, "not even when forced")
        XCTAssertEqual(m(false, ok), .logOnly, "DEBUG builds never send by default")
        XCTAssertEqual(m(false, ok, arg: "live"), .live, "a person checking Events Manager with a DEBUG build")
        XCTAssertEqual(m(false, none, arg: "live"), .logOnly)
        XCTAssertEqual(m(true, ok, arg: "off"), .logOnly)
        for release in [true, false] {
            XCTAssertEqual(m(release, ok, arg: "live", host: true), .logOnly, "never the SDK inside the unit-test host")
        }
        // RFIX 2026-09-29: with the real token in every Release / Measure product, a Simulator run and a Measure build are
        // test runs, never installs: log only, whatever the other flags say (bench.py's '-pc.go home -pc.seed 1' Measure
        // launch on the Simulator, an argument-free Release smoke launch, the owner's PH-2/PH-3 Measure runs)
        XCTAssertEqual(m(true, ok, sim: true), .logOnly, "a Release build on the Simulator with no test flag")
        XCTAssertEqual(m(true, ok, measure: true), .logOnly, "a Measure build on the phone with no test flag")
        XCTAssertEqual(m(true, ok, sim: true, measure: true), .logOnly, "bench.py: Measure on the Simulator")
        XCTAssertEqual(m(false, ok, sim: true), .logOnly)
        XCTAssertEqual(m(true, ok, arg: "live", sim: true), .live, "-pc.meta live still forces it (a person checking Events Manager)")
        XCTAssertEqual(m(true, ok, arg: "live", measure: true), .live)
        XCTAssertEqual(m(true, none, arg: "live", sim: true), .off, "never without the token")
        XCTAssertEqual(m(true, ok, arg: "live", host: true, sim: true), .logOnly, "never inside the unit-test host")
    }

    func testCredentialsNeedTheNumericAppIDAndA32HexToken() {
        let hex = String(repeating: "0123456789abcdef", count: 2)
        XCTAssertTrue(MetaCredentials(info: ["FacebookAppID": "2657116281470019", "FacebookClientToken": hex]).isValid)
        XCTAssertFalse(MetaCredentials(info: ["FacebookAppID": "2657116281470019", "FacebookClientToken": ""]).isValid, "empty token")
        XCTAssertFalse(MetaCredentials(info: ["FacebookAppID": "2657116281470019", "FacebookClientToken": String(hex.dropLast())]).isValid)
        XCTAssertFalse(MetaCredentials(info: ["FacebookAppID": "2657116281470019", "FacebookClientToken": hex.uppercased()]).isValid)
        XCTAssertFalse(MetaCredentials(info: ["FacebookAppID": "26571162814x0019", "FacebookClientToken": hex]).isValid)
        XCTAssertFalse(MetaCredentials(info: ["FacebookClientToken": hex]).isValid, "no app id")
        XCTAssertFalse(MetaCredentials(info: nil).isValid)
    }

    // MARK: 5. the ATT prompt's moment

    func testTheTrackingPromptComesOnceAfterTheFTUEAndNeverWithTheRatingSheet() {
        let due = TrackingPrompt.Inputs(allowed: true, homeSeen: true, level: 7, ftueEndsAtLevel: 7, askedThisRun: false,
                                        notDetermined: true, ratedThisVisit: false)
        XCTAssertTrue(TrackingPrompt.isDue(due), "the first home after the L6 win (level 7)")
        var i = due; i.level = 35
        XCTAssertTrue(TrackingPrompt.isDue(i), "a later calm visit while it was never asked")
        i = due; i.homeSeen = false
        XCTAssertFalse(TrackingPrompt.isDue(i), "never before the first home (the FTUE chain, first launch, Loading)")
        i = due; i.level = 6
        XCTAssertFalse(TrackingPrompt.isDue(i), "never while the FTUE levels are still ahead")
        // RFIX 2026-09-29: the saved 'attAsked' marker is gone (it was written before the request and silenced the prompt
        // forever when the process died with the alert up). Once per INSTALL is iOS's own answer (notDetermined below, still
        // asserted); once per RUN is this guard, asserted with the same strength as the old marker was.
        i = due; i.askedThisRun = true
        XCTAssertFalse(TrackingPrompt.isDue(i), "one request per process (the alert may still be up)")
        i = due; i.notDetermined = false
        XCTAssertFalse(TrackingPrompt.isDue(i), "iOS already has an answer")
        i = due; i.ratedThisVisit = true
        XCTAssertFalse(TrackingPrompt.isDue(i), "one system sheet per visit: the rating sheet went first")
        i = due; i.allowed = false
        XCTAssertFalse(TrackingPrompt.isDue(i), "not in log-only runs (tests, captures, the bot) without -pc.att 1")
    }

    /// RFIX 2026-09-29: a marker saved by an older build (written before the request; the process died with the alert up) no
    /// longer silences the prompt while iOS still has no answer; once iOS has an answer nothing asks again.
    func testAStaleSavedMarkerNoLongerSilencesThePrompt() {
        var s = PlayerState()
        s.homeSeen = true
        s.level = 9
        s.flags.seen.insert(TrackingPrompt.legacyAskedKey)
        let stale = TrackingPrompt.inputs(s, allowed: true, ftueEndsAtLevel: 7, askedThisRun: false, notDetermined: true, ratedThisVisit: false)
        XCTAssertTrue(TrackingPrompt.isDue(stale), "iOS says notDetermined: the person was never really asked")
        let answered = TrackingPrompt.inputs(s, allowed: true, ftueEndsAtLevel: 7, askedThisRun: false, notDetermined: false, ratedThisVisit: false)
        XCTAssertFalse(TrackingPrompt.isDue(answered), "iOS kept an answer: once per install")
        s.flags.seen.remove(TrackingPrompt.legacyAskedKey)
        let fresh = TrackingPrompt.inputs(s, allowed: true, ftueEndsAtLevel: 7, askedThisRun: false, notDetermined: true, ratedThisVisit: false)
        XCTAssertEqual(stale, fresh, "the saved flags play no part in the decision")
    }

    // MARK: 6. production money only; nothing dropped before the SDK starts (RFIX 2026-09-29)

    func testOnlyProductionMoneyIsReportedAsRevenue() {
        let sink = RecordingSink()
        let meta = MetaAds(mode: .live, sink: sink)
        XCTAssertTrue(MetaEvents.isRevenue(value(env: .production)))
        for env in [StoreEnvironment.sandbox, .xcode, .unknown] {
            XCTAssertFalse(MetaEvents.isRevenue(value(env: env)), "\(env)")
            meta.purchaseCompleted(value("com.manycode.arrowout.coins.1000", "90\(env.rawValue.count)", "0.99", "USD", env: env))
        }
        XCTAssertEqual(sink.events, [], "TestFlight, App Review's test purchases and StoreKit testing are never revenue")
        XCTAssertEqual(meta.recent, [], "…and never reach the reporter's event list")
        meta.purchaseCompleted(value("com.manycode.arrowout.coins.1000", "9100", "0.99", "USD", env: .production))
        XCTAssertEqual(sink.events.map(\.name), ["fb_mobile_purchase"], "a production purchase is")
    }

    func testEventsBeforeTheModeIsDecidedAreQueuedNotDropped() {
        let sink = RecordingSink()
        let meta = MetaAds()                    // the app's shared reporter before boot step 4
        meta.deferral = 0
        meta.purchaseCompleted(value("com.manycode.arrowout.bundle.mini", "7101"))   // Transaction.updates before boot
        meta.levelsWon([3])
        XCTAssertEqual(sink.events, [])
        XCTAssertEqual(meta.mode, .off, "not decided yet")
        meta.configure(mode: .live, sink: sink, started: false)     // boot: live, the SDK starts 3 frames later
        meta.levelsWon([4])
        XCTAssertEqual(sink.events, [], "FacebookSink drops events before start: they wait")
        meta.sinkStarted()
        XCTAssertEqual(sink.events.map(\.name), ["fb_mobile_purchase", "fb_mobile_level_achieved", "fb_mobile_level_achieved"],
                       "handed on in order once the SDK has started")
        XCTAssertEqual(sink.events.compactMap { $0.parameters["fb_level"] }, [.text("3"), .text("4")])
        meta.levelsWon([5])
        XCTAssertEqual(sink.events.count, 4, "after the start: straight through")
        meta.sinkStarted()
        XCTAssertEqual(sink.events.count, 4, "nothing is handed on twice")
    }

    func testQueuedEventsFollowTheDecidedModeAndTheQueueIsBounded() {
        let logSink = RecordingSink(), offSink = RecordingSink()
        let quiet = MetaAds(), off = MetaAds()
        quiet.deferral = 0; off.deferral = 0
        for m in [quiet, off] { m.levelsWon([1, 2]) }
        quiet.configure(mode: .logOnly, sink: logSink, started: true)
        off.configure(mode: .off, sink: offSink, started: true)
        XCTAssertEqual(logSink.events.count, 2, "a log-only run logs them")
        XCTAssertEqual(offSink.events, [], "a build without credentials sends them nowhere")
        let never = MetaAds()                   // a run that never boots (a unit-test host)
        never.deferral = 0                      // live below: no 0.4 s hop, so the handing-on is synchronous here
        never.levelsWon(Array(1...(MetaAds.pendingLimit + 30)))
        let late = RecordingSink()
        never.configure(mode: .live, sink: late, started: true)
        XCTAssertEqual(late.events.count, MetaAds.pendingLimit, "bounded")
        XCTAssertEqual(late.events.first?.parameters["fb_level"], .text("31"), "the newest are kept")
    }

    func testTheTrackingAnswerSwitchesIDFACollection() {
        let sink = RecordingSink()
        let meta = MetaAds(mode: .live, sink: sink)
        meta.trackingAnswered(.denied)
        meta.trackingAnswered(.authorized)
        meta.trackingAnswered(.restricted)
        XCTAssertEqual(sink.idfa, [false, true, false], "IDFA only while ATT says authorized")
    }
}
