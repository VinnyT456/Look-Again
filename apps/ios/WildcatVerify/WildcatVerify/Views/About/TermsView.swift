import SwiftUI

/// Terms of Use, bundled so they're readable offline. Keep in sync with
/// TERMS.md at the project root.
struct TermsView: View {
    var body: some View {
        List {
            Section {
                Text("These terms cover your use of WildcatVerify. Last updated October 15, 2026. Apple's standard Licensed Application End User License Agreement also applies.")
            }

            Section("What WildcatVerify does") {
                Text("It estimates whether a photo looks real, edited or AI-generated, using a detection model that runs on your iPhone. It's a tool to help you decide what to trust, not a final answer.")
            }

            Section("Verdicts are estimates") {
                Text("No detector is always right. A verdict can be wrong in either direction, and the confidence number is the model's own score, not a guarantee. Don't rely on a verdict alone for anything important, such as news, legal, academic or safety decisions.")
            }

            Section("Use it fairly") {
                Text("Don't use a verdict to harass, shame or publicly accuse someone of faking a photo. If something matters, look for other evidence: the original poster, other photos of the same moment, and trusted reporting. Don't use the app to break the law or anyone's rights.")
            }

            Section("Other people's content") {
                Text("Posts and photos in the Feed and from links belong to their authors and are shown from Bluesky's public service. WildcatVerify doesn't own, endorse or check them in advance. You can hide posts and accounts or report them with ••• on any Feed post. WildcatVerify isn't affiliated with Bluesky.")
            }

            Section("Your photos") {
                Text("Photos you check stay yours. They're processed on this iPhone and aren't uploaded. See the Privacy Policy for exactly what is kept and for how long.")
            }

            Section("Open source credits") {
                Text("The detection model is based on Community Forensics (MIT License). Full notices are under Settings → Credits.")
            }

            Section("No warranty") {
                Text("The app is provided “as is”, without warranties of any kind, to the extent the law allows. The developers aren't liable for decisions made based on a verdict.")
            }

            Section("Changes") {
                Text("If these terms change, the new version will be in the app and online before it applies.")
            }

            Section {
                if let url = AppLinks.terms {
                    Link("View Terms Online", destination: url)
                }
                if let url = AppLinks.support {
                    Link("Contact Support", destination: url)
                }
            }
        }
        .navigationTitle("Terms of Use")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        TermsView()
    }
}
