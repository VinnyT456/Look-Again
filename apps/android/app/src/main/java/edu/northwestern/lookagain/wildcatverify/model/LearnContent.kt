package edu.northwestern.lookagain.wildcatverify.model

/** Icons are named, then mapped to Material icons in `ui/theme/Theme.kt`. */
enum class ClueIcon {
    SUN, TOUCH, PEOPLE, GRID, GLASSES, HAND, SHADOW, APERTURE, COPY, FLAG, FRAME, SCRIBBLE,
    TAG, FIRST_POST, REPLIES, CALENDAR, CAMERA, ALT_TEXT, AI, EDITED, SOURCE,
}

/** One thing to look for, in the Clue Guide. */
data class Clue(val title: String, val detail: String, val icon: ClueIcon)

/** The Clue Guide, grouped by the kind of problem. */
data class ClueGroup(
    val title: String,
    /** Label in the guide's group switcher. */
    val shortTitle: String,
    /** One line on the Learn home describing the group. */
    val summary: String,
    val icon: ClueIcon,
    /** The verdict these clues help you reach; picks which group to review after a round. */
    val focus: VerdictType,
    val clues: List<Clue>,
) {
    val id: String get() = title

    companion object {
        /** The group to review after missing questions whose answer was `verdict`. */
        fun groupFor(verdict: VerdictType, groups: List<ClueGroup> = guide): ClueGroup? = groups.firstOrNull { it.focus == verdict }

        val guide = listOf(
            ClueGroup(
                title = "Signs of AI",
                shortTitle = "AI",
                summary = "What generated images still get wrong",
                icon = ClueIcon.AI,
                focus = VerdictType.AI,
                clues = listOf(
                    Clue("Lighting", "Highlights, shadows and reflections should all come from the same lights. Generators often light each part of a picture on its own.", ClueIcon.SUN),
                    Clue("Things touching", "Look where objects meet: fingers and cups, water and legs, hair and collars. Generated objects tend to blend into each other.", ClueIcon.TOUCH),
                    Clue("The background", "Faces, signs and buildings at the back get less attention from a generator. Look for faces without features and lettering that spells nothing.", ClueIcon.PEOPLE),
                    Clue("Patterns", "Windows, tiles, fences and keyboard keys should repeat evenly. Watch for rows that drift or merge.", ClueIcon.GRID),
                    Clue("Pairs", "Earrings, glasses arms and shoes often don't match left to right.", ClueIcon.GLASSES),
                    Clue("Hands and teeth", "Extra fingers and blurred teeth were common in older generators. Newer ones rarely make these mistakes, so good hands don't prove a photo is real.", ClueIcon.HAND),
                ),
            ),
            ClueGroup(
                title = "Signs of editing",
                shortTitle = "Editing",
                summary = "Where part of a real photo was changed",
                icon = ClueIcon.EDITED,
                focus = VerdictType.TAMPERED,
                clues = listOf(
                    Clue("Shadows", "Everyone outdoors shares one sun. A shadow pointing the wrong way, or a person lit differently from the crowd, was probably added.", ClueIcon.SHADOW),
                    Clue("Sharpness and grain", "Things the same distance from the camera should be equally sharp and equally grainy. A crisp object in a soft scene stands out.", ClueIcon.APERTURE),
                    Clue("Copies", "The same person, cloud or brick showing up twice means part of the picture was copied to fill space.", ClueIcon.COPY),
                    Clue("Text on things", "Printed words bend with the surface they're on. Text that stays flat across folds or curves was pasted on.", ClueIcon.FLAG),
                    Clue("Bent backgrounds", "Door frames, tiles and walls that warp only next to a body mean the body was reshaped.", ClueIcon.FRAME),
                    Clue("Edges", "A thin outline or halo around a person or skyline is often where something was cut in.", ClueIcon.SCRIBBLE),
                ),
            ),
            ClueGroup(
                title = "Check the source",
                shortTitle = "Source",
                summary = "Who posted it, and whether the story fits",
                icon = ClueIcon.SOURCE,
                focus = VerdictType.REAL,
                clues = listOf(
                    Clue("Labels", "Bluesky shows labels from the moderation services you use, and some of them label AI-generated images. In Bluesky, tap a label to see who added it.", ClueIcon.TAG),
                    Clue("The first post", "Follow reposts and quote posts back to whoever posted it first, then look at what else that account shares.", ClueIcon.FIRST_POST),
                    Clue("Replies and quotes", "People who were there, or who found the original, often say so in the replies.", ClueIcon.REPLIES),
                    Clue("Date and place", "A real photo from another year or another city is still misleading. Watermarks and credits often give it away.", ClueIcon.CALENDAR),
                    Clue("Other angles", "Big events get photographed by many people. If only one picture exists, wait before sharing it.", ClueIcon.CAMERA),
                    Clue("Alt text and credentials", "Some posters describe how a picture was made in its alt text, and some files carry Content Credentials. WildcatVerify shows them when it finds them.", ClueIcon.ALT_TEXT),
                ),
            ),
        )
    }
}

