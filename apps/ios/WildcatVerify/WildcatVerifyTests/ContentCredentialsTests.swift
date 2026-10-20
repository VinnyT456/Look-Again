import Foundation
import Testing
@testable import WildcatVerify

/// Builds small C2PA files by hand: CBOR, JUMBF boxes, and JPEG/PNG wrappers.
private enum C2PAFixture {
    static func head(_ major: UInt8, _ n: Int) -> [UInt8] {
        n < 24 ? [major << 5 | UInt8(n)] : n < 256 ? [major << 5 | 24, UInt8(n)] : [major << 5 | 25, UInt8(n >> 8), UInt8(n & 0xFF)]
    }
    static func text(_ s: String) -> [UInt8] { head(3, s.utf8.count) + Array(s.utf8) }
    static func map(_ pairs: [(String, [UInt8])]) -> [UInt8] {
        head(5, pairs.count) + pairs.flatMap { text($0.0) + $0.1 }
    }
    static func array(_ items: [[UInt8]]) -> [UInt8] { head(4, items.count) + items.flatMap { $0 } }

    static func box(_ type: String, _ payload: [UInt8]) -> [UInt8] {
        let length = UInt32(8 + payload.count)
        return withUnsafeBytes(of: length.bigEndian, Array.init) + Array(type.utf8) + payload
    }
    static func superbox(_ label: String, _ children: [[UInt8]]) -> [UInt8] {
        let description = box("jumd", [UInt8](repeating: 0, count: 16) + [0x03] + Array(label.utf8) + [0])
        return box("jumb", description + children.flatMap { $0 })
    }

    static func store(generator: String, sourceType: String?, actions: [String]) -> [UInt8] {
        let actionItems = actions.map { name -> [UInt8] in
            var pairs: [(String, [UInt8])] = [("action", text(name))]
            if let sourceType, name == "c2pa.created" { pairs.append(("digitalSourceType", text(sourceType))) }
            return map(pairs)
        }
        let assertions = superbox("c2pa.assertions", [
            superbox("c2pa.actions", [box("cbor", map([("actions", array(actionItems))]))]),
        ])
        let claim = superbox("c2pa.claim", [box("cbor", map([("claim_generator", text(generator))]))])
        let older = superbox("urn:uuid:old", [superbox("c2pa.claim", [box("cbor", map([("claim_generator", text("Old_App/1.0"))]))])])
        return superbox("c2pa", [older, superbox("urn:uuid:active", [assertions, claim])])
    }

    /// A JPEG header with the store split across APP11 segments.
    static func jpeg(_ store: [UInt8], chunk: Int = 40) -> Data {
        var bytes: [UInt8] = [0xFF, 0xD8]
        let header = Array(store.prefix(8))
        var offset = 0
        var sequence: UInt32 = 1
        while offset < store.count {
            let body: [UInt8] = sequence == 1
                ? Array(store[offset..<min(offset + chunk, store.count)])
                : header + Array(store[offset..<min(offset + chunk, store.count)])
            offset += chunk
            let segment = Array("JP".utf8) + [0, 1] + withUnsafeBytes(of: sequence.bigEndian, Array.init) + body
            let length = UInt16(segment.count + 2)
            bytes += [0xFF, 0xEB, UInt8(length >> 8), UInt8(length & 0xFF)] + segment
            sequence += 1
        }
        bytes += [0xFF, 0xDA, 0x00, 0x02, 0xFF, 0xD9]
        return Data(bytes)
    }

    static func png(_ store: [UInt8]) -> Data {
        func chunk(_ type: String, _ data: [UInt8]) -> [UInt8] {
            withUnsafeBytes(of: UInt32(data.count).bigEndian, Array.init) + Array(type.utf8) + data + [0, 0, 0, 0]
        }
        return Data([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A] + chunk("IHDR", [UInt8](repeating: 0, count: 13)) + chunk("caBX", store) + chunk("IEND", []))
    }
}

struct ContentCredentialsTests {
    private let aiType = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

