import Foundation
import XCTest
import FacebookCore
@testable import ArrowOut

/// META (OWNER 2026-09-29 19:33; memory meta-sdk-wiring: "the failure is silent" — a missing package or an array plist key
/// written as INFOPLIST_KEY_* builds and ships with NO attribution). Proved on the BUILT products, never on project.yml:
///  1. the built Info.plist carries every Meta key with its ruled value (the App ID, the display name from PC_BRAND_NAME,
///     auto-log OFF (RFIX), IDFA collection off, Meta's two SKAdNetwork ids, the ATT purpose = infoplist.tsv's English) and the
///     client-token key (its value is checked only as "empty or well formed" here: a DEBUG build may lack it);
///  2. the ATT purpose ships in all 13 .lproj (InfoPlist.strings) with the table's exact text;
///  3. FacebookCore is REALLY linked: the frameworks are embedded at the pinned version, the binary that holds our code
///     (ArrowOut.debug.dylib in Debug, ArrowOut in Release) loads @rpath/FBSDKCoreKit and carries MetaAds' real SDK calls
///     (activateApp, logPurchase), and the SDK's classes are loaded in THIS process; the unit-test host never initialised it;
///  4. a Release product on this machine carries the factory .env's token (compared, never printed); with no token in the
///     .env there can be no Release product at all (tools/meta_token.py stops the build) and this is skipped with that reason.
/// The ATT prompt itself is never asserted (one-shot per install: memory att-prompt-is-one-shot-too).
final class MetaSDKLinkageTests: XCTestCase {
    static let appID = "2657116281470019"
    static let skad: Set<String> = ["v9wttpbfk9.skadnetwork", "n38lu8286q.skadnetwork"]
    static let pinned = "18.1.1"
    static let langs = ["en", "tr", "de", "fr", "es", "it", "pt-BR", "ja", "ko", "zh-Hans", "pl", "sk", "sl"]

    /// infoplist.tsv: lang -> the NSUserTrackingUsageDescription cell.
    static func purposeTable() throws -> [String: String] {
        let text = try V1Repo.text("App/Resources/Strings/infoplist.tsv")
        let lines = text.components(separatedBy: "\n")
        let header = try XCTUnwrap(lines.first).components(separatedBy: "\t")
        let row = try XCTUnwrap(lines.first { $0.hasPrefix("NSUserTrackingUsageDescription\t") }).components(separatedBy: "\t")
        XCTAssertEqual(header.count, row.count)
        var out: [String: String] = [:]
        for (i, h) in header.enumerated() where langs.contains(h) { out[h] = row[i] }
        return out
    }

    static func brandFromProjectYML() throws -> String {
        let yml = try V1Repo.text("project.yml")
        let line = try XCTUnwrap(yml.components(separatedBy: "\n").first { $0.contains("PC_BRAND_NAME: \"") })
        return try XCTUnwrap(line.components(separatedBy: "\"").dropFirst().first)
    }

    static func tokenLooksRight(_ s: String) -> Bool { s.count == 32 && s.allSatisfy { $0.isHexDigit && !$0.isUppercase } }

    // MARK: 1. the built Info.plist

