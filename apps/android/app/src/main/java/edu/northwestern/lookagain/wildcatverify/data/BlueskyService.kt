package edu.northwestern.lookagain.wildcatverify.data

import edu.northwestern.lookagain.wildcatverify.model.BlueskyPost
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import edu.northwestern.lookagain.wildcatverify.model.FeedPage
import edu.northwestern.lookagain.wildcatverify.model.FeedPost
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.net.URLEncoder
import java.time.Instant

/** A plain GET, returning the status and body. Swappable in tests. */
fun interface HttpClient {
    /** @throws IOException when the server can't be reached. */
    suspend fun get(url: String): Pair<Int, ByteArray>
}

/** Any HTTP request, for signed-in calls. Swappable in tests. */
fun interface HttpSender {
    suspend fun send(method: String, url: String, headers: Map<String, String>, body: ByteArray?): Pair<Int, ByteArray>
}

/** HTTPS with `HttpURLConnection`, off the main thread. */
object UrlConnectionHttpClient : HttpClient, HttpSender {
    override suspend fun get(url: String): Pair<Int, ByteArray> = send("GET", url, emptyMap(), null)

    override suspend fun send(method: String, url: String, headers: Map<String, String>, body: ByteArray?): Pair<Int, ByteArray> = withContext(Dispatchers.IO) {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 15_000
            connection.readTimeout = 30_000
            connection.requestMethod = method
            connection.setRequestProperty("Accept", "*/*")
            headers.forEach(connection::setRequestProperty)
            if (body != null) {
                connection.doOutput = true
                connection.outputStream.use { it.write(body) }
            }
            val status = connection.responseCode
            ensureActive()
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            status to (stream?.use { it.readBytes() } ?: ByteArray(0))
        } finally {
            connection.disconnect()
        }
    }
}

internal val lenientJson = Json { ignoreUnknownKeys = true; coerceInputValues = true }

private fun encode(value: String) = URLEncoder.encode(value, "UTF-8")

/** Reads public posts through the unauthenticated Bluesky AppView. */
class BlueskyService(private val http: HttpClient = UrlConnectionHttpClient) {

    suspend fun fetchPost(link: String): BlueskyPost {
        val (actor, rkey) = parse(link) ?: throw CheckException.InvalidLink
        val (status, body) = try {
            http.get(threadUrl(actor, rkey))
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            throw CheckException.Network
        }
        if (status != 200) throw CheckException.PostNotFound
        val thread = try {
            lenientJson.decodeFromString<ThreadResponse>(body.decodeToString())
        } catch (e: Exception) {
            throw CheckException.PostNotFound
        }
        val post = thread.thread.post ?: throw CheckException.PostNotFound
        val all = post.embed?.allImages.orEmpty()
        val image = all.firstOrNull() ?: throw CheckException.NoImage
        val handle = post.author.handle
        return BlueskyPost(
            authorHandle = handle,
            text = post.record.text ?: "",
            postUrl = "https://bsky.app/profile/$handle/post/$rkey",
            imageUrl = image,
            moreImageUrls = all.drop(1),
        )
    }

    companion object {
        /** Parses `https://bsky.app/profile/{handle-or-did}/post/{rkey}` into its parts. */
        fun parse(link: String): Pair<String, String>? {
            var trimmed = link.trim()
            if (!trimmed.lowercase().startsWith("http")) trimmed = "https://$trimmed"
            val uri = try { URI(trimmed) } catch (e: Exception) { return null }
            val host = uri.host?.lowercase() ?: return null
            if (host != "bsky.app" && !host.endsWith(".bsky.app")) return null
            val parts = (uri.path ?: "").split("/").filter { it.isNotEmpty() }
            if (parts.size < 4 || parts[0] != "profile" || parts[2] != "post") return null
            return parts[1] to parts[3]
        }

        fun threadUrl(actor: String, rkey: String): String =
            "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread" +
                "?uri=${encode("at://$actor/app.bsky.feed.post/$rkey")}&depth=0&parentHeight=0"

        /**
         * Finds the first Bluesky post link in shared text, such as "Look at this
         * https://bsky.app/profile/a/post/b". Returns null when there isn't one.
         */
        fun linkIn(text: String): String? =
            text.split(Regex("\\s+"))
                .map { it.trim('<', '>', '(', ')', '"', '\'', ',', '.') }
                .firstOrNull { parse(it) != null }
    }

