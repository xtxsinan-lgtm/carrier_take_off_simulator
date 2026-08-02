import SwiftUI

@main
struct CarrierTakeOffApp: App {
    var body: some Scene {
        WindowGroup {
            TabView {
                ContentView()
                    .tabItem {
                        Label("起飞仿真", systemImage: "airplane.departure")
                    }
                SaturationStrikeView()
                    .tabItem {
                        Label("饱和打击", systemImage: "scope")
                    }
            }
            .tint(AppTheme.accent)
        }
    }
}
