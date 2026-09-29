import Foundation
import PathCore

// `lvtool consistency [--levels App/Resources/Levels] [--rules App/Resources/Tuning/rules.json] [--art art/ui/out]
//                     [--strings App/Resources/Strings] [--catalog App/Resources/Localizable.xcstrings]
//                     [--social App/Resources/Tuning/social.json] [--design design/levels.json] [--report F.json]`
//
// CONTENT (L2): the unlock cards, the tutorial, the first session, the tag cadence and the timers across L1-L150, checked
// against the values the specs pin (not only against each other, which L1's cross-checks already do):
//   unlock cards  exactly SPEC-gameplay §10.4 (+ SPEC.md §5.19): Linked L7, Box L11, Pipe L21, Elevator L31, Door L33, and
//                 Corner L70 (SPEC-gameplay §3.9, SPEC.md ruling 26: corners ship since the recast; F3-B 2026-09-29) with
//                 the spec's title / card / icon; each at its obstacle kind's FIRST appearance in L1-L150 (tape = linked,
//                 box/curtain = box, door/key = door), on that level's `unlock` field and nowhere else, as the first stage
//                 of its session; the curve's obstacles.firstLevel (the endless generator's schedule) equal to the card
//                 levels; the icon sprite in art/ui/out; the caps run upper-case and inside the card.
//   strings       every data key (unlock titles / cards, "Unlocked!", the tutorial caption, the session labels) has an EN +
//                 TR row in strings.tsv/requests and a translated TR entry in the generated Localizable.xcstrings; each TR
//                 card has its own upper-case run (the blue caps words, SHELL draws the upper-case words of the localized
//                 text).
//   tutorial      exactly GP §10.2's tapToMove: L1 stage 0 of the "Levels 1-4" session, stageReady / anyTap, no timer hold,
//                 no input restriction, the hand on arrow 1 which is visible and FREE at the start under C2's rules (the
//                 hint never points at an arrow that would bump), the fingertip on that arrow.
//   session       exactly GP §10.2's "L1-4" (levels 1-4, labels, reward 80, stage gap 0.7 s, hearts carried).
//   tags, timers  L19 / L25 Hard, L29 Super Hard (the videos), every level from L34 ending in 4 Hard and in 9 Super Hard,
//                 all others normal (GP §10.5, CONSISTENCY L-4); L1-L31 at 3:00; designed levels on
//                 `Difficulty.allowedTimers` (their template's recorded timer when `curve.timers.fromTemplate`, else
//                 `curve.timers` by tag); every timer one seen (3:30 … 2:00 or a recorded template's).
//                 F3-B (2026-09-29): a level's provenance (source, the stand-in note) is read from the DESIGN
//                 (--design design/levels.json): the bundle is the publish form since FIX-2 B (N-01), which drops `source`,
//                 so every bundled level decoded as designed and the recorded / video boards were held to the template rule.
//                 The six dedup stand-ins (SPEC.md ruling 28) carry the timer of the phone slot they fill (`pinnedStandIns`).
//   renderable    `renderProblems` on every authored level (the L6 zoom-floor case is the one VERIFIED warning).
//   events        social.json `unlocks` = GP §11.3 (Streak Race L30, Claw L33, Sky Jump L40, Weekly L50, Rocket Race L55), and
//                 Balloon Rise (B1) with the Claw: SPEC.md ruling 38, the two alternate weekly in the same top-bar slot.

struct PinnedUnlock {
    let feature: String; let level: Int; let kinds: [ObstacleKind]; let curveKind: String
    let title: String; let card: String; let icon: String
}