    @Serializable
    private data class ThreadResponse(val thread: Thread) {
        @Serializable data class Thread(val post: Post? = null)
        @Serializable data class Post(val author: Author, val record: Record, val embed: Embed? = null)
        @Serializable data class Author(val handle: String)
        @Serializable data class Record(val text: String? = null)
        @Serializable data class ImageView(val fullsize: String)
        @Serializable data class Media(val images: List<ImageView>? = null)

        /** `images` for image posts; `media` for `app.bsky.embed.recordWithMedia#view`. */
        @Serializable
        data class Embed(val images: List<ImageView>? = null, val media: Media? = null) {
            val allImages: List<String> get() = (images ?: media?.images).orEmpty().map { it.fullsize }
        }
    }
}

/**
 * Reads Bluesky's public "What's Hot" feed through the unauthenticated
 * AppView and keeps only image posts that are safe to show.
 */
class BlueskyFeedService(
    private val http: HttpClient = UrlConnectionHttpClient,
    private val feedUri: String = WHATS_HOT,
) {
    suspend fun fetchPage(cursor: String?): FeedPage {
        var url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed?feed=${encode(feedUri)}&limit=$PAGE_SIZE"
        if (cursor != null) url += "&cursor=${encode(cursor)}"
        val (status, body) = try {
            http.get(url)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            throw CheckException.Network
        }
        if (status != 200) throw CheckException.Network
        return try {
            page(body)
        } catch (e: Exception) {
            throw CheckException.Network
        }
    }


    companion object {
        const val WHATS_HOT = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot"
        const val PAGE_SIZE = 30

        /** Turns a getFeed/getTimeline body into a page of safe image posts. */
        fun page(body: ByteArray): FeedPage {
            val decoded = lenientJson.decodeFromString<FeedResponse>(body.decodeToString())
            return FeedPage(decoded.feed.mapNotNull { post(it.post) }, decoded.cursor)
        }

        /** Bluesky timestamps include fractional seconds ("…15.455Z"). */
        fun parseDate(value: String): Long? = try {
            Instant.parse(value).toEpochMilli()
        } catch (e: Exception) {
            null
        }

        /**
         * Keeps posts with at least one image and no moderation or self labels on
         * the post or its author. Labels flag adult, graphic or otherwise
         * sensitive content, so anything labelled is left out entirely.
         */
        internal fun post(post: FeedResponse.Post): FeedPost? {
            if (!post.labels.isNullOrEmpty() || !post.author.labels.isNullOrEmpty()) return null
            val images = post.embed?.allImages.orEmpty()
            val first = images.firstOrNull() ?: return null
            val rkey = post.uri.split("/").lastOrNull()?.takeIf { it.isNotEmpty() } ?: return null
            val ratio = first.aspectRatio?.let { if (it.height > 0) it.width / it.height else null }
            return FeedPost(
                id = post.uri,
                authorHandle = post.author.handle,
                authorName = post.author.displayName?.takeIf { it.isNotEmpty() } ?: post.author.handle,
                avatarUrl = post.author.avatar,
                text = post.record.text ?: "",
                postUrl = "https://bsky.app/profile/${post.author.handle}/post/$rkey",
                thumbUrl = first.thumb,
                fullsizeUrl = first.fullsize ?: first.thumb,
                imageAlt = first.alt ?: "",
                aspectRatio = ratio,
                postedAt = post.indexedAt?.let(::parseDate),
                imageCount = images.size,
                imageUrls = images.map { it.fullsize ?: it.thumb },
            )
        }
    }

    /** The fields WildcatVerify reads from `app.bsky.feed.getFeed`. */
    @Serializable
    internal data class FeedResponse(val feed: List<Item> = emptyList(), val cursor: String? = null) {
        @Serializable data class Item(val post: Post)
        @Serializable data class Label(val `val`: String)
        @Serializable data class Author(
            val handle: String,
            val displayName: String? = null,
            val avatar: String? = null,
            val labels: List<Label>? = null,
        )
        @Serializable data class Record(val text: String? = null)
        @Serializable data class Ratio(val width: Double, val height: Double)
        @Serializable data class Image(val thumb: String, val fullsize: String? = null, val alt: String? = null, val aspectRatio: Ratio? = null)
        @Serializable data class Media(val images: List<Image>? = null)

        @Serializable
        data class Embed(val images: List<Image>? = null, val media: Media? = null) {
            val allImages: List<Image> get() = images ?: media?.images ?: emptyList()
        }

        @Serializable
        data class Post(
            val uri: String,
            val author: Author,
            val record: Record = Record(),
            val embed: Embed? = null,
            val labels: List<Label>? = null,
            val indexedAt: String? = null,
        )
    }
}
