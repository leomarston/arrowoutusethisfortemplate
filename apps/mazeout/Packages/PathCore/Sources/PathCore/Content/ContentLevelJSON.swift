import Foundation

// C4 (SPEC-gameplay §14.1). A level as the content tools write it (build_levels.py / gen_levels.py): the bundle v1 keys
// with `capture` and `mask` always present (null for designed and generated boards), `layer` only when it is not 1,
// obstacle lists only when non-empty (an elevator always carries `arrows` and `reveals`), doubles in Python's repr.
// `ContentJSON.write(ContentJSON.value(level, schema: true))` is the line design/levels.json holds for a designed level.

extension ContentJSON {

    public static func value(_ c: Cell) -> JSONValue { .array([.int(c.c), .int(c.r)]) }

    public static func value(_ a: ArrowSpec) -> JSONValue {
        var kv: [(String, JSONValue)] = [("id", .int(a.id.raw)), ("cells", .array(a.cells.map(value))), ("dir", .string(a.dir.rawValue))]
        if a.layer != 1 { kv.append(("layer", .int(a.layer))) }
        if let h = a.hiddenBy { kv.append(("hidden_by", .string(h.raw))) }
        return .object(kv)
    }

    public static func value(_ o: ObstacleSpec) -> JSONValue {
        var kv: [(String, JSONValue)] = [("id", .string(o.id.raw)), ("kind", .string(o.kind.rawValue)),
                                         ("cells", .array(o.cells.map(value)))]
        if !o.arrows.isEmpty || o.kind == .elevator { kv.append(("arrows", .array(o.arrows.map { .int($0.raw) }))) }
        if !o.ends.isEmpty {
            kv.append(("ends", .array(o.ends.map { .object([("cell", value($0.cell)), ("out", .string($0.out.rawValue))]) })))
        }
        if let c = o.counter { kv.append(("counter", .int(c))) }
        if let at = o.counterAt { kv.append(("counter_at", .array(at.map { .double($0) }))) }
        if let x = o.order { kv.append(("order", .int(x))) }
        if let x = o.opens { kv.append(("opens", .string(x.raw))) }
        if let x = o.turn { kv.append(("turn", .string(x.rawValue))) }
        if !o.reveals.isEmpty || o.kind == .elevator { kv.append(("reveals", .array(o.reveals.map { .int($0.raw) }))) }
        if let x = o.sprite { kv.append(("sprite", .string(x))) }
        return .object(kv)
    }

    public static func value(_ m: LevelMetrics) -> JSONValue {
        var kv: [(String, JSONValue)] = [("rounds", .int(m.rounds)), ("free_at_start", .int(m.freeAtStart)),
                                         ("arrows", .int(m.arrows)), ("cells", .int(m.cells)),
                                         ("mean_length", .double(m.meanLength))]
        if let b = m.botTimeLeft, let k = LevelCoding.botTimeKey { kv.append((k, .double(b))) }   // FIX-2 B (N-01): macOS tools only
        return .object(kv)
    }

    /// The level object; `schema: true` adds `"schema":1` (design/levels.json and the bundle files carry it).
    public static func value(_ l: LevelSpec, schema: Bool) -> JSONValue {
        var kv: [(String, JSONValue)] = []
        if schema { kv.append(("schema", .int(LevelJSON.bundleSchema))) }
        kv.append(("level", .int(l.level)))
        kv.append(("source", .string(l.source.rawValue)))
        kv.append(("capture", l.capture.map { .string($0) } ?? .null))
        kv.append(("cols", .int(l.cols)))
        kv.append(("rows", .int(l.rows)))
        kv.append(("mask", l.mask.map { .array($0.map { .string($0) }) } ?? .null))
        kv.append(("timer_s", .int(l.timerSeconds)))
        kv.append(("hearts", .int(l.hearts)))
        kv.append(("tag", .string(l.tag.rawValue)))
        kv.append(("arrows", .array(l.arrows.map(value))))
        kv.append(("obstacles", .array(l.obstacles.map(value))))
        if let u = l.unlock { kv.append(("unlock", .string(u.rawValue))) }
        if let s = l.seed { kv.append(("seed", .uint(s))) }
        if let m = l.metrics { kv.append(("metrics", value(m))) }
        return .object(kv)
    }

    /// The canonical line of a level (no trailing newline).
    public static func line(_ l: LevelSpec, schema: Bool) -> String { write(value(l, schema: schema)) }

    #if PC_RESEARCH   // FIX-2 B (N-01): the content tools' record (its "bot_left"), macOS only
    /// A generator info record as design/tools/work/designed.json `infos` holds it.
    public static func value(_ i: Generator.Info) -> JSONValue {
        let t = i.target
        func opt(_ s: String?) -> JSONValue { s.map { .string($0) } ?? .null }
        return .object([
            ("level", .int(i.level)),
            ("target", .object([("n", .int(t.n)), ("pos", .int(t.pos)), ("tag", .string(t.tag.rawValue)),
                                ("template", .int(t.template)), ("units", .int(t.units)), ("rounds", .int(t.rounds)),
                                ("free", .int(t.free)), ("cols", .int(t.cols)), ("rows", .int(t.rows)),
                                ("template_timer", .int(t.templateTimer))])),
            ("planned", .array(i.planned.map { .string($0) })),
            ("kinds", .array(i.kinds.map { .string($0) })),
            ("got", .object([("units", .int(i.units)), ("rounds", .int(i.rounds)), ("free", .int(i.free)),
                             ("arrows", .int(i.arrows)), ("cols", .int(i.cols)), ("rows", .int(i.rows)),
                             ("mean_length", .double(i.meanLength)), ("max_length", .int(i.maxLength)),
                             ("timer", .int(i.timer)), ("bot_left", .double(i.botLeft)), ("density", .double(i.density))])),
            ("score", .double(i.score)),
            ("attempt", .string(i.attempt)),
            ("notes", .object([("shape", opt(i.shape)), ("door_style", opt(i.doorStyle)), ("box_style", opt(i.boxStyle))]
                              + (i.cornerSides.map { [("corner_sides", .array($0.map { .string($0) }))] } ?? []))),
            ("rejected", .array(i.rejected.map { .string($0) })),
        ])
    }
    #endif
}
