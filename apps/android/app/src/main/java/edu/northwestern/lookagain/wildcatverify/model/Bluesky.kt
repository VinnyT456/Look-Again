package edu.northwestern.lookagain.wildcatverify.model

/** A Bluesky post reduced to what the checker needs. */
data class BlueskyPost(
    val authorHandle: String,
    val text: String,
    val postUrl: String,
    val imageUrl: String,
    /** The post's other images, in order (Bluesky allows up to four). */
    val moreImageUrls: List<String> = emptyList(),
) {
    val imageUrls: List<String> get() = listOf(imageUrl) + moreImageUrls
}

/** An image post from Bluesky's public "What's Hot" feed. */
data class FeedPost(
    /** The post's AT URI. */
    val id: String,
    val authorHandle: String,
    val authorName: String,
    val avatarUrl: String?,
    val text: String,
    val postUrl: String,
    val thumbUrl: String,
    /** The full-resolution image, which is what gets checked. */
    val fullsizeUrl: String,
    val imageAlt: String,
    /** Width ÷ height of the first image, when Bluesky provides it. */
    val aspectRatio: Double?,
    /** Epoch milliseconds. */
    val postedAt: Long?,
    /** How many images the post has; every one is checked. */
    val imageCount: Int,
    /** Full-resolution URLs of every image, in post order. */
    val imageUrls: List<String> = listOf(fullsizeUrl),
) {
    /** The author's DID, from the post's AT URI. Stable even when the author changes their handle. */
    val authorDid: String
        get() = id.removePrefix("at://").split("/").firstOrNull()?.takeIf { it.isNotEmpty() } ?: authorHandle
}

/** One page of feed posts and the cursor for the next page (null at the end). */
data class FeedPage(val posts: List<FeedPost>, val cursor: String?)

/** Errors with copy the user can act on. */
sealed class CheckException(message: String) : Exception(message) {
    data object InvalidLink : CheckException("That doesn't look like a Bluesky post link. It should look like bsky.app/profile/…/post/…")
    data object PostNotFound : CheckException("We couldn't find that post. It may be deleted or private.")
    data object NoImage : CheckException("That post doesn't have a photo to check.")
    data object Network : CheckException("Couldn't reach Bluesky. Check your connection and try again.")
    data object UnreadablePhoto : CheckException("We couldn't open that photo. Try a different image or screenshot.")
    data object Unsupported : CheckException("WildcatVerify can check photos, screenshots and Bluesky post links. Try sharing the image itself or the post's link.")
}

/** User-facing copy for any failure. */
fun Throwable.userMessage(fallback: String = "Something went wrong checking that image. Please try again."): String =
    (this as? CheckException)?.message ?: fallback
