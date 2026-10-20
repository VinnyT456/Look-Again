import Foundation

enum CheckError: LocalizedError {
    case unreadablePhoto

    var errorDescription: String? {
        "We couldn't open that photo. Try a different image or screenshot."
    }
}