    @Test func readsAnAIGeneratedJPEGSplitAcrossSegments() throws {
        let store = C2PAFixture.store(generator: "Adobe_Firefly/1.0 c2pa-rs/0.25", sourceType: aiType, actions: ["c2pa.created", "c2pa.cropped"])
        let credentials = try #require(ContentCredentialsReader.read(C2PAFixture.jpeg(store)))
        #expect(credentials.source == .aiGenerated)
        #expect(credentials.generator == "Adobe Firefly", "From the active (last) manifest, tidied")
        #expect(credentials.actions == ["Created", "Cropped"])
    }

    @Test func readsPNG() throws {
        let store = C2PAFixture.store(generator: "Camera_App/2", sourceType: "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture", actions: ["c2pa.created"])
        let credentials = try #require(ContentCredentialsReader.read(C2PAFixture.png(store)))
        #expect(credentials.source == .camera)
    }

    @Test func plainImagesHaveNone() {
        #expect(ContentCredentialsReader.read(TestImages.pngData()) == nil)
        #expect(ContentCredentialsReader.read(Data([0xFF, 0xD8, 0xFF, 0xD9])) == nil)
        #expect(ContentCredentialsReader.read(Data("not an image".utf8)) == nil)
    }

    @Test func truncatedOrHostileFilesDontCrash() {
        let store = C2PAFixture.store(generator: "X/1", sourceType: aiType, actions: ["c2pa.created"])
        let full = C2PAFixture.jpeg(store)
        for cut in stride(from: 4, to: full.count, by: 7) {
            _ = ContentCredentialsReader.read(full.prefix(cut))
        }
        // A box claiming to be far bigger than the file.
        let bogus = Data([0xFF, 0xD8, 0xFF, 0xEB, 0x00, 0x12] + Array("JP".utf8) + [0, 1, 0, 0, 0, 1] + [0x7F, 0xFF, 0xFF, 0xFF] + Array("jumb".utf8))
        #expect(ContentCredentialsReader.read(bogus) == nil)
        // Deeply nested CBOR arrays stop at the depth cap.
        #expect(CBOR.decode(Data(repeating: 0x81, count: 10_000)) == nil)
    }

    @Test func sourceTypesRankAIFirst() {
        let base = "http://cv.iptc.org/newscodes/digitalsourcetype/"
        #expect(ContentCredentialsReader.source(from: [base + "digitalCapture", base + "compositeWithTrainedAlgorithmicMedia"]) == .aiEdited)
        #expect(ContentCredentialsReader.source(from: []) == .unspecified)
        #expect(ContentCredentialsReader.actionName("c2pa.color_adjustments") == "Color adjusted")
        #expect(ContentCredentialsReader.actionName("com.example.sharpen_more") == "Sharpen more")
    }

    @Test func cborDecodesTheBasics() throws {
        let value = try #require(CBOR.decode(Data(C2PAFixture.map([("a", C2PAFixture.text("b")), ("n", [0x18, 0x64])]))))
        #expect(value["a"]?.string == "b")
        #expect(value["n"] == .int(100))
        #expect(CBOR.decode(Data([0x39, 0x01, 0x00])) == .int(-257))
        #expect(CBOR.decode(Data([0xF9, 0x3C, 0x00])) == .float(1.0))
        #expect(CBOR.decode(Data([0x9F, 0x01, 0x02, 0xFF]))?.array?.count == 2, "Indefinite arrays")
    }

    @MainActor
    @Test func uploadsCarryTheirCredentials() async throws {
        let store = C2PAFixture.store(generator: "Adobe_Firefly/1.0", sourceType: aiType, actions: ["c2pa.created"])
        // A real PNG with a caBX chunk inserted after IHDR.
        var png = [UInt8](TestImages.pngData())
        let insertAt = 8 + 25
        let chunk = withUnsafeBytes(of: UInt32(store.count).bigEndian, Array.init) + Array("caBX".utf8) + store + [0, 0, 0, 0]
        png.insert(contentsOf: chunk, at: insertAt)

        let pipeline = CheckPipeline(bluesky: StubBluesky(result: .failure(.network)), classifier: StubClassifier(), images: ImageRepository())
        let item = try await pipeline.checkImage(data: Data(png))
        #expect(item.credentials?.source == .aiGenerated)
        #expect(item.credentials?.generator == "Adobe Firefly")
    }
}
