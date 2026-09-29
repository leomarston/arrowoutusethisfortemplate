import Foundation
let r = Locale.Region.isoRegions.map { $0.identifier }.sorted()
let en = Locale(identifier: "en_US")
var out: [String] = []
for id in r {
    let name = en.localizedString(forRegionCode: id) ?? "?"
    let sub = Locale.Region(id).subRegions.count
    let cont = Locale.Region(id).containingRegion?.identifier ?? "-"
    out.append("\(id)\t\(name)\t\(cont)\t\(sub)")
}
print(out.joined(separator: "\n"))
print("#count\t\(r.count)")
print("#legacy\t\(Locale.isoRegionCodes.count)\t" + Set(Locale.isoRegionCodes).symmetricDifference(Set(r)).sorted().joined(separator: ","))
