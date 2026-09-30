import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// A0 LEAD-P (SPEC.md §5 item 42, contract amend 4; design/publish/PLAN-P.md §4.3). Pins what the amendment and the publish
/// project settings RULED, so a later edit that drifts from them fails here:
/// - the haptic map (ruling 39 OD4 + motion-catalog §5.1/§5.2): the compiled ◆ defaults carry every row and the priority
///   (ScaffoldTests keeps audio.json == compiled, AudioEngineTests keeps audio.json == AudioCueMap.spec);
/// - the Balloon Rise screen id (v582 rules; the outcomes are pinned in PathCore's APISurfaceTests);
/// - the shipped bundle: PrivacyInfo.xcprivacy with the release-plan §2.5 S-5 / §7 declarations, a release version string.
final class ContractAmend4Tests: XCTestCase {

    func testTheCompiledHapticDefaultsAreTheRuledMap() {
        let ruled: [Haptic: (String, Double)] = [
            .tap: ("rigid", 0.70), .bumpContact: ("heavy", 0.85), .fail: ("warning", 1.0), .clear: ("medium", 0.80),
            .win: ("heavy", 1.0),            // the OUT! slam (was success): OD4
            .burst: ("medium", 0.65), .heartLost: ("error", 1.0),
            .button: ("rigid", 0.60),        // every UI button (was light 0.50): OD4
            .booster: ("medium", 0.60), .coinLand: ("soft", 0.45),
            .logoLetter: ("rigid", 0.70),    // the strongest of the five rising letter clicks (0.55 → 0.70 per beat)
            .logoBounce: ("rigid", 0.40), .firework: ("soft", 0.35), .rewardPop: ("light", 0.40),
            .logoSwell: ("light", 0.45), .keyTurn: ("rigid", 0.45),
            .play: ("rigid", 0.75),          // the Play button's stronger click: OD4
        ]
        XCTAssertEqual(Set(ruled.keys), Set(Haptic.allCases), "every Haptic case has a ruled row")
        let compiled = Tuning.defaults.audio
        for h in Haptic.allCases {
            guard let r = ruled[h] else { continue }
            XCTAssertEqual(compiled.haptic(h).style, r.0, "\(h) style")
            XCTAssertEqual(compiled.haptic(h).intensity, r.1, accuracy: 1e-9, "\(h) intensity")
            XCTAssertEqual(AudioCueMap.spec.row(h).style.rawValue, r.0, "\(h) spec style")
            XCTAssertEqual(AudioCueMap.spec.row(h).intensity, r.1, accuracy: 1e-9, "\(h) spec intensity")
        }
        XCTAssertEqual(AudioCueMap.spec.priority, [.heartLost, .fail, .win, .burst, .bumpContact, .clear, .logoLetter, .logoSwell,
                                                   .keyTurn, .booster, .rewardPop, .coinLand, .firework, .logoBounce, .tap,
                                                   .play, .button],
                       "motion-catalog §5.2 + logoSwell/keyTurn with the event beats + play above button")
        XCTAssertEqual(AudioCueMap.spec.problems, [], "the spec table names every case")
    }

    /// The contract's per-beat intensity entry point exists and, for a player without its own implementation, plays the row.
    @MainActor func testPlayWithIntensityFallsBackToTheRow() {
        final class Recorder: HapticPlaying {
            var enabled = true
            var played: [Haptic] = []
            func prepare() {}
            func play(_ h: Haptic) { played.append(h) }
        }
        let r = Recorder()
        let p: any HapticPlaying = r
        p.play(.logoLetter, intensity: 0.55)
        XCTAssertEqual(r.played, [.logoLetter])
    }

    func testBalloonRiseIsAnEventScreen() {
        XCTAssertEqual(EventScreen(rawValue: "balloonRise"), .balloonRise, "-pc.go event:balloonRise")
        XCTAssertEqual(Screen.event(.balloonRise).logName, "event(balloonRise)")
        XCTAssertEqual(EventScreen.allCases.count, 5)
    }

