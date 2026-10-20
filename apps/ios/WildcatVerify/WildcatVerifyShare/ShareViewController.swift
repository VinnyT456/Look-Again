import SwiftUI
import UIKit

/// Principal class of the share extension. Hosts the SwiftUI share sheet and
/// hands it whatever the user shared.
final class ShareViewController: UIViewController {
    private let viewModel = ShareViewModel()
    private var loadTask: Task<Void, Never>?

    override func viewDidLoad() {
        super.viewDidLoad()

        let host = UIHostingController(rootView: ShareRootView(viewModel: viewModel, onDone: { [weak self] in
            self?.finish()
        }))
        addChild(host)
        host.view.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(host.view)
        NSLayoutConstraint.activate([
            host.view.topAnchor.constraint(equalTo: view.topAnchor),
            host.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            host.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            host.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])
        host.didMove(toParent: self)

        let items = extensionContext?.inputItems.compactMap { $0 as? NSExtensionItem } ?? []
        let providers = items.flatMap { $0.attachments ?? [] }
        loadTask = Task { await viewModel.load(providers: providers) }
    }

    private func finish() {
        loadTask?.cancel()
        // Nothing is stored or returned: the shared item lived only in memory.
        ImageRepository.shared.removeAllUploads()
        extensionContext?.completeRequest(returningItems: nil)
    }
}