/// SPEC-gameplay §10.4 (VERIFIED V1/V2/phone; the Door card is ORCH 19's wording).
let pinnedUnlocks: [PinnedUnlock] = [
    PinnedUnlock(feature: "linked", level: 7, kinds: [.tape], curveKind: "tape", title: "Linked Arrows!", card: "LINKED ARROWS move together!", icon: "unlockIconLinked"),
    PinnedUnlock(feature: "box", level: 11, kinds: [.box, .curtain], curveKind: "box", title: "Box!", card: "Clear required amount of arrows to break the BOX!", icon: "unlockIconBox"),
    PinnedUnlock(feature: "pipe", level: 21, kinds: [.pipe], curveKind: "pipe", title: "Pipe!", card: "Pass arrows through the PIPE to break it!", icon: "unlockIconPipe"),
    PinnedUnlock(feature: "elevator", level: 31, kinds: [.elevator], curveKind: "elevator", title: "Elevator!", card: "Clear all arrows on the ELEVATOR to activate it!", icon: "unlockIconElevator"),
    PinnedUnlock(feature: "door", level: 33, kinds: [.door, .key], curveKind: "door", title: "Door!", card: "Collect the KEY to open the DOOR!", icon: "unlockIconDoor"),
    // SPEC-gameplay §3.9 (VERIFIED phone shots/456) + SPEC.md ruling 26: "Corner card at L70 with the original's text"
    PinnedUnlock(feature: "corner", level: 70, kinds: [.corner], curveKind: "corner", title: "Corner!", card: "Arrows turn when they hit the CORNER!", icon: "unlockIconCorner"),
]
/// SPEC-gameplay §11.3 (= SPEC-social D11).
let pinnedEventUnlocks: [String: Int] = ["streakRace": 30, "clawChallenge": 33, "skyJump": 40, "weeklyContest": 50, "rocketRace": 55]
/// + Balloon Rise (B1, the v582 event): SPEC.md ruling 38 "Claw / Balloon alternate weekly on the top bar" = the Claw's slot,
/// so it unlocks with the Claw (F3-B 2026-09-29; was missing, so social.json failed this check since B1).
let pinnedEventUnlocksShipped: [String: Int] = pinnedEventUnlocks.merging(["balloonRise": pinnedEventUnlocks["clawChallenge"]!]) { a, _ in a }

/// SPEC.md ruling 28 (DEDUP): the later duplicate slots got a generated stand-in "matched to the repeated board (size, units,
/// waves, free arrows, timer, tag, obstacle kinds)"; the timer is the one the phone recorded in the slot it fills (research
/// levels L086 / L083 / L081 / L100 / L103 / L101: timer_s), not the stand-in's curve template's. level -> (phone slot, timer).
let pinnedStandIns: [Int: (slot: Int, timer: Int)] = [81: (86, 150), 83: (83, 150), 86: (81, 150), 100: (100, 180), 101: (103, 180), 105: (101, 180)]

/// A level's provenance in design/levels.json (the shipped publish form carries none since N-01).
struct DesignRow { let source: String; let from: String?; let timer: Int }

struct ContentSet {
    var levels: [LevelSpec]
    var unlocks: [FeatureUnlock]
    var tutorials: [TutorialScript]
    var sessions: [SessionPlan]
    var curve: CurveSpec
    var strings: [String: String]          // en -> tr (strings.tsv wins over requests)
    var catalog: [String: String]          // key -> translated TR value of Localizable.xcstrings
    var art: Set<String>
    var social: [String: Int]?
    var design: [Int: DesignRow] = [:]     // level -> its design/levels.json provenance (F3-B)
}

/// Upper-case words (≥ 2 letters) of a text: the caps run the unlock card draws in blue.
func capsWords(_ s: String) -> [String] {
    s.components(separatedBy: CharacterSet.letters.inverted).filter { w in
        w.count >= 2 && w == w.uppercased() && w != w.lowercased()
    }
}