    func testThePrivacyManifestShipsWithTheRuledDeclarations() throws {
        let url = try XCTUnwrap(Bundle.main.url(forResource: "PrivacyInfo", withExtension: "xcprivacy"),
                                "PrivacyInfo.xcprivacy is in the app bundle (release-plan S-5; ITMS-91053 otherwise)")
        let plist = try XCTUnwrap(PropertyListSerialization.propertyList(from: Data(contentsOf: url), format: nil)
                                  as? [String: Any])
        // The template ships no ad / attribution SDK (docs/ROADMAP.md D2): no tracking, no tracking domains. A game that adds
        // one restates these pins together with the manifest, the label and the privacy text (docs/recipes/ad-attribution.md).
        XCTAssertEqual(plist["NSPrivacyTracking"] as? Bool, false, "no tracking in the template")
        XCTAssertEqual(plist["NSPrivacyTrackingDomains"] as? [String], [], "no tracking domains")
        let apis = try XCTUnwrap(plist["NSPrivacyAccessedAPITypes"] as? [[String: Any]])
        var reasons: [String: [String]] = [:]
        for a in apis { reasons[a["NSPrivacyAccessedAPIType"] as? String ?? ""] = a["NSPrivacyAccessedAPITypeReasons"] as? [String] }
        XCTAssertEqual(reasons["NSPrivacyAccessedAPICategoryUserDefaults"], ["CA92.1"])
        XCTAssertEqual(reasons["NSPrivacyAccessedAPICategorySystemBootTime"], ["35F9.1"], "ProcessInfo.systemUptime")
        XCTAssertEqual(apis.count, 2)
        let collected = try XCTUnwrap(plist["NSPrivacyCollectedDataTypes"] as? [[String: Any]])
        let p = "NSPrivacyCollectedDataTypePurpose", t = "NSPrivacyCollectedDataType"
        // type -> (linked, tracking, purposes)
        let want: [String: (Bool, Bool, Set<String>)] = [
            t + "PurchaseHistory": (false, false, [p + "AppFunctionality", p + "Analytics"]),     // RevenueCat (observer mode)
        ]
        XCTAssertEqual(collected.count, want.count, "exactly the declared types")
        for c in collected {
            let type = c["NSPrivacyCollectedDataType"] as? String ?? "?"
            guard let (linked, tracking, purposes) = want[type] else { XCTFail("undeclared type \(type)"); continue }
            XCTAssertEqual(c["NSPrivacyCollectedDataTypeLinked"] as? Bool, linked, type)
            XCTAssertEqual(c["NSPrivacyCollectedDataTypeTracking"] as? Bool, tracking, type)
            XCTAssertEqual(Set(c["NSPrivacyCollectedDataTypePurposes"] as? [String] ?? []), purposes, type)
        }
        // the App Store label (fastlane/metadata/app_privacy_details.json, uploaded by the orchestrator) says the same
        let label = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: V1Repo.url("fastlane/metadata/app_privacy_details.json")))
                                  as? [[String: Any]])
        var byCategory: [String: Set<String>] = [:]
        for e in label { byCategory[e["category"] as? String ?? "?"] = Set(e["data_protections"] as? [String] ?? []) }
        XCTAssertEqual(byCategory, ["PURCHASE_HISTORY": ["DATA_NOT_LINKED_TO_YOU"]],
                       "the label mirrors the manifest one for one (a mismatch draws an ITMS-91xxx notice / a 5.1.2 rejection)")
        // RFIX 2026-09-29: the PURPOSES too, one for one (the label check above compared only the protections)
        let catName = [t + "PurchaseHistory": "PURCHASE_HISTORY", t + "ProductInteraction": "PRODUCT_INTERACTION", t + "DeviceID": "DEVICE_ID",
                       t + "CrashData": "CRASH_DATA", t + "OtherDataTypes": "OTHER_DATA"]
        let purposeName = [p + "AppFunctionality": "APP_FUNCTIONALITY", p + "Analytics": "ANALYTICS",
                           p + "DeveloperAdvertising": "DEVELOPERS_ADVERTISING", p + "ThirdPartyAdvertising": "THIRD_PARTY_ADVERTISING",
                           p + "ProductPersonalization": "PRODUCT_PERSONALIZATION", p + "Other": "OTHER_PURPOSES"]
        var labelPurposes: [String: Set<String>] = [:]
        for e in label { labelPurposes[e["category"] as? String ?? "?"] = Set(e["purposes"] as? [String] ?? []) }
        for (type, row) in want {
            let cat = try XCTUnwrap(catName[type], type)
            XCTAssertEqual(labelPurposes[cat], Set(row.2.compactMap { purposeName[$0] }), "\(cat): the label's purposes = the manifest's")
        }
        // RFIX 2026-09-29: every SDK manifest embedded in the app (today RevenueCat's bundle) is
        // COVERED by ours: Xcode's privacy report merges them, so each type an SDK collects must be declared here with at least
        // its purposes, linked if it says linked, tracking if it says tracking
        let appRoot = Bundle.main.bundleURL.standardizedFileURL
        let files = FileManager.default.enumerator(at: appRoot, includingPropertiesForKeys: nil)?.compactMap { $0 as? URL }
            .filter { $0.lastPathComponent == "PrivacyInfo.xcprivacy" && $0.standardizedFileURL.deletingLastPathComponent() != appRoot } ?? []
        let names = Set(files.map { $0.deletingLastPathComponent().lastPathComponent })
        XCTAssertFalse(names.contains { $0.hasPrefix("FBSDK") || $0.hasPrefix("FBAEM") }, "no Meta SDK in the template: \(names.sorted())")
        let ours = Dictionary(uniqueKeysWithValues: collected.map { ($0["NSPrivacyCollectedDataType"] as? String ?? "?", $0) })
        for f in files {
            let sdk = try XCTUnwrap(PropertyListSerialization.propertyList(from: Data(contentsOf: f), format: nil) as? [String: Any])
            let where_ = f.deletingLastPathComponent().lastPathComponent
            if sdk["NSPrivacyTracking"] as? Bool == true {
                XCTAssertEqual(plist["NSPrivacyTracking"] as? Bool, true, "\(where_) tracks")
                for d in sdk["NSPrivacyTrackingDomains"] as? [String] ?? [] {
                    XCTAssertTrue((plist["NSPrivacyTrackingDomains"] as? [String] ?? []).contains(d), "\(where_)'s tracking domain \(d)")
                }
            }
            for c in sdk["NSPrivacyCollectedDataTypes"] as? [[String: Any]] ?? [] {
                let type = c["NSPrivacyCollectedDataType"] as? String ?? "?"
                guard let mine = ours[type] else { XCTFail("\(where_) collects \(type), which the app's manifest does not declare"); continue }
                let need = Set(c["NSPrivacyCollectedDataTypePurposes"] as? [String] ?? [])
                let have = Set(mine["NSPrivacyCollectedDataTypePurposes"] as? [String] ?? [])
                XCTAssertTrue(need.isSubset(of: have), "\(where_) \(type): purposes \(need.subtracting(have).sorted()) missing from ours")
                if c["NSPrivacyCollectedDataTypeLinked"] as? Bool == true {
                    XCTAssertEqual(mine["NSPrivacyCollectedDataTypeLinked"] as? Bool, true, "\(where_) \(type) is linked")
                }
                if c["NSPrivacyCollectedDataTypeTracking"] as? Bool == true {
                    XCTAssertEqual(mine["NSPrivacyCollectedDataTypeTracking"] as? Bool, true, "\(where_) \(type) tracks")
                }
            }
        }
    }

    /// release-plan S-6: a store version (x.y.z, major ≥ 1; it must equal the ASC version record) and an integer build.
    func testTheBundleCarriesAReleaseVersion() throws {
        let info = try XCTUnwrap(Bundle.main.infoDictionary)
        let version = try XCTUnwrap(info["CFBundleShortVersionString"] as? String)
        let parts = version.split(separator: ".").compactMap { Int($0) }
        XCTAssertEqual(parts.count, 3, version)
        XCTAssertGreaterThanOrEqual(parts.first ?? 0, 1, "not the 0.x development version")
        let build = try XCTUnwrap(info["CFBundleVersion"] as? String)
        XCTAssertGreaterThanOrEqual(Int(build) ?? 0, 1, build)
    }
}
