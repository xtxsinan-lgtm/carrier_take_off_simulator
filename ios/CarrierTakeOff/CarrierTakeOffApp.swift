import SwiftUI

@main
struct CarrierTakeOffApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                HubView()
            }
            .preferredColorScheme(.dark)
        }
    }
}
