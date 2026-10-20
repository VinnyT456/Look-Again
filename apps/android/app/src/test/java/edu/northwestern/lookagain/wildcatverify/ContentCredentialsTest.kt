package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.Cbor
import edu.northwestern.lookagain.wildcatverify.data.ContentCredentialsReader
import edu.northwestern.lookagain.wildcatverify.model.ContentCredentials
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.ByteArrayOutputStream

/** Builds small C2PA files by hand: CBOR, JUMBF boxes, and JPEG/PNG wrappers (same fixtures as the iOS tests). */
private object C2pa {
    fun head(major: Int, n: Int): ByteArray = when {
        n < 24 -> byteArrayOf((major shl 5 or n).toByte())
        n < 256 -> byteArrayOf((major shl 5 or 24).toByte(), n.toByte())
        else -> byteArrayOf((major shl 5 or 25).toByte(), (n shr 8).toByte(), (n and 0xFF).toByte())
    }
    fun text(s: String) = head(3, s.toByteArray().size) + s.toByteArray()
    fun map(pairs: List<Pair<String, ByteArray>>) = head(5, pairs.size) + pairs.fold(ByteArray(0)) { acc, (k, v) -> acc + text(k) + v }
    fun array(items: List<ByteArray>) = head(4, items.size) + items.fold(ByteArray(0)) { acc, b -> acc + b }
    fun u32(n: Int) = byteArrayOf((n ushr 24).toByte(), (n ushr 16).toByte(), (n ushr 8).toByte(), n.toByte())
    fun box(type: String, payload: ByteArray) = u32(8 + payload.size) + type.toByteArray() + payload
    fun superbox(label: String, children: List<ByteArray>): ByteArray {
        val description = box("jumd", ByteArray(16) + byteArrayOf(0x03) + label.toByteArray() + byteArrayOf(0))
        return box("jumb", description + children.fold(ByteArray(0)) { acc, b -> acc + b })
    }

    fun store(generator: String, sourceType: String?, actions: List<String>): ByteArray {
        val items = actions.map { name ->
            val pairs = mutableListOf("action" to text(name))
            if (sourceType != null && name == "c2pa.created") pairs += "digitalSourceType" to text(sourceType)
            map(pairs)
        }
        val assertions = superbox("c2pa.assertions", listOf(superbox("c2pa.actions", listOf(box("cbor", map(listOf("actions" to array(items))))))))
        val claim = superbox("c2pa.claim", listOf(box("cbor", map(listOf("claim_generator" to text(generator))))))
        val older = superbox("urn:uuid:old", listOf(superbox("c2pa.claim", listOf(box("cbor", map(listOf("claim_generator" to text("Old_App/1.0"))))))))
        return superbox("c2pa", listOf(older, superbox("urn:uuid:active", listOf(assertions, claim))))
    }

    /** A JPEG header with the store split across APP11 segments. */
    fun jpeg(store: ByteArray, chunk: Int = 40): ByteArray {
        val out = ByteArrayOutputStream()
        out.write(byteArrayOf(0xFF.toByte(), 0xD8.toByte()))
        val header = store.copyOfRange(0, 8)
        var offset = 0
        var sequence = 1
        while (offset < store.size) {
            val piece = store.copyOfRange(offset, minOf(offset + chunk, store.size))
            val body = if (sequence == 1) piece else header + piece
            offset += chunk
            val segment = "JP".toByteArray() + byteArrayOf(0, 1) + u32(sequence) + body
            val length = segment.size + 2
            out.write(byteArrayOf(0xFF.toByte(), 0xEB.toByte(), (length shr 8).toByte(), (length and 0xFF).toByte()))
            out.write(segment)
            sequence++
        }
        out.write(byteArrayOf(0xFF.toByte(), 0xDA.toByte(), 0x00, 0x02, 0xFF.toByte(), 0xD9.toByte()))
        return out.toByteArray()
    }

    fun png(store: ByteArray): ByteArray {
        fun chunk(type: String, data: ByteArray) = u32(data.size) + type.toByteArray() + data + ByteArray(4)
        return byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A) + chunk("IHDR", ByteArray(13)) + chunk("caBX", store) + chunk("IEND", ByteArray(0))
    }
}

class ContentCredentialsTest {
    private val aiType = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

    @Test fun readsAnAIGeneratedJpegSplitAcrossSegments() {
        val store = C2pa.store("Adobe_Firefly/1.0 c2pa-rs/0.25", aiType, listOf("c2pa.created", "c2pa.cropped"))
        val credentials = ContentCredentialsReader.read(C2pa.jpeg(store))
        assertNotNull(credentials)
        credentials!!
        assertEquals(ContentCredentials.Source.AI_GENERATED, credentials.source)
        assertEquals("From the active (last) manifest, tidied", "Adobe Firefly", credentials.generator)
        assertEquals(listOf("Created", "Cropped"), credentials.actions)
    }

    @Test fun readsPng() {
        val store = C2pa.store("Camera_App/2", "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture", listOf("c2pa.created"))
        assertEquals(ContentCredentials.Source.CAMERA, ContentCredentialsReader.read(C2pa.png(store))?.source)
    }

    @Test fun plainFilesHaveNone() {
        assertNull(ContentCredentialsReader.read(byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xD9.toByte())))
        assertNull(ContentCredentialsReader.read("not an image".toByteArray()))
    }

    @Test fun truncatedOrHostileFilesDontCrash() {
        val full = C2pa.jpeg(C2pa.store("X/1", aiType, listOf("c2pa.created")))
        for (cut in 4 until full.size step 7) ContentCredentialsReader.read(full.copyOfRange(0, cut))
        // A box claiming to be far bigger than the file.
        val bogus = byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xEB.toByte(), 0x00, 0x12) + "JP".toByteArray() +
            byteArrayOf(0, 1, 0, 0, 0, 1, 0x7F, 0xFF.toByte(), 0xFF.toByte(), 0xFF.toByte()) + "jumb".toByteArray()
        assertNull(ContentCredentialsReader.read(bogus))
        // Deeply nested CBOR arrays stop at the depth cap.
        assertNull(Cbor.decode(ByteArray(10_000) { 0x81.toByte() }))
    }

    @Test fun sourceTypesRankAIFirst() {
        val base = "http://cv.iptc.org/newscodes/digitalsourcetype/"
        assertEquals(ContentCredentials.Source.AI_EDITED, ContentCredentialsReader.source(listOf(base + "digitalCapture", base + "compositeWithTrainedAlgorithmicMedia")))
        assertEquals(ContentCredentials.Source.UNSPECIFIED, ContentCredentialsReader.source(emptyList()))
        assertEquals("Color adjusted", ContentCredentialsReader.actionName("c2pa.color_adjustments"))
        assertEquals("Sharpen more", ContentCredentialsReader.actionName("com.example.sharpen_more"))
    }

    @Test fun cborDecodesTheBasics() {
        val value = Cbor.decode(C2pa.map(listOf("a" to C2pa.text("b"), "n" to byteArrayOf(0x18, 0x64))))!!
        assertEquals("b", value["a"]?.string)
        assertEquals(Cbor.Int(100), value["n"])
        assertEquals(Cbor.Int(-257), Cbor.decode(byteArrayOf(0x39, 0x01, 0x00)))
        assertEquals(Cbor.Float(1.0), Cbor.decode(byteArrayOf(0xF9.toByte(), 0x3C, 0x00)))
        assertEquals("Indefinite arrays", 2, Cbor.decode(byteArrayOf(0x9F.toByte(), 0x01, 0x02, 0xFF.toByte()))?.array?.size)
    }
}
