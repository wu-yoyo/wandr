
import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            NavigationStack {
                FeedView()
            }
            .tabItem {
                Label("Feed", systemImage: "house.fill")
            }

            NavigationStack {
                ExploreView()
            }
            .tabItem {
                Label("Explore", systemImage: "magnifyingglass")
            }

            NavigationStack {
                ProfileView()
            }
            .tabItem {
                Label("Profile", systemImage: "person.fill")
            }
        }
        .tint(.blue)
    }
}

#Preview {
    ContentView()
}
  