    func testTheBuiltInfoPlistCarriesEveryMetaKey() throws {
        let info = try XCTUnwrap(Bundle.main.infoDictionary)
        XCTAssertEqual(info["FacebookAppID"] as? String, Self.appID)
        XCTAssertEqual(info["FacebookDisplayName"] as? String, try Self.brandFromProjectYML(), "PC_BRAND_NAME, the one source")
        // RFIX 2026-09-29 (orchestrator 23:49): auto-log OFF (was true), pinned exactly as before: with it on, FBSDK's own
        // StoreKit purchase logging could count every purchase a second time once the dashboard switch flips
        XCTAssertEqual(info["FacebookAutoLogAppEventsEnabled"] as? Bool, false)
        XCTAssertEqual(info["FacebookAdvertiserIDCollectionEnabled"] as? Bool, false, "no IDFA before ATT .authorized")
        let items = try XCTUnwrap(info["SKAdNetworkItems"] as? [[String: String]], "SKAdNetworkItems is an ARRAY key: it needs the base plist")
        XCTAssertEqual(Set(items.compactMap { $0["SKAdNetworkIdentifier"] }), Self.skad)
        XCTAssertEqual(items.count, 2)
        XCTAssertEqual(info["NSUserTrackingUsageDescription"] as? String, try Self.purposeTable()["en"],
                       "without it iOS answers .denied with no prompt")
        let token = try XCTUnwrap(info["FacebookClientToken"] as? String, "the key exists (meta_token.py fills the built copy)")
        XCTAssertTrue(token.isEmpty || Self.tokenLooksRight(token), "empty (no .env token) or a 32-hex token; nothing else")
        // the base plist's other keys survived the move into project.yml's info: block
        XCTAssertEqual(info["UIAppFonts"] as? [String], ["Fonts/PCDisplay-Black.ttf", "Fonts/PCDisplay-BlackItalic.ttf"])
        XCTAssertEqual(info["CADisableMinimumFrameDurationOnPhone"] as? Bool, true)
        XCTAssertEqual(info["UIStatusBarHidden"] as? Bool, true)
        XCTAssertEqual(info["UIRequiresFullScreen"] as? Bool, true)
        XCTAssertEqual(info["LSApplicationCategoryType"] as? String, "public.app-category.puzzle-games")
        XCTAssertEqual((info["UILaunchScreen"] as? [String: String])?["UIColorName"], "LaunchBackground")
        XCTAssertEqual(info["CFBundleShortVersionString"] as? String, "1.0.0", "MARKETING_VERSION, not xcodegen's 1.0 default")
        XCTAssertEqual(info["CFBundleVersion"] as? String, "1")
        XCTAssertEqual(info["UISupportedInterfaceOrientations"] as? [String], ["UIInterfaceOrientationPortrait"])
        // no ad-SERVING SDK key rides along (release_gates.sh gate 8 checks the Release bundle the same way)
        for k in ["GADApplicationIdentifier", "AppLovinSdkKey", "FacebookAutoInitEnabled"] { XCTAssertNil(info[k], k) }
    }

    // MARK: 2. the ATT purpose in 13 languages

    func testTheTrackingPurposeShipsInAll13Languages() throws {
        let table = try Self.purposeTable()
        XCTAssertEqual(Set(table.keys), Set(Self.langs))
        for lang in Self.langs {
            let path = try XCTUnwrap(Bundle.main.path(forResource: "InfoPlist", ofType: "strings", inDirectory: nil, forLocalization: lang),
                                     "\(lang).lproj/InfoPlist.strings is in the app")
            let dict = try XCTUnwrap(NSDictionary(contentsOfFile: path) as? [String: String], lang)
            XCTAssertEqual(dict["NSUserTrackingUsageDescription"], table[lang], "\(lang): the table's exact text")
            let v = table[lang] ?? ""
            XCTAssertFalse(v.isEmpty)
            XCTAssertTrue(v.contains("Meta"), "\(lang) names who receives it")
            XCTAssertFalse(v.contains("Arrow Out"), "\(lang): iOS names the app in the alert's title")
            if lang != "en" { XCTAssertNotEqual(v, table["en"], "\(lang) is translated") }
        }
    }

    // MARK: 3. really linked

