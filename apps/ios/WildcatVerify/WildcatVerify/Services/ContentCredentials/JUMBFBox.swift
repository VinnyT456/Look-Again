import Foundation

/// A JUMBF box (ISO/IEC 19566-5), the container C2PA stores manifests in.
/// Superboxes ("jumb") carry a label from their description box ("jumd").
struct JUMBFBox: Sendable {
    var type: String
    var label: String?
    var payload: Data
    var children: [JUMBFBox]

    /// First descendant superbox (including self) with this label.
    func find(label wanted: String) -> JUMBFBox? {
        if label == wanted { return self }
        for child in children {
            if let found = child.find(label: wanted) { return found }
        }
        return nil
    }

    /// Child superboxes whose label starts with `prefix`, searched recursively.
    func all(labelPrefix prefix: String) -> [JUMBFBox] {
        var found: [JUMBFBox] = []
        if label?.hasPrefix(prefix) == true { found.append(self) }
        for child in children { found += child.all(labelPrefix: prefix) }
        return found
    }

    /// The CBOR content box inside a superbox, decoded.
    var cbor: CBOR? {
        children.first { $0.type == "cbor" }.flatMap { CBOR.decode($0.payload) }
    }

    static func parse(_ data: Data, depth: Int = 0) -> [JUMBFBox] {
        guard depth < 16 else { return [] }
        let bytes = [UInt8](data)
        var boxes: [JUMBFBox] = []
        var index = 0
        while index + 8 <= bytes.count {
            var length = UInt64(bytes[index..<index + 4].reduce(UInt32(0)) { $0 << 8 | UInt32($1) })
            let type = String(decoding: bytes[index + 4..<index + 8], as: UTF8.self)
            var header = 8
            if length == 1 {
                guard index + 16 <= bytes.count else { break }
                length = bytes[index + 8..<index + 16].reduce(UInt64(0)) { $0 << 8 | UInt64($1) }
                header = 16
            } else if length == 0 {
                length = UInt64(bytes.count - index)
            }
            guard length >= UInt64(header), length <= UInt64(bytes.count - index) else { break }
            let payload = Data(bytes[index + header..<index + Int(length)])
            var box = JUMBFBox(type: type, label: nil, payload: payload, children: [])
            if type == "jumb" {
                box.children = parse(payload, depth: depth + 1)
                box.label = box.children.first { $0.type == "jumd" }.flatMap { description($0.payload) }
            }
            boxes.append(box)
            index += Int(length)
        }
        return boxes
    }

    /// The label in a description box: 16-byte type UUID, a toggles byte,
    /// then a NUL-terminated UTF-8 label when bit 0x02 is set.
    private static func description(_ payload: Data) -> String? {
        let bytes = [UInt8](payload)
        guard bytes.count > 17, bytes[16] & 0x02 != 0 else { return nil }
        let labelBytes = bytes[17...].prefix { $0 != 0 }
        return String(bytes: labelBytes, encoding: .utf8)
    }
}
