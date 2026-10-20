import Foundation

/// Finds C2PA Content Credentials embedded in JPEG (APP11 segments) or PNG
/// ("caBX" chunk) files and summarizes the active manifest. Returns nil when
/// there are none, which is the usual case: most sites, Bluesky included, strip
/// them on upload.
enum ContentCredentialsReader {
    /// Credentials stores are small; ignore anything implausibly large.
    private static let maxStoreSize = 8 << 20

    static func read(_ data: Data) -> ContentCredentials? {
        guard let store = manifestStore(in: data) else { return nil }
        let boxes = JUMBFBox.parse(store)
        guard let root = boxes.lazy.compactMap({ $0.find(label: "c2pa") }).first,
              // The active manifest is the last one in the store.
              let manifest = root.children.last(where: { $0.type == "jumb" && $0.label != nil })
        else { return nil }
        return summarize(manifest)
    }

    // MARK: Containers

    static func manifestStore(in data: Data) -> Data? {
        let bytes = [UInt8](data)
        if bytes.starts(with: [0xFF, 0xD8]) { return jpegStore(bytes) }
        if bytes.starts(with: [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) { return pngStore(bytes) }
        return nil
    }

    /// APP11 segments: "JP", a 2-byte box instance, a 4-byte sequence number,
    /// then box data. Continuations repeat the 8-byte box header, which is skipped.
    private static func jpegStore(_ bytes: [UInt8]) -> Data? {
        var parts: [UInt16: Data] = [:]
        var order: [UInt16] = []
        var index = 2
        while index + 4 <= bytes.count, bytes[index] == 0xFF {
            let marker = bytes[index + 1]
            if marker == 0xDA || marker == 0xD9 { break }        // image data / end
            if (0xD0...0xD7).contains(marker) || marker == 0x01 { index += 2; continue }
            let length = Int(bytes[index + 2]) << 8 | Int(bytes[index + 3])
            let start = index + 4
            let end = index + 2 + length
            guard length >= 2, end <= bytes.count else { break }
            if marker == 0xEB, end - start >= 8, bytes[start] == 0x4A, bytes[start + 1] == 0x50 {
                let instance = UInt16(bytes[start + 2]) << 8 | UInt16(bytes[start + 3])
                let sequence = bytes[start + 4..<start + 8].reduce(UInt32(0)) { $0 << 8 | UInt32($1) }
                let body = bytes[start + 8..<end]
                if parts[instance] == nil { order.append(instance) }
                if sequence <= 1 {
                    parts[instance] = Data(body)
                } else {
                    parts[instance, default: Data()].append(contentsOf: body.dropFirst(8))
                }
                if (parts[instance]?.count ?? 0) > maxStoreSize { return nil }
            }
            index = end
        }
        for instance in order {
            if let data = parts[instance], JUMBFBox.parse(data).contains(where: { $0.find(label: "c2pa") != nil }) {
                return data
            }
        }
        return nil
    }

    private static func pngStore(_ bytes: [UInt8]) -> Data? {
        var index = 8
        while index + 12 <= bytes.count {
            let length = Int(bytes[index..<index + 4].reduce(UInt32(0)) { $0 << 8 | UInt32($1) })
            let type = String(decoding: bytes[index + 4..<index + 8], as: UTF8.self)
            let start = index + 8
            guard length <= maxStoreSize, start + length + 4 <= bytes.count else { return nil }
            if type == "caBX" { return Data(bytes[start..<start + length]) }
            if type == "IEND" { return nil }
            index = start + length + 4
        }
        return nil
    }

    // MARK: Manifest

    private static func summarize(_ manifest: JUMBFBox) -> ContentCredentials {
        let claim = manifest.children.first { $0.label?.hasPrefix("c2pa.claim") == true }?.cbor
        let actionList = manifest.all(labelPrefix: "c2pa.actions")
            .compactMap(\.cbor)
            .flatMap { $0["actions"]?.array ?? [] }

        let sourceTypes = actionList.compactMap { $0["digitalSourceType"]?.string }
        let names = actionList.compactMap { $0["action"]?.string }.map(actionName)
        var unique: [String] = []
        for name in names where !unique.contains(name) { unique.append(name) }

        let agent = actionList.lazy.compactMap { $0["softwareAgent"]?.string ?? $0["softwareAgent"]?["name"]?.string }.first

        return ContentCredentials(
            generator: generatorName(claim) ?? agent,
            source: source(from: sourceTypes),
            actions: unique
        )
    }

    private static func generatorName(_ claim: CBOR?) -> String? {
        guard let claim else { return nil }
        if let info = claim["claim_generator_info"] {
            let first = info.array?.first ?? info
            if let name = first["name"]?.string {
                return [name, first["version"]?.string].compactMap { $0 }.joined(separator: " ")
            }
        }
        // v1 claims: "Adobe_Firefly/1.0 c2pa-rs/0.25" → "Adobe Firefly"
        guard let raw = claim["claim_generator"]?.string,
              let first = raw.split(separator: " ").first?.split(separator: "/").first
        else { return nil }
        return first.replacingOccurrences(of: "_", with: " ")
    }

    /// IPTC digital source types, most telling first.
    static func source(from types: [String]) -> ContentCredentials.Source {
        let names = types.compactMap { $0.split(separator: "/").last.map(String.init) }
        if names.contains(where: { $0 == "trainedAlgorithmicMedia" || $0 == "algorithmicMedia" }) { return .aiGenerated }
        if names.contains("compositeWithTrainedAlgorithmicMedia") { return .aiEdited }
        if names.contains(where: { $0 == "digitalCapture" || $0 == "computationalCapture" }) { return .camera }
        return .unspecified
    }

    static func actionName(_ action: String) -> String {
        let known = [
            "c2pa.created": "Created", "c2pa.edited": "Edited", "c2pa.opened": "Opened",
            "c2pa.placed": "Added content", "c2pa.cropped": "Cropped", "c2pa.resized": "Resized",
            "c2pa.color_adjustments": "Color adjusted", "c2pa.filtered": "Filtered",
            "c2pa.converted": "Converted", "c2pa.drawing": "Drawn on", "c2pa.removed": "Removed content",
            "c2pa.published": "Published", "c2pa.transcoded": "Re-encoded", "c2pa.repackaged": "Repackaged",
        ]
        if let name = known[action] { return name }
        let tail = action.split(separator: ".").last.map(String.init) ?? action
        let words = tail.replacingOccurrences(of: "_", with: " ")
        return words.prefix(1).uppercased() + words.dropFirst()
    }
}
