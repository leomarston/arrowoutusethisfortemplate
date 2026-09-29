import Foundation

// LEAD, WP0, frozen (SPEC-architecture §2.3, §3.2, §6.11; SPEC.md §2 "the copying line").
// The ONLY place the product's name comes from: the `PC_BRAND_NAME` build setting (project.yml, the one place it is
// spelled) → Info.plist `PCBrandName` → `Brand.name`. Nothing else in the code may spell it; copy that names the game
// interpolates `Brand.name`. The logo is art (`logoArrowOut`), never text.

enum Brand {
    /// Info.plist `PCBrandName` (= `$(PC_BRAND_NAME)`), falling back to the bundle's display name.
    static let name: String = {
        let info = Bundle.main.infoDictionary ?? [:]
        for key in ["PCBrandName", "CFBundleDisplayName", "CFBundleName"] {
            if let v = info[key] as? String, !v.isEmpty, !v.hasPrefix("$(") { return v }
        }
        return ""
    }()

    /// The logo raster's art id (UI-ART: our own lettering in the original logo's style).
    static let logoArtID = "logoArrowOut"
}
