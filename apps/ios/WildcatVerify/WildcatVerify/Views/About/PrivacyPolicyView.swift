import SwiftUI

/// The full privacy policy, bundled so it is readable offline. Keep in sync
/// with PRIVACY.md at the project root.
struct PrivacyPolicyView: View {
    var body: some View {
        List {
            Section {
                Text("WildcatVerify is built so your photos and checks stay on your iPhone. Last updated October 15, 2026.")
            }

            Section("Photos you choose") {
                Text("iOS gives the app only the photo you pick, never the rest of your library. It is analyzed in memory on this iPhone, never uploaded or written to disk, and is discarded when you delete the check, clear My Checks, or quit the app. Location and other personal metadata aren't read. If the photo carries Content Credentials, only the app or device that made it and its edit history are read and shown with the result.")
            }

            Section("Items you share") {
                Text("When you use Share → WildcatVerify in another app, only what you shared reaches the app. It is checked in memory the same way and discarded when you tap Done.")
            }

            Section("Siri and Shortcuts") {
                Text("The Check Image action receives the screenshot your shortcut takes, in memory. The app never reads your photo library. Only the area you box is checked, on this iPhone, and the screenshot is discarded when you're done.")
                Text("Visual Intelligence hands over the image you search with, in memory, only when you choose Check with WildcatVerify.")
                Text("“Check the copied link” reads your clipboard only when you ask, and iOS asks your permission first. Only a Bluesky post link is used; anything else on the clipboard is ignored.")
            }

            Section {
                Text("To check a post, the app asks Bluesky's public API for that post's text and photo. The request goes straight from your iPhone to Bluesky, which sees your IP address like any website would. WildcatVerify runs no server and keeps no copy of the link.")
                if let url = AppLinks.blueskyPrivacy {
                    Link("Bluesky Privacy Policy", destination: url)
                }
            } header: {
                Text("Bluesky links you paste")
            }

            Section("My Checks") {
                Text("By default, past checks are kept in memory and disappear when you close the app. If you turn on Settings → Keep My Checks, results and small copies of the photos you checked are saved on this iPhone only: encrypted while locked, left out of backups, never uploaded, and deleted when you turn the setting off or erase your data.")
            }

            Section("The Feed") {
                Text("The Feed loads public image posts from Bluesky's What's Hot feed directly from Bluesky. No account is used. With Check Posts Automatically on, each post's image is analyzed on this iPhone as it appears; those verdicts stay in memory and aren't added to My Checks unless you open the post.")
                Text("When you open the app, it asks iOS only whether the clipboard looks like a link, without reading it and without a paste prompt. The link is read only when you tap Paste.")
            }

            Section("Hidden accounts and settings") {
                Text("Accounts you hide from the Feed, your preferences and your best Look Again score are saved on this iPhone only. Bluesky and hidden accounts aren't told. Erase All Data removes them.")
            }

            Section("Where processing happens") {
                Text("All image analysis, including the AI-image detector, runs on this iPhone with Core ML. Nothing is sent to the developer or to any AI service. If you use Siri, Apple handles your voice request under its own privacy policy.")
            }

            Section("Your choices") {
                Text("Delete one check with a swipe, clear My Checks, or use Settings → Erase All Data. Deleting the app removes everything. The developer holds no personal data, but you can still contact us with any privacy request.")
            }

            Section("What the app doesn't do") {
                Label("No account or sign-in", systemImage: "person.crop.circle.badge.xmark")
                Label("No analytics, ads or tracking", systemImage: "eye.slash")
                Label("No data sold, shared or collected", systemImage: "hand.raised")
            }

            Section {
                if let url = AppLinks.privacyPolicy {
                    Link("View Policy Online", destination: url)
                }
                if let url = AppLinks.support {
                    Link("Contact Support", destination: url)
                }
            }
        }
        .navigationTitle("Privacy Policy")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        PrivacyPolicyView()
    }
}
