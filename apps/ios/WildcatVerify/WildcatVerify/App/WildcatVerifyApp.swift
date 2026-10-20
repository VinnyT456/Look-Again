import SwiftUI

@main
struct WildcatVerifyApp: App {
    @State private var app = AppViewModel.live

    var body: some Scene {
        WindowGroup {
            RootView(app: app)
                .onOpenURL { app.handle($0) }
        }
    }
}