func consistencyErrors(_ c: ContentSet, rules: RulesTuning) -> (errors: [String], warnings: [String], table: [String]) {
    var e: [String] = [], w: [String] = [], t: [String] = []
    let N = c.levels.count
    let byLevel = Dictionary(c.levels.map { ($0.level, $0) }, uniquingKeysWith: { a, _ in a })
    func lv(_ n: Int) -> LevelSpec? { byLevel[n] }
    func needRow(_ key: String, _ what: String) {
        guard let tr = c.strings[key], !tr.isEmpty else { e.append("strings: \(what) \"\(key)\" has no EN/TR row"); return }
        guard let cat = c.catalog[key], !cat.isEmpty else { e.append("Localizable.xcstrings: \(what) \"\(key)\" has no translated TR entry"); return }
        if cat != tr { e.append("Localizable.xcstrings: \(what) \"\(key)\" TR \"\(cat)\" != the table's \"\(tr)\" (catalogue stale)") }
    }

    // first appearances of every obstacle kind in L1-L150
    var first: [ObstacleKind: Int] = [:]
    for l in c.levels.sorted(by: { $0.level < $1.level }) { for o in l.obstacles where first[o.kind] == nil { first[o.kind] = l.level } }
    // (was: "a corner (not shipped, SPEC-gameplay §3.9)" on any corner; corners ship since ruling 26 and their card is pinned
    // above, so a corner before L70 is caught as "its obstacle first appears at L…")

    // unlock cards
    let got = Dictionary(c.unlocks.map { ($0.feature.rawValue, $0) }, uniquingKeysWith: { a, _ in a })
    if c.unlocks.count != pinnedUnlocks.count || got.count != c.unlocks.count {
        e.append("unlocks.json lists \(c.unlocks.map { "\($0.feature.rawValue)@L\($0.level)" }), expected \(pinnedUnlocks.map { "\($0.feature)@L\($0.level)" })")
    }
    needRow("Unlocked!", "the unlock line")
    for p in pinnedUnlocks {
        guard let u = got[p.feature] else { e.append("unlocks.json: no \(p.feature) card"); continue }
        if u.level != p.level { e.append("unlock \(p.feature) at L\(u.level), SPEC-gameplay §10.4 says L\(p.level)") }
        if u.title != p.title { e.append("unlock \(p.feature) title \"\(u.title)\" != \"\(p.title)\"") }
        if u.card != p.card { e.append("unlock \(p.feature) card \"\(u.card)\" != \"\(p.card)\"") }
        if u.icon != p.icon { e.append("unlock \(p.feature) icon \(u.icon ?? "nil") != \(p.icon)") }
        if let i = u.icon, !c.art.contains(i) { e.append("unlock \(p.feature) icon \(i) missing from the art catalogue") }
        if let caps = u.caps {
            if caps != caps.uppercased() || !u.card.contains(caps) { e.append("unlock \(p.feature) caps \"\(caps)\" is not an upper-case run of its card") }
        } else { e.append("unlock \(p.feature) has no caps run") }
        let firstSeen = p.kinds.compactMap { first[$0] }.min()
        if firstSeen != u.level { e.append("unlock \(p.feature) at L\(u.level) but its obstacle first appears at L\(firstSeen.map(String.init) ?? "never")") }
        if let l = lv(u.level) {
            if l.unlock?.rawValue != p.feature { e.append("L\(u.level): unlock field \(l.unlock?.rawValue ?? "nil"), expected \(p.feature)") }
            if !l.obstacles.contains(where: { p.kinds.contains($0.kind) }) { e.append("L\(u.level): the \(p.feature) card level has no \(p.feature) obstacle") }
        } else { e.append("unlock \(p.feature): L\(u.level) missing") }
        if c.curve.obstacles.firstLevel[p.curveKind] != p.level {
            e.append("curve.obstacles.firstLevel.\(p.curveKind) = \(c.curve.obstacles.firstLevel[p.curveKind].map(String.init) ?? "nil"), the card is at L\(p.level)")
        }
        let s = c.sessions.first { $0.levels.contains(u.level) }
        if let s, s.levels.first != u.level { e.append("unlock \(p.feature) at L\(u.level), not the first stage of session \(s.id)") }
        needRow(u.title, "unlock title"); needRow(u.card, "unlock card")
        if let tr = c.strings[u.card], capsWords(tr).isEmpty { e.append("strings: the TR card \"\(tr)\" has no upper-case run (the blue caps words)") }
        if capsWords(u.card).isEmpty { e.append("unlock \(p.feature): the EN card has no upper-case run") }
        t.append("card \(p.feature) L\(u.level): \"\(u.title)\" / \"\(u.card)\" → TR \"\(c.strings[u.title] ?? "?")\" / \"\(c.strings[u.card] ?? "?")\" (caps EN \(capsWords(u.card)), TR \(capsWords(c.strings[u.card] ?? "")))")
    }
    for l in c.levels where l.unlock != nil && !pinnedUnlocks.contains(where: { $0.level == l.level && $0.feature == l.unlock!.rawValue }) {
        e.append("L\(l.level): unlock \(l.unlock!.rawValue) is not one of the \(pinnedUnlocks.count) cards")
    }
    for (k, lvl) in c.curve.obstacles.firstLevel where !pinnedUnlocks.contains(where: { $0.curveKind == k }) {
        e.append("curve.obstacles.firstLevel lists \(k)@\(lvl), which has no unlock card")
    }

    // the first session (GP §10.2)
    if c.sessions.count != 1 { e.append("sessions.json: \(c.sessions.count) sessions, expected only L1-4") }
    if let s = c.sessions.first {
        if s.id != "L1-4" || s.levels != [1, 2, 3, 4] { e.append("session \(s.id) \(s.levels), expected L1-4 [1, 2, 3, 4]") }
        if s.hudLabel != "Levels 1-4" || s.panelLabel != "Level 1-4" { e.append("session labels \(s.hudLabel ?? "nil") / \(s.panelLabel ?? "nil")") }
        if s.reward != 80 { e.append("session reward \(s.reward.map(String.init) ?? "nil"), expected 80") }
        if s.stageGap != 0.7 { e.append("session stage gap \(s.stageGap.map { "\($0)" } ?? "nil"), expected 0.7") }
        if s.hearts != .carry { e.append("session hearts \(s.hearts.rawValue), expected carry") }
        if let h = s.hudLabel { needRow(h, "session HUD label") }
        if let p = s.panelLabel { needRow(p, "session panel label") }
    }

    // the tutorial (GP §10.2)
    if c.tutorials.count != 1 { e.append("tutorials.json: \(c.tutorials.count) steps, expected only tapToMove") }
    for tu in c.tutorials {
        if tu.id.rawValue != "tapToMove" || tu.level != 1 || tu.stage != 0 { e.append("tutorial \(tu.id.rawValue) at L\(tu.level) stage \(tu.stage), expected tapToMove L1 stage 0") }
        if tu.trigger != .stageReady || tu.dismiss != .anyTap || tu.holdTimer { e.append("tutorial \(tu.id.rawValue): trigger \(tu.trigger.rawValue) dismiss \(tu.dismiss.rawValue) holdTimer \(tu.holdTimer), expected stageReady / anyTap / false") }
        if tu.allowedArrows != nil { e.append("tutorial \(tu.id.rawValue) restricts input (GP §10.2: no restriction)") }
        if tu.caption != "Tap to move!" { e.append("tutorial caption \(tu.caption ?? "nil"), expected \"Tap to move!\"") }
        if let cap = tu.caption { needRow(cap, "tutorial caption") }
        let s = c.sessions.first { $0.levels.contains(tu.level) }
        if let s, s.levels.firstIndex(of: tu.level) != tu.stage { e.append("tutorial \(tu.id.rawValue): stage \(tu.stage) but L\(tu.level) is stage \(s.levels.firstIndex(of: tu.level) ?? -1) of \(s.id)") }
        guard let l = lv(tu.level) else { e.append("tutorial \(tu.id.rawValue): L\(tu.level) missing"); continue }
        guard let h = tu.hand else { e.append("tutorial \(tu.id.rawValue) has no hand"); continue }
        if h.arrow != ArrowID(1) { e.append("tutorial hand on arrow \(h.arrow.raw), GP §10.2 says the middle arrow 1") }
        guard let a = l.arrows.first(where: { $0.id == h.arrow }) else { e.append("tutorial hand on a missing arrow \(h.arrow.raw)"); continue }
        if a.hiddenBy != nil || a.layer != 1 { e.append("tutorial hand on a hidden arrow \(a.id.raw)") }
        let free = BoardState(level: l, rules: rules).freeUnits()
        if !free.contains(where: { $0.contains(a.id) }) { e.append("tutorial hand on arrow \(a.id.raw), which is NOT free at the start (a tap would bump)") }
        if let at = h.at, at.count == 2 {
            let d = a.cells.map { max(abs(Double($0.c) - at[0]), abs(Double($0.r) - at[1])) }.min() ?? 99
            if d > 0.75 { e.append("tutorial fingertip \(at) is \(String(format: "%.2f", d)) cells from arrow \(a.id.raw)") }
        } else { e.append("tutorial hand without a fingertip point") }
        t.append("tutorial \(tu.id.rawValue): L\(tu.level) stage \(tu.stage), hand on arrow \(a.id.raw) (free at start: \(free.contains { $0.contains(a.id) })), caption \"\(tu.caption ?? "")\" → TR \"\(c.strings[tu.caption ?? ""] ?? "?")\"")
    }

    // tags and timers across L1-L150
    // the timers seen: the videos' and the phone's 3:30, 3:00, 2:30, 2:00, plus every recorded template timer the curve
    // carries (the recast's templates are the phone's L30-L79, e.g. L64 at 1:40)
    let seenTimers = Set([120, 150, 180, 210]).union(c.curve.templates.map(\.timer))
    for l in c.levels {
        let n = l.level
        let want: LevelTag = n < 34 ? ([19, 25].contains(n) ? .hard : n == 29 ? .superHard : .normal) : (cadence[n % 10] ?? .normal)
        if l.tag != want { e.append("L\(n): tag \(l.tag.rawValue), expected \(want.rawValue)") }
        if n <= 31, l.timerSeconds != 180 { e.append("L\(n): timer \(l.timerSeconds), the videos' levels are 3:00") }
        // the provenance from the design (F3-B): the publish-form bundle decodes every level as .designed
        let d = c.design[n]
        if d == nil { e.append("L\(n): not in the design file (no provenance to check its timer against)") }
        if let d, d.timer != l.timerSeconds { e.append("L\(n): bundle timer \(l.timerSeconds) != the design's \(d.timer)") }
        let standIn = d?.from?.hasPrefix("designed stand-in") ?? false
        if standIn != (pinnedStandIns[n] != nil) {
            e.append("L\(n): \(standIn ? "a dedup stand-in the checker does not pin" : "pinned as a stand-in but the design says \(d?.source ?? "nothing")")")
        }
        if let pin = pinnedStandIns[n] {
            if l.timerSeconds != pin.timer { e.append("L\(n): stand-in with timer \(l.timerSeconds), the phone slot L\(pin.slot) it fills has \(pin.timer)") }
        } else if d?.source == "designed" {
            // C4c: the generator's own rule (Difficulty.allowedTimers). With `curve.timers.fromTemplate` (the recast) a
            // designed level carries its target template's recorded timer whatever its tag; without it, the tag's fixed
            // curve.timers.
            var templateTimer: Int?
            var what = "curve.timers"
            if c.curve.timers.fromTemplate {
                do {
                    let t = try Generator.target(c.curve, n)
                    templateTimer = t.templateTimer
                    what = "the timer of its template L\(t.template)"
                } catch { e.append("L\(n): designed level without a curve template (\(error))") }
            }
            let allowed = Difficulty.allowedTimers(l.tag, curve: c.curve, templateTimer: templateTimer)
            if !allowed.contains(l.timerSeconds) {
                e.append("L\(n): designed \(l.tag.rawValue) level with timer \(l.timerSeconds), allowed \(allowed.sorted()) (\(what))")
            }
        }
        if !seenTimers.contains(l.timerSeconds) { e.append("L\(n): timer \(l.timerSeconds) never seen (3:30, 3:00, 2:30, 2:00 or a recorded template's)") }
        let r = renderProblems(l, art: c.art)
        for x in r.errors { e.append("L\(n): render: \(x)") }
        for x in r.warnings { w.append("L\(n): render: \(x)") }
    }
    if N != 150 { e.append("\(N) authored levels, SPEC-gameplay §14 says 150") }

    // event unlock levels (SOC1's social.json; GP §11.3)
    if let s = c.social {
        if s != pinnedEventUnlocksShipped { e.append("social.json unlocks \(s.sorted { $0.key < $1.key }), GP §11.3 + ruling 38 say \(pinnedEventUnlocksShipped.sorted { $0.key < $1.key })") }
        for (k, v) in s.sorted(by: { $0.value < $1.value }) { t.append("event \(k) unlocks at L\(v)") }
    } else { w.append("social.json has no unlocks section") }
    return (e, w, t)
}

