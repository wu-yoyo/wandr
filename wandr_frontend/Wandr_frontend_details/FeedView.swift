
import SwiftUI

struct FeedView: View {
    let posts = [
        ("Tokyo", "Japan", "Troy", "9.5", "tokyo"),
        ("Lisbon", "Portugal", "Yoyo", "9.2", "lisbon"),
        ("Paris", "France", "Kate", "8.8", "paris"),
        ("New York", "USA", "Charles", "9.0", "newyork")
    ]

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 20) {
                ForEach(posts, id: \.0) { post in
                    VStack(alignment: .leading, spacing: 12) {

                        Image(post.4)
                            .resizable()
                            .scaledToFill()
                            .frame(height: 200)
                            .frame(maxWidth: .infinity)
                            .clipped()

                        VStack(alignment: .leading, spacing: 8) {
                            Text(post.0)
                                .font(.title2)
                                .bold()

                            Text(post.1)
                                .foregroundStyle(.secondary)

                            HStack {
                                Text("\(post.2) visited here")
                                Spacer()
                                Text("⭐ \(post.3)/10")
                            }
                            .font(.subheadline)
                        }
                        .padding(.horizontal)
                        .padding(.bottom)
                    }
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                }
            }
            .padding()
        }
        .navigationTitle("Wandr")
    }
}

#Preview {
    NavigationStack {
        FeedView()
    }
}
