package edu.northwestern.lookagain.wildcatverify.data

import edu.northwestern.lookagain.wildcatverify.model.ContentCredentials

/**
 * A decoded CBOR value (RFC 8949), just enough to read C2PA claims and
 * assertions. Untrusted input: every read is bounds-checked and nesting is capped.
 */
sealed interface Cbor {
    data class Int(val value: Long) : Cbor
    class Bytes(val value: ByteArray) : Cbor {
        override fun equals(other: Any?) = other is Bytes && value.contentEquals(other.value)
        override fun hashCode() = value.contentHashCode()
    }
    data class Text(val value: String) : Cbor
    data class Array(val items: List<Cbor>) : Cbor
    data class Map(val entries: kotlin.collections.Map<Cbor, Cbor>) : Cbor
    data class Tagged(val tag: Long, val inner: Cbor) : Cbor
    data class Bool(val value: Boolean) : Cbor
    data object Null : Cbor
    data class Float(val value: Double) : Cbor

    val untagged: Cbor get() = if (this is Tagged) inner.untagged else this

    operator fun get(key: String): Cbor? = (untagged as? Map)?.entries?.get(Text(key))
    val string: String? get() = (untagged as? Text)?.value
    val array: List<Cbor>? get() = (untagged as? Array)?.items

    companion object {
        private const val MAX_DEPTH = 32

        fun decode(data: ByteArray): Cbor? = try {
            Reader(data).value(0)
        } catch (e: Exception) {
            // Malformed input, bad UTF-8 or an impossible length: no credentials.
            null
        }
    }

    private class Malformed : Exception()

    private class Reader(val bytes: ByteArray) {
        var index = 0

        fun byte(): kotlin.Int {
            if (index >= bytes.size) throw Malformed()
            return bytes[index++].toInt() and 0xFF
        }

        fun take(count: Long): ByteArray {
            if (count < 0 || count > bytes.size - index) throw Malformed()
            val out = bytes.copyOfRange(index, index + count.toInt())
            index += count.toInt()
            return out
        }

        fun argument(info: kotlin.Int): Long = when (info) {
            in 0..23 -> info.toLong()
            24 -> byte().toLong()
            25 -> take(2).fold(0L) { acc, b -> acc shl 8 or (b.toLong() and 0xFF) }
            26 -> take(4).fold(0L) { acc, b -> acc shl 8 or (b.toLong() and 0xFF) }
            27 -> take(8).fold(0L) { acc, b -> acc shl 8 or (b.toLong() and 0xFF) }.also { if (it < 0) throw Malformed() }
            else -> throw Malformed()
        }

        fun value(depth: kotlin.Int): Cbor {
            if (depth >= MAX_DEPTH) throw Malformed()
            val initial = byte()
            val major = initial shr 5
            val info = initial and 0x1F
            if (info == 31) return indefinite(major, depth)
            return when (major) {
                0 -> Int(argument(info))
                1 -> Int(-1 - argument(info))
                2 -> Bytes(take(argument(info)))
                3 -> Text(take(argument(info)).decodeToString(throwOnInvalidSequence = true))
                4 -> {
                    val count = argument(info)
                    if (count > bytes.size - index) throw Malformed()
                    Array(List(count.toInt()) { value(depth + 1) })
                }
                5 -> {
                    val count = argument(info)
                    if (count > bytes.size - index) throw Malformed()
                    val map = LinkedHashMap<Cbor, Cbor>()
                    repeat(count.toInt()) {
                        val key = value(depth + 1)
                        map[key] = value(depth + 1)
                    }
                    Map(map)
                }
                6 -> Tagged(argument(info), value(depth + 1))
                else -> simple(info)
            }
        }

        fun simple(info: kotlin.Int): Cbor = when (info) {
            20 -> Bool(false)
            21 -> Bool(true)
            22, 23 -> Null
            25 -> Float(halfToDouble(argument(25).toInt()))
            26 -> Float(java.lang.Float.intBitsToFloat(argument(26).toInt()).toDouble())
            27 -> Float(java.lang.Double.longBitsToDouble(argument(27)))
            else -> throw Malformed()
        }

        /** Indefinite-length strings, arrays and maps, ended by 0xFF. */
        fun indefinite(major: kotlin.Int, depth: kotlin.Int): Cbor {
            val items = mutableListOf<Cbor>()
            while (true) {
                if (index >= bytes.size) throw Malformed()
                if (bytes[index] == 0xFF.toByte()) { index++; break }
                items += value(depth + 1)
            }
            return when (major) {
                2 -> Bytes(items.filterIsInstance<Bytes>().fold(ByteArray(0)) { acc, b -> acc + b.value })
                3 -> Text(items.mapNotNull { it.string }.joinToString(""))
                4 -> Array(items)
                5 -> {
                    if (items.size % 2 != 0) throw Malformed()
                    Map(items.chunked(2).associate { it[0] to it[1] })
                }
                else -> throw Malformed()
            }
        }

