import SwiftUI

/// A checked image in a list: thumbnail, title, source and verdict.
struct CaseRow: View {
    let item: VerificationCase

    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    private var details: String {
        item.isDemo ? "\(item.timeAgo) · Demo" : item.timeAgo
    }

    var body: some View {
        let layout = dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: 8))
            : AnyLayout(HStackLayout(spacing: 12))

        layout {
            CaseThumbnail(item: item)
            VStack(alignment: .leading, spacing: 4) {
                Text(item.title)
                    .font(.headline)
                    .lineLimit(dynamicTypeSize.isAccessibilitySize ? nil : 2)
                // Handles are identifiers: keep them on one line so wrapping
                // never inserts a hyphen that isn't part of the handle.
                Text(item.displayHandle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                HStack(spacing: 8) {
                    VerdictBadge(verdict: item.verdict)
                    Text(details)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    List {
        CaseRow(item: SampleData.monorail)
        CaseRow(item: SampleData.lakefill)
    }
}