/**
 * The four answers in Look Again. Practice-only: the detector still has
 * three verdicts, but the most common misleading Bluesky post is a real photo
 * with a false story, and players should learn to name it.
 */
enum class PracticeAnswer(
    /** Button label. */
    val label: String,
    /** Reads after "It's …": "It's a real photo." */
    val phrase: String,
    /** One-line definition, shown before the first answer. */
    val definition: String,
    /** For "You caught every …". */
    val singularNoun: String,
    /** For "Most misses were …". */
    val pluralNoun: String,
) {
    REAL("Real", "a real photo", "The photo is what the post says it is.", "real photo", "real photos"),
    EDITED("Edited", "an edited photo", "A real photo with part of it changed.", "edited photo", "edited photos"),
    AI("AI", "made by AI", "The whole image was generated.", "AI image", "AI images"),
    MISLEADING("False story", "a real photo with a false story", "A real, unedited photo with the wrong date, place or story.", "false story", "false stories");

    /** Mid-sentence form: "You said AI", "You said edited". */
    val inSentence: String get() = if (this == AI) label else label.lowercase()

    /** Which clue group helps with this answer. */
    val guideFocus: VerdictType
        get() = when (this) {
            REAL, MISLEADING -> VerdictType.REAL
            EDITED -> VerdictType.TAMPERED
            AI -> VerdictType.AI
        }
}

/**
 * A region of a practice photo to point at after answering, in 0–1 image
 * coordinates. Decoys mark details that look suspicious but are normal.
 */
data class PracticeHotspot(
    val x: Double,
    val y: Double,
    val width: Double,
    val height: Double,
    /** Short label drawn on the photo, usually one of the case's clues. */
    val label: String,
    /** True for "this is normal" details (lens flare, grain), drawn neutrally. */
    val isDecoy: Boolean = false,
) {
    val isInsideImage: Boolean get() = x >= 0 && y >= 0 && width > 0 && height > 0 && x + width <= 1 && y + height <= 1
}

/**
 * One Look Again case, shaped like a Bluesky post: who posted it, what they
 * wrote, and a plain description of the photo (or a bundled image).
 * Descriptions state what's visible without saying which detail matters; the
 * explanation and clues are only shown after answering.
 */
data class PracticeQuestion(
    val id: String,
    val author: String,
    /** Practice handles use the reserved `.example` domain so no real account is ever labelled fake. */
    val handle: String,
    /** Relative time as Bluesky shows it, e.g. "2h". */
    val posted: String,
    val caption: String,
    /** What the photo shows, for text-only play. */
    val imageDescription: String,
    /** Optional bundled image (drawable resource) shown instead of the description. */
    val imageRes: Int? = null,
    /** Neutral description for TalkBack once there's a photo. Falls back to `imageDescription`. */
    val altText: String? = null,
    /** Facts a photo can't show (replies, other coverage), drawn under the post like a reply. */
    val context: String? = null,
    /** Who took or made the photo and its license, e.g. "Photo: Jane Doe · CC BY 4.0". */
    val credit: String? = null,
    /** Regions to mark on the photo after answering. */
    val hotspots: List<PracticeHotspot> = emptyList(),
    val answer: PracticeAnswer,
    /** Why that answer is right, shown after the user picks. */
    val explanation: String,
    /** The specific clues, shown under the result. */
    val clues: List<String>,
) {
    /** What TalkBack reads for the photo. */
    val spokenImageDescription: String get() = if (imageRes == null) imageDescription else altText ?: imageDescription
}

