/// The "What to look for" guide, grouped by the kind of problem.
struct ClueGroup: Identifiable, Hashable, Sendable {
    var id: String { title }
    var title: String
    /// Label in the guide's group picker.
    var shortTitle: String
    /// One line on the Learn home describing the group.
    var summary: String
    var icon: String
    /// The verdict these clues help you reach; colours the group and picks
    /// which group to review after a round.
    var focus: VerdictType
    var clues: [Clue]

    /// The group to review after missing questions whose answer was `verdict`.
    static func group(for verdict: VerdictType, in groups: [ClueGroup] = guide) -> ClueGroup? {
        groups.first { $0.focus == verdict }
    }

    static let guide: [ClueGroup] = [
        ClueGroup(
            title: "Signs of AI",
            shortTitle: "AI",
            summary: "What generated images still get wrong",
            icon: VerdictType.ai.icon,
            focus: .ai,
            clues: [
                Clue(title: "Lighting", detail: "Highlights, shadows and reflections should all come from the same lights. Generators often light each part of a picture on its own.", icon: "sun.max"),
                Clue(title: "Things touching", detail: "Look where objects meet: fingers and cups, water and legs, hair and collars. Generated objects tend to blend into each other.", icon: "hand.point.up.left"),
                Clue(title: "The background", detail: "Faces, signs and buildings at the back get less attention from a generator. Look for faces without features and lettering that spells nothing.", icon: "person.3"),
                Clue(title: "Patterns", detail: "Windows, tiles, fences and keyboard keys should repeat evenly. Watch for rows that drift or merge.", icon: "square.grid.3x3"),
                Clue(title: "Pairs", detail: "Earrings, glasses arms and shoes often don't match left to right.", icon: "eyeglasses"),
                Clue(title: "Hands and teeth", detail: "Extra fingers and blurred teeth were common in older generators. Newer ones rarely make these mistakes, so good hands don't prove a photo is real.", icon: "hand.raised"),
            ]
        ),
        ClueGroup(
            title: "Signs of editing",
            shortTitle: "Editing",
            summary: "Where part of a real photo was changed",
            icon: VerdictType.tampered.icon,
            focus: .tampered,
            clues: [
                Clue(title: "Shadows", detail: "Everyone outdoors shares one sun. A shadow pointing the wrong way, or a person lit differently from the crowd, was probably added.", icon: "sun.min"),
                Clue(title: "Sharpness and grain", detail: "Things the same distance from the camera should be equally sharp and equally grainy. A crisp object in a soft scene stands out.", icon: "camera.aperture"),
                Clue(title: "Copies", detail: "The same person, cloud or brick showing up twice means part of the picture was copied to fill space.", icon: "square.on.square"),
                Clue(title: "Text on things", detail: "Printed words bend with the surface they're on. Text that stays flat across folds or curves was pasted on.", icon: "flag"),
                Clue(title: "Bent backgrounds", detail: "Door frames, tiles and walls that warp only next to a body mean the body was reshaped.", icon: "rectangle.portrait"),
                Clue(title: "Edges", detail: "A thin outline or halo around a person or skyline is often where something was cut in.", icon: "scribble.variable"),
            ]
        ),
        ClueGroup(
            title: "Check the source",
            shortTitle: "Source",
            summary: "Who posted it, and whether the story fits",
            icon: "person.crop.circle.badge.questionmark",
            focus: .real,
            clues: [
                Clue(title: "Labels", detail: "Bluesky shows labels from the moderation services you use, and some of them label AI-generated images. In Bluesky, tap a label to see who added it.", icon: "tag"),
                Clue(title: "The first post", detail: "Follow reposts and quote posts back to whoever posted it first, then look at what else that account shares.", icon: "arrow.uturn.backward.circle"),
                Clue(title: "Replies and quotes", detail: "People who were there, or who found the original, often say so in the replies.", icon: "bubble.left.and.bubble.right"),
                Clue(title: "Date and place", detail: "A real photo from another year or another city is still misleading. Watermarks and credits often give it away.", icon: "calendar"),
                Clue(title: "Other angles", detail: "Big events get photographed by many people. If only one picture exists, wait before sharing it.", icon: "camera"),
                Clue(title: "Alt text and credentials", detail: "Some posters describe how a picture was made in its alt text, and some files carry Content Credentials. WildcatVerify shows them when it finds them.", icon: "text.below.photo"),
            ]
        ),
    ]
}
