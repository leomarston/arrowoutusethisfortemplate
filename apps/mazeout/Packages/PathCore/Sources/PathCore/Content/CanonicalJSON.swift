import Foundation

// C4 (SPEC-architecture §4.14; SPEC-gameplay §14.1). The content pipeline's JSON, byte-compatible with the Python tools
// (design/tools/*.py): `json.dumps(obj, sort_keys=True, separators=(',', ':'))` with the default `ensure_ascii=True`.
// - `ContentJSON.parse` reads any JSON and KEEPS every number's lexeme, so a value read from design/levels.json and written
//   back is the same bytes (`pclevels bundle`: "each level object as it is", CONSISTENCY O-5).
// - `ContentJSON.write` sorts keys by code point, writes compact separators, escapes like Python (\uXXXX lower-case hex
//   for non-ASCII and control characters) and prints doubles with the shortest round-trip repr (Python's `float.__repr__`).
// - `ContentJSON.pyRound(x, digits)` = Python's `round(x, n)` for a float (correctly rounded decimal, ties to even on the
//   exact binary value), which the generator's metrics use.

/// A JSON value. Numbers keep their source lexeme (`.number`) or are typed values written in Python's repr.
public indirect enum JSONValue: Equatable, Sendable {
    case null
    case bool(Bool)
    /// A number exactly as it was written in the source text (re-emitted verbatim).
    case number(String)
    case int(Int)
    case uint(UInt64)
    case double(Double)
    case string(String)
    case array([JSONValue])
    /// Keys in source order; the writer sorts them.
    case object([(String, JSONValue)])

    public static func == (a: JSONValue, b: JSONValue) -> Bool { ContentJSON.write(a) == ContentJSON.write(b) }

    // MARK: accessors (nil when the type does not match)

    public subscript(key: String) -> JSONValue? {
        guard case .object(let kv) = self else { return nil }
        return kv.last { $0.0 == key }?.1
    }

    public var objectPairs: [(String, JSONValue)]? { if case .object(let kv) = self { return kv }; return nil }
    public var arrayValue: [JSONValue]? { if case .array(let a) = self { return a }; return nil }
    public var stringValue: String? { if case .string(let s) = self { return s }; return nil }
    public var boolValue: Bool? { if case .bool(let b) = self { return b }; return nil }
    public var isNull: Bool { if case .null = self { return true }; return false }

    /// An integral number (a lexeme without '.', 'e' or 'E', or a typed int).
    public var intValue: Int? {
        switch self {
        case .int(let i): return i
        case .uint(let u): return u <= UInt64(Int.max) ? Int(u) : nil
        case .number(let s): return s.contains(where: { $0 == "." || $0 == "e" || $0 == "E" }) ? nil : Int(s)
        default: return nil
        }
    }

    public var uint64Value: UInt64? {
        switch self {
        case .uint(let u): return u
        case .int(let i): return i >= 0 ? UInt64(i) : nil
        case .number(let s): return UInt64(s)
        default: return nil
        }
    }

    /// Any number as a Double.
    public var doubleValue: Double? {
        switch self {
        case .int(let i): return Double(i)
        case .uint(let u): return Double(u)
        case .double(let d): return d
        case .number(let s): return Double(s)
        default: return nil
        }
    }

    /// Python truthiness of a JSON value (used where the reference tools write `if o.get(k):`).
    public var isTruthy: Bool {
        switch self {
        case .null: return false
        case .bool(let b): return b
        case .int(let i): return i != 0
        case .uint(let u): return u != 0
        case .double(let d): return d != 0
        case .number: return (doubleValue ?? 0) != 0
        case .string(let s): return !s.isEmpty
        case .array(let a): return !a.isEmpty
        case .object(let kv): return !kv.isEmpty
        }
    }

    /// The same object with `key` set (replaced in place, or appended).
    public func setting(_ key: String, _ value: JSONValue) -> JSONValue {
        guard case .object(var kv) = self else { return self }
        if let i = kv.firstIndex(where: { $0.0 == key }) { kv[i].1 = value } else { kv.append((key, value)) }
        return .object(kv)
    }

    /// The same object without `key`.
    public func removing(_ key: String) -> JSONValue {
        guard case .object(let kv) = self else { return self }
        return .object(kv.filter { $0.0 != key })
    }
}

public enum ContentJSONError: Error, CustomStringConvertible, Equatable {
    case syntax(offset: Int, String)
    public var description: String {
        switch self { case .syntax(let o, let m): return "JSON syntax error at byte \(o): \(m)" }
    }
}

public enum ContentJSON {

    // MARK: writing (Python json.dumps(sort_keys=True, separators=(',', ':')), ensure_ascii=True)

    public static func write(_ v: JSONValue) -> String {
        var out = ""
        out.reserveCapacity(1024)
        write(v, into: &out)
        return out
    }

    public static func data(_ v: JSONValue, newline: Bool = false) -> Data {
        var d = Data(write(v).utf8)
        if newline { d.append(0x0A) }
        return d
    }

