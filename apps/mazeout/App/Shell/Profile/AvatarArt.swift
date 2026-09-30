import SwiftUI
import PathCore

// SHELL S3 (SPEC-ui §1.6.12 AvatarFrame, §2.14.2 avatar index table; SPEC.md §5.12; CONSISTENCY V-24, M-6). The avatar set v552
// ships — the default silhouette + 8 recoloured worker / scientist portraits (our renders, 64 pt tiles with their background):
//   0 default · 1 Walkie · 2 CapGlasses · 3 Detective · 4 Burger · 5 Scientist · 6 Party · 7 BoxHead · 8 Notebook
// `SocialState.avatar` (the player's) and `SimPlayer.avatar` (SOC1's world, range 0…8) index this table. `AvatarFrameTile` is the
// blue superellipse frame (#0070E7 → #009BFD ring, dark outline; green #15E615 when selected) around the portrait, reused by
// Profile, Edit Profile and (SOC2) the leaderboard rows / podium / race tiles.

enum Avatars {
    static let arts: [UIArt] = [.avatar0, .avatar1, .avatar2, .avatar3, .avatar4, .avatar5,
                                .avatar6, .avatar7, .avatar8]
    static var count: Int { arts.count }
    /// The portrait of an index (out of range → the default silhouette).
    static func art(_ index: Int) -> UIArt { arts.indices.contains(index) ? arts[index] : .avatar0 }
}

struct AvatarFrameTile: View {
    let index: Int
    var selected = false
    /// Superellipse exponent of the frame (3.4-3.6 measured).
    var n: CGFloat = 3.5
    /// Ring thickness as a fraction of the tile width (5-6 pt on the 80 pt grid tile, VERIFIED meta-003).
    var ring: CGFloat = 0.075

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let r = w * ring
            ZStack {
                AvatarRing(selected: selected, n: n)
                ArtImage(art: Avatars.art(index), contentMode: .fill)
                    .frame(width: w - 2 * r, height: h - 2 * r)
                    .clipShape(Superellipse(n: n + 0.3))
                    .overlay(Superellipse(n: n + 0.3).stroke(Color(hex: selected ? Skin.profileAvatarArtAvatarFrameTileStrokeSelected : Skin.profileAvatarArtAvatarFrameTileStrokeNotSelected), lineWidth: max(1, w * 0.012)))
            }
            .frame(width: w, height: h)
        }
        .accessibilityHidden(true)
    }
}

/// The frame's ring, rasterised once per look.
private struct AvatarRing: View {
    let selected: Bool
    let n: CGFloat
    var body: some View {
        Rasterized("avatarRing|\(selected)|\(n)", overflow: 1.5) { _ in
            let ring: [Color] = selected ? [Color(hex: Skin.profileAvatarArtAvatarRingRing0), Color(hex: Skin.profileAvatarArtAvatarRingRing1), Color(hex: Skin.profileAvatarArtAvatarRingRing2)]
                                         : [Color(hex: Skin.profileAvatarArtAvatarRing0), Color(hex: Skin.profileAvatarArtAvatarRing1), Color(hex: Skin.profileAvatarArtAvatarRing2)]
            ZStack {
                Superellipse(n: n).fill(Color(hex: selected ? Skin.profileAvatarArtAvatarRingFillSelected : Skin.profileAvatarArtAvatarRingFillNotSelected)).offset(y: 1.2)
                Superellipse(n: n).fill(Color(hex: selected ? Skin.profileAvatarArtAvatarRingFillSelected : Skin.profileAvatarArtAvatarRingFillNotSelected))
                Superellipse(n: n)
                    .fill(LinearGradient(stops: [.init(color: ring[0], location: 0), .init(color: ring[1], location: 0.12),
                                                 .init(color: ring[2], location: 1)], startPoint: .top, endPoint: .bottom))
                    .padding(1.2)
            }
        }
    }
}

/// The player's portrait over S1's home avatar tile (its inner tile rect; index 0 keeps S1's drawn silhouette).
struct HomeAvatarPortrait: View {
    @Environment(AppModel.self) private var app
    var body: some View {
        let i = app.store.state.social.avatar
        if i > 0 {
            GeometryReader { geo in
                let tile = CGRect(x: 8.6, y: 8.3, width: geo.size.width - 17.2, height: geo.size.height - 16.0)
                ArtImage(art: Avatars.art(i), contentMode: .fill)
                    .frame(width: tile.width, height: tile.height)
                    .clipShape(Superellipse(n: 3.8))
                    .offset(x: tile.minX, y: tile.minY)
            }
            .allowsHitTesting(false)
            .accessibilityHidden(true)
        }
    }
}