// MARK: loading

/// strings.tsv + requests/*.tsv as build.py merges them (a strings.tsv row wins); only en -> tr.
func loadStrings(_ dir: String) throws -> [String: String] {
    func parse(_ path: String) throws -> [(String, String)] {
        let text = String(decoding: try readData(path), as: UTF8.self)
        var out: [(String, String)] = []
        for (i, line) in text.components(separatedBy: "\n").enumerated() where i > 0 && !line.hasPrefix("#") && !line.isEmpty {
            let f = line.components(separatedBy: "\t")
            guard f.count >= 2 else { continue }
            func un(_ s: String) -> String { s.replacingOccurrences(of: "\\n", with: "\n") }
            out.append((un(f[0]), un(f[1])))
        }
        return out
    }
    var m: [String: String] = [:]
    let req = (dir as NSString).appendingPathComponent("requests")
    for name in ((try? FileManager.default.contentsOfDirectory(atPath: req)) ?? []).sorted() where name.hasSuffix(".tsv") {
        for (en, tr) in try parse((req as NSString).appendingPathComponent(name)) where m[en] == nil { m[en] = tr }
    }
    for (en, tr) in try parse((dir as NSString).appendingPathComponent("strings.tsv")) { m[en] = tr }
    return m
}

/// key -> TR value of a translated entry in the String Catalog.
func loadCatalog(_ path: String) throws -> [String: String] {
    guard let top = try jsonObject(try readData(path), path) as? [String: Any], let strings = top["strings"] as? [String: Any] else {
        throw ToolError("\(path): no `strings`")
    }
    var m: [String: String] = [:]
    for (k, v) in strings {
        guard let e = v as? [String: Any], let loc = e["localizations"] as? [String: Any], let tr = loc["tr"] as? [String: Any],
              let unit = tr["stringUnit"] as? [String: Any], (unit["state"] as? String) == "translated",
              let value = unit["value"] as? String else { continue }
        m[k] = value
    }
    return m
}

