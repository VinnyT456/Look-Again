import Foundation

/// A decoded CBOR value (RFC 8949), just enough to read C2PA claims and
/// assertions. Untrusted input: every read is bounds-checked and nesting is capped.
indirect enum CBOR: Hashable, Sendable {
    case int(Int64)
    case bytes(Data)
    case text(String)
    case array([CBOR])
    case map([CBOR: CBOR])
    case tagged(UInt64, CBOR)
    case bool(Bool)
    case null
    case float(Double)

    subscript(key: String) -> CBOR? {
        guard case .map(let map) = untagged else { return nil }
        return map[.text(key)]
    }

    var string: String? {
        if case .text(let value) = untagged { return value }
        return nil
    }

    var array: [CBOR]? {
        if case .array(let value) = untagged { return value }
        return nil
    }

    private var untagged: CBOR {
        if case .tagged(_, let inner) = self { return inner.untagged }
        return self
    }

    static func decode(_ data: Data) -> CBOR? {
        var reader = Reader(bytes: [UInt8](data))
        return try? reader.value(depth: 0)
    }

    private struct Reader {
        struct Malformed: Error {}
        static let maxDepth = 32

        let bytes: [UInt8]
        var index = 0

        mutating func byte() throws -> UInt8 {
            guard index < bytes.count else { throw Malformed() }
            defer { index += 1 }
            return bytes[index]
        }

        mutating func take(_ count: UInt64) throws -> ArraySlice<UInt8> {
            guard count <= UInt64(bytes.count - index) else { throw Malformed() }
            let end = index + Int(count)
            defer { index = end }
            return bytes[index..<end]
        }

        mutating func argument(_ info: UInt8) throws -> UInt64 {
            switch info {
            case 0..<24: return UInt64(info)
            case 24: return UInt64(try byte())
            case 25: return try take(2).reduce(0) { $0 << 8 | UInt64($1) }
            case 26: return try take(4).reduce(0) { $0 << 8 | UInt64($1) }
            case 27: return try take(8).reduce(0) { $0 << 8 | UInt64($1) }
            default: throw Malformed()
            }
        }

        mutating func value(depth: Int) throws -> CBOR {
            guard depth < Self.maxDepth else { throw Malformed() }
            let initial = try byte()
            let major = initial >> 5
            let info = initial & 0x1F

            if info == 31 { return try indefinite(major: major, depth: depth) }

            switch major {
            case 0:
                let n = try argument(info)
                guard n <= UInt64(Int64.max) else { throw Malformed() }
                return .int(Int64(n))
            case 1:
                let n = try argument(info)
                guard n < UInt64(Int64.max) else { throw Malformed() }
                return .int(-1 - Int64(n))
            case 2:
                return .bytes(Data(try take(argument(info))))
            case 3:
                guard let text = String(bytes: try take(argument(info)), encoding: .utf8) else { throw Malformed() }
                return .text(text)
            case 4:
                let count = try argument(info)
                guard count <= UInt64(bytes.count - index) else { throw Malformed() }
                return .array(try (0..<count).map { _ in try value(depth: depth + 1) })
            case 5:
                let count = try argument(info)
                guard count <= UInt64(bytes.count - index) else { throw Malformed() }
                var map: [CBOR: CBOR] = [:]
                for _ in 0..<count {
                    let key = try value(depth: depth + 1)
                    map[key] = try value(depth: depth + 1)
                }
                return .map(map)
            case 6:
                let tag = try argument(info)
                return .tagged(tag, try value(depth: depth + 1))
            default:
                return try simple(info)
            }
        }

        mutating func simple(_ info: UInt8) throws -> CBOR {
            switch info {
            case 20: return .bool(false)
            case 21: return .bool(true)
            case 22, 23: return .null
            case 25:
                let bits = UInt16(try argument(25))
                return .float(Double(Float16(bitPattern: bits)))
            case 26: return .float(Double(Float(bitPattern: UInt32(try argument(26)))))
            case 27: return .float(Double(bitPattern: try argument(27)))
            default: throw Malformed()
            }
        }

        /// Indefinite-length strings, arrays and maps, ended by 0xFF.
        mutating func indefinite(major: UInt8, depth: Int) throws -> CBOR {
            var items: [CBOR] = []
            while true {
                guard index < bytes.count else { throw Malformed() }
                if bytes[index] == 0xFF { index += 1; break }
                items.append(try value(depth: depth + 1))
            }
            switch major {
            case 2:
                return .bytes(items.reduce(into: Data()) { if case .bytes(let d) = $1 { $0.append(d) } })
            case 3:
                return .text(items.compactMap(\.string).joined())
            case 4:
                return .array(items)
            case 5:
                guard items.count.isMultiple(of: 2) else { throw Malformed() }
                var map: [CBOR: CBOR] = [:]
                for pair in stride(from: 0, to: items.count, by: 2) { map[items[pair]] = items[pair + 1] }
                return .map(map)
            default:
                throw Malformed()
            }
        }
    }
}