    /// The LC_UUIDs of a Mach-O file (thin 64-bit or FAT), read from its load commands (dwarfdump --uuid, on the device).
    static func machoUUIDs(_ d: Data) -> Set<String> {
        func u32(_ o: Int, big: Bool) -> Int {
            guard o + 4 <= d.count else { return 0 }
            let b = [UInt8](d[(d.startIndex + o)..<(d.startIndex + o + 4)])
            return big ? Int(b[0]) << 24 | Int(b[1]) << 16 | Int(b[2]) << 8 | Int(b[3])
                       : Int(b[3]) << 24 | Int(b[2]) << 16 | Int(b[1]) << 8 | Int(b[0])
        }
        func thin(_ base: Int) -> String? {
            guard u32(base, big: false) == 0xfeedfacf else { return nil }
            let n = u32(base + 16, big: false)
            var o = base + 32
            for _ in 0..<n {
                let cmd = u32(o, big: false), size = u32(o + 4, big: false)
                if cmd == 0x1b, o + 24 <= d.count {
                    let u = [UInt8](d[(d.startIndex + o + 8)..<(d.startIndex + o + 24)])
                    return UUID(uuid: (u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], u[9], u[10], u[11], u[12], u[13], u[14], u[15])).uuidString
                }
                guard size > 0 else { break }
                o += size
            }
            return nil
        }
        if u32(0, big: true) == 0xcafebabe {
            return Set((0..<u32(4, big: true)).compactMap { thin(u32(8 + $0 * 20 + 8, big: true)) })
        }
        return Set([thin(0)].compactMap { $0 })
    }

    func testFacebookCoreIsReallyLinkedAtThePinnedVersion() throws {
        let root = Bundle.main.bundleURL
        let fm = FileManager.default
        for kit in ["FBSDKCoreKit", "FBSDKCoreKit_Basics", "FBAEMKit"] {
            let bin = root.appendingPathComponent("Frameworks/\(kit).framework/\(kit)")
            XCTAssertTrue(fm.fileExists(atPath: bin.path), "\(kit) is embedded")
            // the framework's own CFBundleShortVersionString is Meta's constant "1.0": the version is proven by identity — the
            // embedded binary's LC_UUIDs are the pinned 18.1.1 artifact's (SPM verified that zip against the pinned checksum)
            let mine = Self.machoUUIDs(try Data(contentsOf: bin))
            XCTAssertFalse(mine.isEmpty, "\(kit): LC_UUID readable")
            var pinned: Set<String> = []
            for slot in ["dd-A", "dd-B"] {
                let x = V1Repo.url("build/\(slot)/SourcePackages/artifacts/facebook-ios-sdk/\(kit)/\(kit).xcframework")
                for slice in (try? fm.contentsOfDirectory(atPath: x.path)) ?? [] {
                    let f = x.appendingPathComponent("\(slice)/\(kit).framework/\(kit)")
                    if let data = try? Data(contentsOf: f) { pinned.formUnion(Self.machoUUIDs(data)) }
                }
            }
            XCTAssertFalse(pinned.isEmpty, "\(kit): the pinned artifact is in build/dd-A|dd-B/SourcePackages (the package was resolved)")
            XCTAssertTrue(mine.isSubset(of: pinned), "\(kit): the embedded binary IS the pinned \(Self.pinned) artifact (LC_UUID)")
        }
        let embedded = try fm.contentsOfDirectory(atPath: root.appendingPathComponent("Frameworks").path).sorted()
        // the test host also embeds Apple's XCTest frameworks and the Debug PathCore package framework: judge the third parties
        XCTAssertEqual(embedded.filter { $0.hasPrefix("FB") || $0.hasPrefix("Facebook") },
                       ["FBAEMKit.framework", "FBSDKCoreKit.framework", "FBSDKCoreKit_Basics.framework"],
                       "FacebookCore only: no Login / Share / Gaming kit")
        let adServing = embedded.filter { $0.range(of: #"(?i)GoogleMobileAds|FBAudienceNetwork|AppLovin|UnityAds|IronSource|Vungle|Chartboost|InMobi|Mintegral|Pangle|Firebase"#,
                                                   options: .regularExpression) != nil }
        XCTAssertEqual(adServing, [], "no ad-serving SDK")
        // the binary with our code: Debug keeps it in ArrowOut.debug.dylib (the thin main binary would find nothing)
        let dylib = root.appendingPathComponent("ArrowOut.debug.dylib")
        let binURL = fm.fileExists(atPath: dylib.path) ? dylib : root.appendingPathComponent("ArrowOut")
        let bin = try Data(contentsOf: binURL)
        XCTAssertNotNil(bin.range(of: Data("@rpath/FBSDKCoreKit.framework/FBSDKCoreKit".utf8)), "\(binURL.lastPathComponent) loads FBSDKCoreKit")
        // MetaAds' real SDK calls: the Objective-C selectors of AppEvents and the imported Swift symbols of Settings /
        // ApplicationDelegate (a missing package would have compiled none of them)
        for sel in ["activateApp", "logPurchase:currency:parameters:", "logEvent:parameters:", "logEvent:valueToSum:parameters:",
                    "12FBSDKCoreKit8SettingsC31isAdvertiserIDCollectionEnabledSbvs",
                    "12FBSDKCoreKit19ApplicationDelegateC11application_29didFinishLaunchingWithOptions"] {
            XCTAssertNotNil(bin.range(of: Data(sel.utf8)), "MetaAds' real SDK call \(sel) is in \(binURL.lastPathComponent)")
        }
        // loaded in this process, at the pinned version
        XCTAssertNotNil(NSClassFromString("FBSDKAppEvents"), "FBSDKCoreKit is loaded")
        XCTAssertEqual(Settings.shared.sdkVersion, Self.pinned)
    }

    @MainActor
    func testTheUnitTestHostNeverStartsTheSDK() {
        XCTAssertTrue(NotificationPrompt.isUnitTestHost)
        XCTAssertTrue([MetaMode.off, .logOnly].contains(MetaAds.shared.mode), "the unit-test host never initialises the SDK")
        for mode in [MetaMode.live, .logOnly, .off] {
            XCTAssertFalse(TrackingPrompt.allowed(mode: mode, attArg: "1", unitTestHost: true), "and never asks for tracking")
        }
        XCTAssertTrue(TrackingPrompt.allowed(mode: .live, attArg: nil, unitTestHost: false), "a live run may ask")
        XCTAssertTrue(TrackingPrompt.allowed(mode: .logOnly, attArg: "1", unitTestHost: false), "-pc.att 1: UI tests reach it")
        XCTAssertFalse(TrackingPrompt.allowed(mode: .logOnly, attArg: nil, unitTestHost: false), "captures / UI tests / the bot: never")
    }

    // MARK: 4. a Release product carries the .env token

    func testAReleaseBuildCarriesTheFactoryEnvToken() throws {
        // RFIX 2026-09-29 (VERIFY F1): the factory .env as tools/meta_token.py finds it (the first ancestor holding .env + apps/),
        // so a snapshot tree compares against the file its build injected from, not a non-existent build/.env
        var env = V1Repo.root.deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent(".env")
        var dir = V1Repo.root
        while dir.path != "/" {
            dir = dir.deletingLastPathComponent()
            if FileManager.default.fileExists(atPath: dir.appendingPathComponent(".env").path),
               FileManager.default.fileExists(atPath: dir.appendingPathComponent("apps").path) {
                env = dir.appendingPathComponent(".env")
                break
            }
        }
        var envToken: String?
        if let text = try? String(contentsOf: env, encoding: .utf8) {
            for line in text.components(separatedBy: "\n") {
                var s = line.trimmingCharacters(in: .whitespaces)
                if s.hasPrefix("export ") { s = String(s.dropFirst(7)).trimmingCharacters(in: .whitespaces) }
                guard s.hasPrefix("META_CLIENT_TOKEN=") else { continue }
                envToken = String(s.dropFirst("META_CLIENT_TOKEN=".count)).trimmingCharacters(in: CharacterSet(charactersIn: "\"' "))
            }
        }
        guard let envToken, !envToken.isEmpty else {
            throw XCTSkip("OWNER ACTION: the factory .env has no META_CLIENT_TOKEN, so no Release / Measure build can exist "
                          + "(tools/meta_token.py stops it at its first phase); release_gates.sh gate 8 reports the same")
        }
        XCTAssertTrue(Self.tokenLooksRight(envToken), "the .env token is 32 lowercase hex characters (value not printed)")
        let fm = FileManager.default
        var products: [(URL, Date)] = []
        for slot in ["dd-A", "dd-B"] {
            for cfg in ["Release-iphonesimulator", "Release-iphoneos", "Measure-iphonesimulator", "Measure-iphoneos"] {
                let app = V1Repo.url("build/\(slot)/Build/Products/\(cfg)/ArrowOut.app/Info.plist")
                if let d = (try? fm.attributesOfItem(atPath: app.path))?[.modificationDate] as? Date { products.append((app, d)) }
            }
        }
        guard let newest = products.max(by: { $0.1 < $1.1 })?.0 else {
            throw XCTSkip("no Release / Measure product under build/dd-A|dd-B yet (build one: CONFIG=Release tools/build.sh A)")
        }
        let info = try XCTUnwrap(NSDictionary(contentsOf: newest) as? [String: Any])
        let token = info["FacebookClientToken"] as? String ?? ""
        XCTAssertTrue(token == envToken, "\(V1Repo.relative(newest)): FacebookClientToken is empty or differs from the .env one (value not printed)")
        XCTAssertEqual(info["FacebookAppID"] as? String, Self.appID)
    }
}
