import SwiftUI

/// Settings → Hidden Accounts: Bluesky accounts hidden from the Feed.
struct HiddenAccountsView: View {
    @Bindable var settings: SettingsStore

    private var accounts: [(did: String, handle: String)] {
        settings.hiddenAccounts.map { ($0.key, $0.value) }.sorted { $0.handle < $1.handle }
    }

    var body: some View {
        List {
            if accounts.isEmpty {
                ContentUnavailableView(
                    "No Hidden Accounts",
                    systemImage: "person.crop.circle.badge.checkmark",
                    description: Text("Use ••• on a Feed post to hide an account.")
                )
                .listRowBackground(Color.clear)
            } else {
                Section {
                    ForEach(accounts, id: \.did) { account in
                        HStack {
                            Text("@\(account.handle)")
                                .lineLimit(1)
                                .truncationMode(.middle)
                            Spacer()
                            Button("Show") { unhide(account.did) }
                                .buttonStyle(.bordered)
                                .accessibilityLabel("Show posts from @\(account.handle)")
                        }
                    }
                    .onDelete { offsets in
                        offsets.map { accounts[$0].did }.forEach(unhide)
                    }
                } footer: {
                    Text("Hidden on this iPhone only. Bluesky and the account aren't told.")
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Hidden Accounts")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func unhide(_ did: String) {
        settings.hiddenAccounts[did] = nil
    }
}
