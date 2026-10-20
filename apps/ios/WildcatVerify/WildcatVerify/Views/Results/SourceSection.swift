import SwiftUI

/// Where the image came from.
struct SourceSection: View {
    let item: VerificationCase

    var body: some View {
        Section("Source") {
            if item.authorHandle.isEmpty {
                #if SHARE_EXTENSION
                LabeledContent("From", value: "Shared image")
                #else
                LabeledContent("From", value: "Your photo library")
                #endif
            } else {
                LabeledContent("Posted by", value: "@\(item.authorHandle)")
            }
            LabeledContent("Checked", value: item.timeAgo)
            if item.imageURL == nil {
                LabeledContent("Photo", value: "Not included")
            }
            // Share extensions can't open other apps or Safari.
            #if !SHARE_EXTENSION
            if let postURL = item.postURL {
                Link(destination: postURL) {
                    Label("Open on Bluesky", systemImage: "arrow.up.right.square")
                }
            }
            #endif
        }
    }
}