    static func write(_ v: JSONValue, into out: inout String) {
        switch v {
        case .null: out += "null"
        case .bool(let b): out += b ? "true" : "false"
        case .number(let s): out += s
        case .int(let i): out += String(i)
        case .uint(let u): out += String(u)
        case .double(let d): out += pyRepr(d)
        case .string(let s): writeString(s, into: &out)
        case .array(let a):
            out += "["
            for (k, x) in a.enumerated() {
                if k > 0 { out += "," }
                write(x, into: &out)
            }
            out += "]"
        case .object(let kv):
            out += "{"
            // Python dicts hold one value per key (the last assignment wins, at the first position); sorting makes
            // the position irrelevant.
            var seen: [String: JSONValue] = [:]
            for (k, x) in kv { seen[k] = x }
            let keys = seen.keys.sorted { Array($0.unicodeScalars.map(\.value)).lexicographicallyPrecedes($1.unicodeScalars.map(\.value)) }
            for (n, k) in keys.enumerated() {
                if n > 0 { out += "," }
                writeString(k, into: &out)
                out += ":"
                write(seen[k]!, into: &out)
            }
            out += "}"
        }
    }

    static func writeString(_ s: String, into out: inout String) {
        out += "\""
        for u in s.utf16 {
            switch u {
            case 0x22: out += "\\\""
            case 0x5C: out += "\\\\"
            case 0x0A: out += "\\n"
            case 0x0D: out += "\\r"
            case 0x09: out += "\\t"
            case 0x08: out += "\\b"
            case 0x0C: out += "\\f"
            case 0x20...0x7E: out.unicodeScalars.append(Unicode.Scalar(u)!)
            default:
                let h = String(u, radix: 16)
                out += "\\u" + String(repeating: "0", count: 4 - h.count) + h
            }
        }
        out += "\""
    }

    /// Python's `repr(float)`: the shortest string that round-trips, "x.0" for integral values, exponent form outside
    /// [1e-4, 1e16) as "1e-05" / "1e+16".
    public static func pyRepr(_ d: Double) -> String {
        if d.isNaN { return "NaN" }
        if d.isInfinite { return d < 0 ? "-Infinity" : "Infinity" }
        if d == 0 { return d.sign == .minus ? "-0.0" : "0.0" }
        // Swift's description is the shortest round-trip digit string too; only the layout can differ.
        let s = d.description
        let neg = s.hasPrefix("-")
        let body = neg ? String(s.dropFirst()) : s
        var digits = ""
        var exp10 = 0
        if let e = body.firstIndex(where: { $0 == "e" || $0 == "E" }) {
            let mant = body[..<e]
            exp10 = Int(body[body.index(after: e)...])!
            let parts = mant.split(separator: ".", omittingEmptySubsequences: false)
            digits = String(parts[0]) + (parts.count > 1 ? String(parts[1]) : "")
            exp10 += parts[0].count
        } else {
            let parts = body.split(separator: ".", omittingEmptySubsequences: false)
            digits = String(parts[0]) + (parts.count > 1 ? String(parts[1]) : "")
            exp10 = parts[0].count
        }
        // normalise: strip leading zeros (adjusting the exponent) and trailing zeros
        while digits.count > 1 && digits.hasPrefix("0") { digits.removeFirst(); exp10 -= 1 }
        while digits.count > 1 && digits.hasSuffix("0") { digits.removeLast() }
        // value = 0.digits × 10^exp10 ; Python's decimal point position: decpt = exp10
        let decpt = exp10
        let n = digits.count
        var r: String
        if decpt > -4 && decpt <= 16 {
            if decpt <= 0 {
                r = "0." + String(repeating: "0", count: -decpt) + digits
            } else if decpt >= n {
                r = digits + String(repeating: "0", count: decpt - n) + ".0"
            } else {
                let i = digits.index(digits.startIndex, offsetBy: decpt)
                r = String(digits[..<i]) + "." + String(digits[i...])
            }
        } else {
            let e = decpt - 1
            let mant = n == 1 ? digits : String(digits.first!) + "." + String(digits.dropFirst())
            let es = e < 0 ? "-" + (abs(e) < 10 ? "0" : "") + String(abs(e)) : "+" + (e < 10 ? "0" : "") + String(e)
            r = mant + "e" + es
        }
        return neg ? "-" + r : r
    }

    /// Python's `round(x, ndigits)` for a float: the correctly rounded decimal (ties to even on the exact binary value),
    /// converted back to the nearest double. Apple's printf is exact (gdtoa), like CPython's `_Py_dg_dtoa` mode 3.
    public static func pyRound(_ x: Double, _ ndigits: Int) -> Double {
        guard x.isFinite else { return x }
        let s = String(format: "%.\(ndigits)f", x)
        return Double(s)!
    }

    // MARK: parsing (lexeme-preserving)

