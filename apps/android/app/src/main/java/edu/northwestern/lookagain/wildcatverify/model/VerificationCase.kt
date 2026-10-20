package edu.northwestern.lookagain.wildcatverify.model

import kotlinx.serialization.Serializable
import java.util.UUID

/** A normalized rectangle (0–1 in image space) marking the region that drove a verdict. */
@Serializable
data class HotspotArea(
    val xRatio: Double,
    val yRatio: Double,
    val widthRatio: Double,
    val heightRatio: Double,
    val label: String,
)

/**
 * What a photo's Content Credentials (C2PA) say about where it came from.
 * Read from the file; the signature isn't verified, so it's a clue, not proof.
 */
@Serializable
data class ContentCredentials(
    /** The app or device that wrote the credentials, e.g. "Adobe Firefly". */
    val generator: String?,
    val source: Source,
    /** Human-readable edit history, e.g. ["Created", "Cropped"]. */
    val actions: List<String>,
) {
    @Serializable
    enum class Source {
        /** Made entirely by generative AI. */
        AI_GENERATED,
        /** A real or edited image with AI-generated parts. */
        AI_EDITED,
        /** Captured by a camera. */
        CAMERA,
        /** Credentials present but don't say. */
        UNSPECIFIED,
    }
}

/** Output of the authenticity model. */
data class ClassificationResult(
    val verdict: VerdictType,
    /** 0–1. */
    val confidence: Double,
    val hotspot: HotspotArea? = null,
    /** Per-patch map from the detector, when the model provides one. */
    val heatmap: PatchHeatmap? = null,
)

/** One checked image: where it came from, what the classifier said, and why. */
@Serializable
data class VerificationCase(
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val authorHandle: String,
    val postUrl: String? = null,
    val caption: String,
    val timeAgo: String,
    /** Null when there is no photo to show (e.g. the bundled examples). */
    val imageUrl: String? = null,
    val verdict: VerdictType,
    val confidencePercentage: Int,
    val plainSummary: String,
    val suggestedAction: String,
    val detectedIssue: String? = null,
    val hotspot: HotspotArea? = null,
    /** Where the detector found what pushed it toward "AI" (detector results only). */
    val heatmap: PatchHeatmap? = null,
    val keyFindings: List<String>,
    /**
     * True when the verdict did not come from the trained model (bundled
     * examples, or the placeholder classifier). Always shown to the user.
     */
    val isDemo: Boolean = false,
    /**
     * Every image in a multi-image post, in post order, each with its own
     * verdict. Null for single images. The case itself is the most suspicious one.
     */
    val postImages: List<VerificationCase>? = null,
    /** Content Credentials (C2PA) found in the original file, if any. */
    val credentials: ContentCredentials? = null,
) {
    /** Uploaded photos have no author. */
    val displayHandle: String
        get() = when {
            authorHandle.isNotEmpty() -> "@$authorHandle"
            title == AUTO_LABEL_TITLE -> "Labeled while browsing Bluesky"
            else -> "From your photos"
        }

    /** Plain-text summary used by the share sheet. */
    val shareText: String
        get() = buildList {
            add("WildcatVerify${if (isDemo) " (demo result)" else ""}: ${verdict.label}, $confidencePercentage% confidence")
            add(title)
            if (authorHandle.isNotEmpty()) add("Posted by @$authorHandle")
            add(plainSummary)
            postUrl?.let(::add)
            add("An automated estimate, not proof.")
        }.joinToString("\n")

    companion object {
        /** Title of photos Auto-Label checked while the user browsed Bluesky. */
        const val AUTO_LABEL_TITLE = "Photo in Bluesky"
    }
}

/** Uploaded photos live only in memory and are addressed with this scheme. */
object InMemoryImage {
    fun url(id: String): String = "memory://upload/$id"
    fun isInMemory(url: String): Boolean = url.startsWith("memory://")
}