/** Example cases shown in the Learn tab, one per verdict. They carry no photos and are always marked as demos. */
object SampleData {
    val lakefill = VerificationCase(
        id = "sample-lakefill",
        title = "Lakefill Storm Clouds",
        authorHandle = "dailynorthwestern.bsky.social",
        postUrl = "https://bsky.app/profile/dailynorthwestern.bsky.social",
        caption = "Graduates celebrate on the Lakefill as storm clouds roll over the Evanston shoreline.",
        timeAgo = "5h ago",
        verdict = VerdictType.REAL,
        confidencePercentage = 96,
        plainSummary = "Natural sunlight, consistent shadows, and clean lens focus throughout. No signs of digital editing or synthesis.",
        suggestedAction = "Fine to share. Still check that the caption matches the event.",
        keyFindings = listOf(
            "Consistent natural lighting and shadows across subjects",
            "Realistic depth of field between foreground and background",
            "Standard camera noise texture with no spliced seams",
        ),
        isDemo = true,
    )

    val protestBanner = VerificationCase(
        id = "sample-protest-banner",
        title = "Altered Student Council Sign",
        authorHandle = "wildcat_watch.bsky.social",
        postUrl = "https://bsky.app/profile/wildcat_watch.bsky.social",
        caption = "Edited banner text circulating in student group chats ahead of the council vote.",
        timeAgo = "3h ago",
        verdict = VerdictType.TAMPERED,
        confidencePercentage = 89,
        plainSummary = "Text on the center banner shows sharp edge seams and uneven compression compared to the surrounding fabric folds.",
        suggestedAction = "Look for the original photo before sharing it.",
        detectedIssue = "Replaced banner text",
        hotspot = HotspotArea(0.30, 0.34, 0.40, 0.26, "Edited text"),
        keyFindings = listOf(
            "Letters look pasted over the natural cloth folds",
            "Blurry seam where the original text was covered up",
            "Mismatched pixel resolution along the banner's edge",
        ),
        isDemo = true,
    )

    val monorail = VerificationCase(
        id = "sample-monorail",
        title = "Lake Michigan Monorail Concept",
        authorHandle = "chicago_future.bsky.social",
        postUrl = "https://bsky.app/profile/chicago_future.bsky.social",
        caption = "Viral post claiming the city approved an elevated monorail along Lake Shore Drive.",
        timeAgo = "1h ago",
        verdict = VerdictType.AI,
        confidencePercentage = 98,
        plainSummary = "Structural inconsistencies typical of generative AI: tracks float without support piers, and water reflections don't match the buildings.",
        suggestedAction = "Don't share it as real. Reply with a note that it appears to be AI-generated.",
        detectedIssue = "Generated structures",
        hotspot = HotspotArea(0.18, 0.45, 0.55, 0.40, "Floating track"),
        keyFindings = listOf(
            "Elevated rails float over open water without support columns",
            "Water reflections blur into melted patterns",
            "Background buildings have warped, painted textures",
        ),
        isDemo = true,
    )

    /** One example per verdict, in the order the Learn tab explains them. */
    val examples = listOf(monorail, protestBanner, lakefill)
}

/** External links the app shows. Each is a fixed, known-good literal. */
object AppLinks {
    const val PRIVACY_POLICY = "https://github.com/VinnyT456/Look-Again/blob/main/apps/android/PRIVACY.md"
    const val TERMS = "https://github.com/VinnyT456/Look-Again/blob/main/apps/android/TERMS.md"
    const val BLUESKY_PRIVACY = "https://bsky.social/about/support/privacy-policy"
    const val SUPPORT = "https://github.com/VinnyT456/Look-Again/issues"
    const val DETECTOR_MODEL = "https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT"
    const val DETECTOR_PAPER = "https://arxiv.org/abs/2411.04125"
    const val DETECTOR_CODE = "https://github.com/JeongsooP/Community-Forensics"
}
