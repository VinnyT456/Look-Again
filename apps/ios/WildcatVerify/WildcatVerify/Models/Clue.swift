/// One thing to look for, in the "What to look for" guide.
struct Clue: Identifiable, Hashable, Sendable {
    var id: String { title }
    var title: String
    var detail: String
    var icon: String
}
