import Foundation
import CoreGraphics
import XCTest
@testable import ArrowOut

/// SKIN phase 3 (docs/SKIN.md §4): the app names art by SLOT. skin/art.json maps each slot to an art/MANIFEST.json id and
/// skin/scenes.json composes the home and Loading scenes; tools/skin/art.py generates `UIArt` / `ArtRig` (UIArt.swift) and
/// `SkinScenes` (SkinScenes.generated.swift), and the Linux CI job runs `art.py --check` (fresh, every shipped file mapped,
/// no Swift source naming a file). These tests prove the COMPILED tables are the JSON's, entry by entry, so a hand edit of a
/// generated file or a stale build cannot slip through.
final class SkinArtTests: XCTestCase {
    private func json(_ relative: String) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: V1Repo.url(relative))) as? [String: Any], relative)
    }

    /// Manifest id -> its entry.
    private func manifest() throws -> [String: [String: Any]] {
        let entries = try XCTUnwrap(try json("art/MANIFEST.json")["entries"] as? [[String: Any]])
        var out: [String: [String: Any]] = [:]
        for e in entries { if let id = e["id"] as? String { out[id] = e } }
        return out
    }

    /// tools/sync_art.sh's mapping: art/ui/out -> UI/, art/out -> Art/.
    private func bundlePath(_ file: String) -> String? {
        if file.hasPrefix("art/ui/out/") { return "UI/" + file.dropFirst("art/ui/out/".count) }
        if file.hasPrefix("art/out/") { return "Art/" + file.dropFirst("art/out/".count) }
        return nil
    }

    func testEverySlotIsTheSkinsMapping() throws {
        let slots = try XCTUnwrap(try json("skin/art.json")["slots"] as? [String: String], "art.json slots")
        let man = try manifest()
        XCTAssertEqual(Set(UIArt.allCases.map(\.rawValue)), Set(slots.keys), "one UIArt case per slot of skin/art.json")
        for art in UIArt.allCases {
            XCTAssertEqual(art.asset, slots[art.rawValue], art.rawValue)
            let entry = try XCTUnwrap(man[art.asset], "\(art.rawValue): \(art.asset) is in the manifest")
            XCTAssertEqual(art.path, (entry["file"] as? String).flatMap { self.bundlePath($0) }, "\(art.rawValue): the manifest's file")
            XCTAssertEqual(art.group, entry["group"] as? String ?? "", art.rawValue)
        }
        // the reference skin maps every shipped raster exactly once (the case list covered the manifest's shipped set before
        // slots, one case per file; art.py --check keeps every shipped file mapped)
        XCTAssertEqual(Set(UIArt.allCases.map(\.path)).count, UIArt.allCases.count, "no two slots share a file in this skin")
    }

    func testEveryRigSlotIsTheSkinsMapping() throws {
        let rigs = try XCTUnwrap(try json("skin/art.json")["rigs"] as? [String: String], "art.json rigs")
        let man = try manifest()
        XCTAssertEqual(Set(ArtRig.allCases.map(\.rawValue)), Set(rigs.keys))
        for rig in ArtRig.allCases {
            let id = try XCTUnwrap(rigs[rig.rawValue])
            let file = try XCTUnwrap(man[id]?["file"] as? String, id)
            XCTAssertEqual(rig.folder, (file.hasSuffix("/") ? String(file.dropLast()) : file).components(separatedBy: "/").last,
                           rig.rawValue)
            XCTAssertNoThrow(try PuppetRig.load(rig.folder), "\(rig.rawValue): Art/\(rig.folder)/rig.json loads")
        }
    }

    func testTheScenesAreTheSkinsScenes() throws {
        let sc = try json("skin/scenes.json")
        let home = try XCTUnwrap(sc["home"] as? [String: Any])
        let parts = sc["rigParts"] as? [String: [String: [String]]] ?? [:]
        func rect(_ a: Any?) -> CGRect? {
            guard let v = a as? [NSNumber], v.count == 4 else { return nil }
            return CGRect(x: v[0].doubleValue, y: v[1].doubleValue, width: v[2].doubleValue, height: v[3].doubleValue)
        }
        for (name, list) in [("back", SkinScenes.homeBack), ("front", SkinScenes.homeFront)] {
            let raw = try XCTUnwrap(home[name] as? [[String: Any]], "home.\(name)")
            XCTAssertEqual(list.count, raw.count, "home.\(name)")
            for (i, (l, d)) in zip(list, raw).enumerated() {
                let at = "home.\(name)[\(i)]"
                switch l.kind {
                case .art(let a): XCTAssertEqual(a.rawValue, d["art"] as? String, at)
                case .rig(let r): XCTAssertEqual(r.rawValue, d["rig"] as? String, at)
                case .centrepiece(let r): XCTAssertEqual(r.rawValue, d["centrepiece"] as? String, at)
                }
                XCTAssertEqual(l.frameKey, d["frame"] as? String ?? "", at)
                XCTAssertEqual(l.rect, rect(d["at"]) ?? .zero, at)
                XCTAssertEqual(l.fill, d["fill"] as? Bool ?? false, at)
                let rig = d["rig"] as? String ?? ""
                XCTAssertEqual(l.only, (d["only"] as? String).flatMap { parts[rig]?[$0] } ?? [], at)
                XCTAssertEqual(l.excluding, (d["excluding"] as? String).flatMap { parts[rig]?[$0] } ?? [], at)
            }
        }
        let loading = try XCTUnwrap(sc["loading"] as? [String: Any])
        XCTAssertEqual(SkinScenes.loadingBackdrop.rawValue, loading["backdrop"] as? String)
        XCTAssertEqual(SkinScenes.loadingLogo.rawValue, loading["logo"] as? String)
        let cast = try XCTUnwrap(loading["cast"] as? [[String: Any]])
        XCTAssertEqual(SkinScenes.loadingCast.map(\.art.rawValue), cast.compactMap { $0["art"] as? String })
        XCTAssertEqual(SkinScenes.loadingCast.map(\.rect), cast.compactMap { rect($0["at"]) })
        // every frame key a layer names is in ui.json, so the data default never silently stands in for a tuned value
        let t = Tuning.load(bundle: .main).ui.tokens
        for l in SkinScenes.homeBack + SkinScenes.homeFront where !l.frameKey.isEmpty {
            XCTAssertNotEqual(t.frame(l.frameKey, .zero), .zero, "frames.\(l.frameKey)")
        }
    }

    /// The avatar index table (Profile, Edit Profile, the leaderboards, the race lanes) is the `avatar.<n>` slots in order.
    func testTheAvatarTableIsTheAvatarSlots() {
        XCTAssertEqual(Avatars.arts.map(\.rawValue), (0..<Avatars.count).map { "avatar.\($0)" })
        XCTAssertEqual(Avatars.art(99), .avatar0, "out of range: the default silhouette")
        for a in Avatars.arts { XCTAssertTrue(ArtStore.exists(a), "\(a.rawValue): \(a.path)") }
    }

    /// The Loading scene's art (the cast included) is exactly the slots' files — nothing named by path.
    @MainActor func testLoadingDrawsItsSlots() {
        XCTAssertEqual(LoadingArt.paths, [SkinScenes.loadingBackdrop.path, SkinScenes.loadingLogo.path]
                       + SkinScenes.loadingCast.map(\.art.path))
        XCTAssertEqual(SkinScenes.loadingCast.count, 6, "R4 LOADING's cast")
        for p in LoadingArt.paths { XCTAssertNotNil(ArtStore.image(path: p, maxPixel: 64), p) }
    }
}
