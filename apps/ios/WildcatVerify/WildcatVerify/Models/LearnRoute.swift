/// Screens pushed inside the Learn tab.
enum LearnRoute: Hashable {
    /// The clue guide, opened on one group (`ClueGroup.id`).
    case clueGuide(String)
}