    public static func parse(_ data: Data) throws -> JSONValue {
        var p = Parser(bytes: [UInt8](data))
        p.skipWS()
        let v = try p.value()
        p.skipWS()
        guard p.i == p.b.count else { throw ContentJSONError.syntax(offset: p.i, "trailing characters") }
        return v
    }

    public static func parse(_ s: String) throws -> JSONValue { try parse(Data(s.utf8)) }

    struct Parser {
        let b: [UInt8]
        var i = 0
        init(bytes: [UInt8]) { b = bytes }

        mutating func skipWS() {
            while i < b.count, b[i] == 0x20 || b[i] == 0x0A || b[i] == 0x0D || b[i] == 0x09 { i += 1 }
        }

        func fail(_ m: String) -> ContentJSONError { .syntax(offset: i, m) }

        mutating func expect(_ lit: String) throws {
            for c in lit.utf8 {
                guard i < b.count, b[i] == c else { throw fail("expected \(lit)") }
                i += 1
            }
        }

        mutating func value() throws -> JSONValue {
            guard i < b.count else { throw fail("unexpected end") }
            switch b[i] {
            case UInt8(ascii: "{"):
                i += 1
                var kv: [(String, JSONValue)] = []
                skipWS()
                if i < b.count, b[i] == UInt8(ascii: "}") { i += 1; return .object(kv) }
                while true {
                    skipWS()
                    guard i < b.count, b[i] == UInt8(ascii: "\"") else { throw fail("expected a key") }
                    let k = try string()
                    skipWS()
                    try expect(":")
                    skipWS()
                    kv.append((k, try value()))
                    skipWS()
                    guard i < b.count else { throw fail("unexpected end in object") }
                    if b[i] == UInt8(ascii: ",") { i += 1; continue }
                    if b[i] == UInt8(ascii: "}") { i += 1; return .object(kv) }
                    throw fail("expected , or }")
                }
            case UInt8(ascii: "["):
                i += 1
                var a: [JSONValue] = []
                skipWS()
                if i < b.count, b[i] == UInt8(ascii: "]") { i += 1; return .array(a) }
                while true {
                    skipWS()
                    a.append(try value())
                    skipWS()
                    guard i < b.count else { throw fail("unexpected end in array") }
                    if b[i] == UInt8(ascii: ",") { i += 1; continue }
                    if b[i] == UInt8(ascii: "]") { i += 1; return .array(a) }
                    throw fail("expected , or ]")
                }
            case UInt8(ascii: "\""):
                return .string(try string())
            case UInt8(ascii: "t"): try expect("true"); return .bool(true)
            case UInt8(ascii: "f"): try expect("false"); return .bool(false)
            case UInt8(ascii: "n"): try expect("null"); return .null
            default:
                let start = i
                if b[i] == UInt8(ascii: "-") { i += 1 }
                while i < b.count, (b[i] >= 0x30 && b[i] <= 0x39) || b[i] == UInt8(ascii: ".") || b[i] == UInt8(ascii: "e")
                        || b[i] == UInt8(ascii: "E") || b[i] == UInt8(ascii: "+") || b[i] == UInt8(ascii: "-") { i += 1 }
                guard i > start, let s = String(bytes: b[start..<i], encoding: .ascii), Double(s) != nil else {
                    throw fail("bad number")
                }
                return .number(s)
            }
        }

        mutating func hex4() throws -> UInt16 {
            guard i + 4 <= b.count, let s = String(bytes: b[i..<i + 4], encoding: .ascii), let v = UInt16(s, radix: 16) else {
                throw fail("bad \\u escape")
            }
            i += 4
            return v
        }

        mutating func string() throws -> String {
            i += 1
            var units: [UInt16] = []
            var raw: [UInt8] = []
            func flushRaw() { if !raw.isEmpty { units.append(contentsOf: String(decoding: raw, as: UTF8.self).utf16); raw.removeAll() } }
            while true {
                guard i < b.count else { throw fail("unterminated string") }
                let c = b[i]
                if c == UInt8(ascii: "\"") { i += 1; break }
                if c == UInt8(ascii: "\\") {
                    flushRaw()
                    i += 1
                    guard i < b.count else { throw fail("bad escape") }
                    let e = b[i]; i += 1
                    switch e {
                    case UInt8(ascii: "\""): units.append(0x22)
                    case UInt8(ascii: "\\"): units.append(0x5C)
                    case UInt8(ascii: "/"): units.append(0x2F)
                    case UInt8(ascii: "b"): units.append(0x08)
                    case UInt8(ascii: "f"): units.append(0x0C)
                    case UInt8(ascii: "n"): units.append(0x0A)
                    case UInt8(ascii: "r"): units.append(0x0D)
                    case UInt8(ascii: "t"): units.append(0x09)
                    case UInt8(ascii: "u"): units.append(try hex4())
                    default: throw fail("bad escape")
                    }
                } else {
                    raw.append(c)
                    i += 1
                }
            }
            flushRaw()
            return String(decoding: units, as: UTF16.self)
        }
    }
}