func loadContentSet(_ a: Args) throws -> ContentSet {
    let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: a.opt("levels", "App/Resources/Levels")))
    if !lib.problems.isEmpty { throw ToolError("LevelLibrary: \(lib.problems)") }
    var levels: [LevelSpec] = []
    for n in 1...lib.authoredCount { levels.append(try lib.loadAuthored(n)) }
    var social: [String: Int]?
    if let d = try? readData(a.opt("social", "App/Resources/Tuning/social.json")), let o = try? jsonObject(d, "social.json") as? [String: Any] {
        social = o["unlocks"] as? [String: Int]
    }
    // F3-B: each level's provenance from the design file (the bundle's publish form has none)
    var design: [Int: DesignRow] = [:]
    let dp = a.opt("design", "design/levels.json")
    guard let top = try jsonObject(try readData(dp), dp) as? [String: Any], let rows = top["levels"] as? [[String: Any]] else {
        throw ToolError("\(dp): no `levels`")
    }
    for r in rows {
        guard let n = r["level"] as? Int, let src = r["source"] as? String, let t = r["timer_s"] as? Int else { throw ToolError("\(dp): a level without level / source / timer_s") }
        design[n] = DesignRow(source: src, from: r["_from"] as? String, timer: t)
    }
    return ContentSet(levels: levels, unlocks: lib.unlocks, tutorials: lib.tutorials, sessions: lib.sessions, curve: lib.curve,
                      strings: try loadStrings(a.opt("strings", "App/Resources/Strings")),
                      catalog: try loadCatalog(a.opt("catalog", "App/Resources/Localizable.xcstrings")),
                      art: artCatalog(a.opt("art", "art/ui/out")), social: social, design: design)
}

func cmdConsistency(_ a: Args) throws -> Int32 {
    let (rules, _) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let c = try loadContentSet(a)
    let r = consistencyErrors(c, rules: rules)
    if let rp = a.options["report"] {
        try writeData(try reportJSON(["levels": c.levels.count, "errors": r.errors, "warnings": r.warnings, "table": r.table]), rp)
    }
    print("consistency: L1-L\(c.levels.count), \(c.unlocks.count) unlock cards, \(c.tutorials.count) tutorial step(s), \(c.sessions.count) session(s); \(r.errors.count) error(s), \(r.warnings.count) warning(s)")
    for x in r.table { print("  \(x)") }
    for x in r.errors { print("ERROR \(x)") }
    for x in r.warnings { print("WARN  \(x)") }
    return r.errors.isEmpty ? 0 : 1
}
