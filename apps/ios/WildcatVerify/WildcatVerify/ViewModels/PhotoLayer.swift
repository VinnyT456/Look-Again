/// What the results photo shows: the plain image, or the image with the
/// region that drove the verdict highlighted.
enum PhotoLayer: String, CaseIterable, Identifiable {
    case photo
    case highlight

    var id: Self { self }

    var title: String {
        switch self {
        case .photo: "Photo"
        case .highlight: "Highlight"
        }
    }
}
