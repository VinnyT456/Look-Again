import SwiftUI

/// What to look for, one group at a time: signs of AI, signs of editing, and
/// checking the source.
struct ClueGuideView: View {
    let groups: [ClueGroup]
    @State private var selection: String
    @ScaledMetric(relativeTo: .title3) private var iconWidth = 30.0

    init(groups: [ClueGroup], initial: String) {
        self.groups = groups
        _selection = State(initialValue: initial)
    }

    private var group: ClueGroup? {
        groups.first { $0.id == selection } ?? groups.first
    }

    var body: some View {
        List {
            Section {
                Picker("Clues", selection: $selection) {
                    ForEach(groups) { group in
                        Text(group.shortTitle).tag(group.id)
                    }
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())
            }

            if let group {
                Section {
                    ForEach(group.clues) { clue in
                        HStack(alignment: .firstTextBaseline, spacing: 14) {
                            Image(systemName: clue.icon)
                                .font(.title3)
                                .foregroundStyle(.tint)
                                .frame(width: iconWidth)
                                .accessibilityHidden(true)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(clue.title)
                                    .font(.headline)
                                Text(clue.detail)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 6)
                        .accessibilityElement(children: .combine)
                    }
                } header: {
                    Text(group.title)
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Clue Guide")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        ClueGuideView(groups: ClueGroup.guide, initial: ClueGroup.guide[0].id)
    }
}