        private fun halfToDouble(bits: kotlin.Int): Double {
            val sign = if (bits and 0x8000 != 0) -1.0 else 1.0
            val exponent = (bits shr 10) and 0x1F
            val fraction = bits and 0x3FF
            return sign * when (exponent) {
                0 -> fraction / 1024.0 * Math.pow(2.0, -14.0)
                31 -> if (fraction == 0) Double.POSITIVE_INFINITY else Double.NaN
                else -> (1 + fraction / 1024.0) * Math.pow(2.0, (exponent - 15).toDouble())
            }
        }
    }
}

/**
 * A JUMBF box (ISO/IEC 19566-5), the container C2PA stores manifests in.
 * Superboxes ("jumb") carry a label from their description box ("jumd").
 */
class JumbfBox(val type: String, val label: String?, val payload: ByteArray, val children: List<JumbfBox>) {
    /** First descendant superbox (including self) with this label. */
    fun find(label: String): JumbfBox? {
        if (this.label == label) return this
        for (child in children) child.find(label)?.let { return it }
        return null
    }

    /** Superboxes whose label starts with `prefix`, searched recursively. */
    fun all(labelPrefix: String): List<JumbfBox> =
        (if (label?.startsWith(labelPrefix) == true) listOf(this) else emptyList()) + children.flatMap { it.all(labelPrefix) }

    /** The CBOR content box inside a superbox, decoded. */
    val cbor: Cbor? get() = children.firstOrNull { it.type == "cbor" }?.let { Cbor.decode(it.payload) }

    companion object {
        fun parse(data: ByteArray, depth: Int = 0): List<JumbfBox> {
            if (depth >= 16) return emptyList()
            val boxes = mutableListOf<JumbfBox>()
            var index = 0
            while (index + 8 <= data.size) {
                var length = readUInt(data, index, 4)
                val type = String(data, index + 4, 4, Charsets.ISO_8859_1)
                var header = 8
                if (length == 1L) {
                    if (index + 16 > data.size) break
                    length = readUInt(data, index + 8, 8)
                    header = 16
                } else if (length == 0L) {
                    length = (data.size - index).toLong()
                }
                if (length < header || length > data.size - index) break
                val payload = data.copyOfRange(index + header, index + length.toInt())
                val children = if (type == "jumb") parse(payload, depth + 1) else emptyList()
                val label = children.firstOrNull { it.type == "jumd" }?.let { description(it.payload) }
                boxes += JumbfBox(type, label, payload, children)
                index += length.toInt()
            }
            return boxes
        }

        /** The label in a description box: 16-byte type UUID, a toggles byte, then a NUL-terminated UTF-8 label when bit 0x02 is set. */
        private fun description(payload: ByteArray): String? {
            if (payload.size <= 17 || payload[16].toInt() and 0x02 == 0) return null
            val end = (17 until payload.size).firstOrNull { payload[it] == 0.toByte() } ?: payload.size
            return String(payload, 17, end - 17, Charsets.UTF_8)
        }

        internal fun readUInt(data: ByteArray, at: Int, count: Int): Long {
            var value = 0L
            for (i in 0 until count) value = value shl 8 or (data[at + i].toLong() and 0xFF)
            return if (value < 0) Long.MAX_VALUE else value
        }
    }
}

/**
 * Finds C2PA Content Credentials embedded in JPEG (APP11 segments) or PNG
 * ("caBX" chunk) files and summarizes the active manifest. Returns null when
 * there are none, which is the usual case: most sites, Bluesky included, strip
 * them on upload.
 */
object ContentCredentialsReader {
    /** Credentials stores are small; ignore anything implausibly large. */
    private const val MAX_STORE_SIZE = 8 shl 20

    fun read(data: ByteArray): ContentCredentials? = try {
        val store = manifestStore(data) ?: return null
        val root = JumbfBox.parse(store).firstNotNullOfOrNull { it.find("c2pa") } ?: return null
        // The active manifest is the last one in the store.
        val manifest = root.children.lastOrNull { it.type == "jumb" && it.label != null } ?: return null
        summarize(manifest)
    } catch (e: Exception) {
        null
    }

    fun manifestStore(data: ByteArray): ByteArray? {
        if (data.size >= 2 && data[0] == 0xFF.toByte() && data[1] == 0xD8.toByte()) return jpegStore(data)
        val png = byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
        if (data.size >= 8 && data.copyOfRange(0, 8).contentEquals(png)) return pngStore(data)
        return null
    }

