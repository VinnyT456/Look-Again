import Foundation
import Network
import Observation

/// Conditions under which automatic Feed checks should wait: Low Data Mode
/// and Low Power Mode. Cellular alone doesn't pause them: the Feed has
/// already downloaded each thumbnail to show it, so checking it uses barely any extra data.
@MainActor
@Observable
final class NetworkConditions {
    private(set) var isLowDataMode = false
    private(set) var isLowPowerMode = ProcessInfo.processInfo.isLowPowerModeEnabled
    /// Called after either changes.
    @ObservationIgnored var onChange: (@MainActor () -> Void)?
    private let monitor = NWPathMonitor()

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let constrained = path.isConstrained
            Task { @MainActor in
                guard let self, self.isLowDataMode != constrained else { return }
                self.isLowDataMode = constrained
                self.onChange?()
            }
        }
        monitor.start(queue: .main)

        Task { [weak self] in
            for await _ in NotificationCenter.default.notifications(named: .NSProcessInfoPowerStateDidChange) {
                guard let self else { break }
                self.isLowPowerMode = ProcessInfo.processInfo.isLowPowerModeEnabled
                self.onChange?()
            }
        }
    }

    deinit {
        monitor.cancel()
    }
}
