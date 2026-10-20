import SwiftUI

/// The magnifier mascot reacting to an answer: a hop when you're right, a
/// head-shake when you're not. Still under Reduce Motion.
struct MascotReaction: View {
    let isCorrect: Bool
    /// Plays when the view appears and again whenever this changes.
    var trigger = 0
    /// False shows the mascot without reacting (reviewing an old miss).
    var animates = true

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    /// keyframeAnimator only plays on a change it sees, so the view owns its
    /// own counter and bumps it after appearing.
    @State private var play = 0

    var body: some View {
        let still = reduceMotion || !animates
        LogoTile(scale: 1.4)
            .keyframeAnimator(initialValue: Pose(), trigger: play) { tile, pose in
                tile
                    .rotationEffect(.degrees(still ? 0 : pose.angle))
                    .offset(y: still ? 0 : pose.lift)
            } keyframes: { _ in
                // Both tracks always run; the one that doesn't apply stays at 0.
                let hop = isCorrect ? 1.0 : 0.0
                let shake = isCorrect ? 0.0 : 1.0
                KeyframeTrack(\.lift) {
                    SpringKeyframe(-8 * hop, duration: 0.18)
                    SpringKeyframe(0, duration: 0.3, spring: .bouncy)
                }
                KeyframeTrack(\.angle) {
                    LinearKeyframe(-9 * shake, duration: 0.08)
                    LinearKeyframe(9 * shake, duration: 0.12)
                    LinearKeyframe(-5 * shake, duration: 0.1)
                    SpringKeyframe(0, duration: 0.2)
                }
            }
            .task(id: trigger) {
                guard animates else { return }
                try? await Task.sleep(for: .milliseconds(150))
                guard !Task.isCancelled else { return }
                play += 1
            }
    }

    struct Pose {
        var angle = 0.0
        var lift = 0.0
    }
}