    /**
     * APP11 segments: "JP", a 2-byte box instance, a 4-byte sequence number,
     * then box data. Continuations repeat the 8-byte box header, which is skipped.
     */
    private fun jpegStore(bytes: ByteArray): ByteArray? {
        val parts = LinkedHashMap<Int, java.io.ByteArrayOutputStream>()
        var index = 2
        fun u(i: Int) = bytes[i].toInt() and 0xFF
        while (index + 4 <= bytes.size && u(index) == 0xFF) {
            val marker = u(index + 1)
            if (marker == 0xDA || marker == 0xD9) break // image data / end
            if (marker in 0xD0..0xD7 || marker == 0x01) { index += 2; continue }
            val length = u(index + 2) shl 8 or u(index + 3)
            val start = index + 4
            val end = index + 2 + length
            if (length < 2 || end > bytes.size) break
            if (marker == 0xEB && end - start >= 8 && u(start) == 0x4A && u(start + 1) == 0x50) {
                val instance = u(start + 2) shl 8 or u(start + 3)
                val sequence = JumbfBox.readUInt(bytes, start + 4, 4)
                val part = parts.getOrPut(instance) { java.io.ByteArrayOutputStream() }
                if (sequence <= 1) {
                    part.reset()
                    part.write(bytes, start + 8, end - start - 8)
                } else if (end - start > 16) {
                    part.write(bytes, start + 16, end - start - 16)
                }
                if (part.size() > MAX_STORE_SIZE) return null
            }
            index = end
        }
        return parts.values.map { it.toByteArray() }.firstOrNull { data -> JumbfBox.parse(data).any { it.find("c2pa") != null } }
    }

    private fun pngStore(bytes: ByteArray): ByteArray? {
        var index = 8
        while (index + 12 <= bytes.size) {
            val length = JumbfBox.readUInt(bytes, index, 4)
            val type = String(bytes, index + 4, 4, Charsets.ISO_8859_1)
            val start = index + 8
            if (length > MAX_STORE_SIZE || start + length + 4 > bytes.size) return null
            if (type == "caBX") return bytes.copyOfRange(start, start + length.toInt())
            if (type == "IEND") return null
            index = start + length.toInt() + 4
        }
        return null
    }

    private fun summarize(manifest: JumbfBox): ContentCredentials {
        val claim = manifest.children.firstOrNull { it.label?.startsWith("c2pa.claim") == true }?.cbor
        val actionList = manifest.all("c2pa.actions").mapNotNull { it.cbor }.flatMap { it["actions"]?.array.orEmpty() }
        val sourceTypes = actionList.mapNotNull { it["digitalSourceType"]?.string }
        val names = actionList.mapNotNull { it["action"]?.string }.map(::actionName).distinct()
        val agent = actionList.firstNotNullOfOrNull { it["softwareAgent"]?.string ?: it["softwareAgent"]?.get("name")?.string }
        return ContentCredentials(generator = generatorName(claim) ?: agent, source = source(sourceTypes), actions = names)
    }

    private fun generatorName(claim: Cbor?): String? {
        claim ?: return null
        claim["claim_generator_info"]?.let { info ->
            val first = info.array?.firstOrNull() ?: info
            first["name"]?.string?.let { name -> return listOfNotNull(name, first["version"]?.string).joinToString(" ") }
        }
        // v1 claims: "Adobe_Firefly/1.0 c2pa-rs/0.25" → "Adobe Firefly"
        val raw = claim["claim_generator"]?.string ?: return null
        return raw.split(" ").firstOrNull()?.split("/")?.firstOrNull()?.replace('_', ' ')
    }

    /** IPTC digital source types, most telling first. */
    fun source(types: List<String>): ContentCredentials.Source {
        val names = types.map { it.substringAfterLast('/') }
        return when {
            names.any { it == "trainedAlgorithmicMedia" || it == "algorithmicMedia" } -> ContentCredentials.Source.AI_GENERATED
            "compositeWithTrainedAlgorithmicMedia" in names -> ContentCredentials.Source.AI_EDITED
            names.any { it == "digitalCapture" || it == "computationalCapture" } -> ContentCredentials.Source.CAMERA
            else -> ContentCredentials.Source.UNSPECIFIED
        }
    }

    fun actionName(action: String): String {
        val known = mapOf(
            "c2pa.created" to "Created", "c2pa.edited" to "Edited", "c2pa.opened" to "Opened",
            "c2pa.placed" to "Added content", "c2pa.cropped" to "Cropped", "c2pa.resized" to "Resized",
            "c2pa.color_adjustments" to "Color adjusted", "c2pa.filtered" to "Filtered",
            "c2pa.converted" to "Converted", "c2pa.drawing" to "Drawn on", "c2pa.removed" to "Removed content",
            "c2pa.published" to "Published", "c2pa.transcoded" to "Re-encoded", "c2pa.repackaged" to "Repackaged",
        )
        known[action]?.let { return it }
        val words = action.substringAfterLast('.').replace('_', ' ')
        return words.replaceFirstChar { it.uppercase() }
    }
}
