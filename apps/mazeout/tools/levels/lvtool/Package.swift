// swift-tools-version:5.10
// lvtool: CONTENT's (L1) level tool over PathCore (SPEC-architecture §3.2 tools/levels/**, §4.3, §4.14; L1 acceptance).
// It is NOT pclevels (C4 owns Packages/PathCore/Sources/pclevels); it drives the same PathCore code:
//   bundle   design/levels.json -> App/Resources/Levels (C1's canonical bundle bytes, LevelJSON.encodeBundle)
//   check    every bundled level decodes, validates (the SPEC-gameplay §14.4 list on C2's BoardState rules), is cleared by
//            C2's greedy solver and won by C2's HeadlessDriver at 0.6 s per tap
//   freeset  the free units of every level's start state (compared with tools/levels/pathlib_rules.py)
//   diff     recorded / video levels against their research JSON (C1's LevelImport), cell for cell after the reveal merge
//   selftest negative controls: mutated levels the checks must catch
// Build + run through tools/levels/lv.sh (swift build -j 2, products in build/l1/lvtool, SPEC.md §6).
import PackageDescription

let package = Package(
    name: "lvtool",
    platforms: [.macOS("15.0")],
    dependencies: [.package(path: "../../../Packages/PathCore")],
    targets: [
        .executableTarget(name: "lvtool", dependencies: [.product(name: "PathCore", package: "PathCore")]),
    ],
    swiftLanguageVersions: [.v5]
)
