import Network
import Observation

/// Whether the connection is cellular/hotspot (expensive) or in Low Data Mode
/// (constrained), so automatic Feed checks can pause.
@MainActor
@Observable
final class NetworkConditions {
    private(set) var isLimited = false
    private let monitor = NWPathMonitor()

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let limited = path.isExpensive || path.isConstrained
            Task { @MainActor in self?.isLimited = limited }
        }
        monitor.start(queue: .main)
    }

    deinit {
        monitor.cancel()
    }
}
