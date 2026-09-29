"""The CORNER's hit animation, MEASURED on the phone (v552) clips -- data for the board code (App/Board/CornerLayer.swift) and
the proof sheets (corner_proofs.py bounce / clip). Lane log: art/lanes/corner.md "Hit animation".

Clips (60 Hz phone recordings, full-res crops around the corner cell, research/motion-tools/mf.raw):
  S2-L070-corner-first-use.mov       L70 corner (8, 14), facing (1, -1), a 3-cell <- arrow whose head travels 2 cells to it
  S2-L070-corner-lower-turn-up.mov   L70 corner (0, 17), same facing, same arrow shape
  S2-L071-corner-right-moving-turns-up.mov   L71 corner (7, 17), facing (-1, -1), a 3-cell -> arrow, 2 cells to it
Tracker: the plate's red centroid projected on the facing unit vector s (pitch units, + = out of the spring, toward the
arrows it turns); the spring's pixels along s. The three clips give the SAME curve in pitch units (two pitches, 20.63 and
19.66 pt; frame by frame within 0.003 p), so it scales with the zoom like the sprite.

What moves (and what does not):
  - the PLATE translates along s; its length and thickness stay constant (within 1 capture px): no squash, no rotation,
    no colour change;
  - the SPRING stretches/compresses along s between a FIXED foot and the plate (its foot end does not move: n -0.914 on
    every frame; the lobes near the plate move most): a scale along s about the foot;
  - the arrow draws OVER the corner the whole time (the exit mover sits above the obstacle root);
  - silent (every in-level event is, SPEC-motion-audio MA1).
Timing (tap R = first motion; exit kinematics s(tau) of SPEC-motion-audio; clip 1: R 1.1644, head at the corner cell
centre 1.2795 = R + T(2), tail at that centre 1.3456 = R + T(4)):
  PRESS   the plate is IN on the first frame after the head reaches the corner cell centre (-0.083 p with the head still
          covering part of it, -0.095 one frame later); the frame 15 ms before that is at rest (-0.002).
  HOLD    it stays in, sinking slowly (-0.093 -> -0.105), while the arrow's body slides over it;
  RELEASE when the arrow's TAIL passes the corner cell centre (+0.010 s) it springs out: overshoot +0.079 p at +0.063 s,
          back to -0.030 at +0.124, at rest at +0.229 (each segment an ease-in-out; fit rms 0.0076 p over 21 frames,
          max 0.032 p on the first pressed frame, which the head half covers).
  INFERRED: release tied to the tail -- all three clips have 3-cell arrows, so "tail passes" (0.066 s after the head) and a
  fixed 0.066 s hold cannot be told apart; physically the plate stays pushed while the body slides over it.
"""
import math

# pitch units along the facing s; times in seconds
PUSH = -0.093            # reached within one frame of the head's arrival (the `.corner` beat)
PRESS_LEAD = 0.012       # the push starts this long BEFORE the beat (the head tip reaches the plate first) ...
PRESS_DUR = 0.016        # ... and is complete 0.004 s after it (one 60 Hz frame)
HOLD_END = -0.105        # linear sink while the body slides over the plate
RELEASE_AFTER_TAIL = 0.010
PEAK = (0.063, 0.079)    # (time after release, offset)
TROUGH = (0.124, -0.030)
REST_AT = 0.229
HOLD_EXAMPLE = 0.066     # the clips' hold (3-cell arrow: tail passes the corner 0.066 s after the head)

# the spring: scale along s about the foot; the foot pivot and the rest length to the plate's back face (pitch units)
PIVOT = -0.98            # the foot's far end on the axis: cell centre + PIVOT * s (our layers' spring ends at -0.978)
PLATE_BACK = -0.286      # the plate's back face on the axis (ours; 456/457 capture -0.281)
SPRING_LEN = PLATE_BACK - PIVOT   # 0.694


def ease_in_out(f):
    f = min(1.0, max(0.0, f))
    return (1 - math.cos(math.pi * f)) / 2


def total_after_release():
    return REST_AT


def offset(t, hold=HOLD_EXAMPLE):
    """The plate offset along s (pitch) at time t after the `.corner` beat (the head at the corner cell centre); `hold` =
    time from the beat until the arrow's tail reaches the corner cell centre (T(s_beat + cells - 1) - T(s_beat))."""
    t0 = -PRESS_LEAD
    if t < t0:
        return 0.0
    t1 = t0 + PRESS_DUR
    if t < t1:
        return PUSH * math.sin(math.pi / 2 * (t - t0) / PRESS_DUR)
    r = hold + RELEASE_AFTER_TAIL
    if t < r:
        return PUSH + (HOLD_END - PUSH) * (t - t1) / max(1e-6, r - t1)
    b = t - r
    if b < PEAK[0]:
        return HOLD_END + (PEAK[1] - HOLD_END) * ease_in_out(b / PEAK[0])
    if b < TROUGH[0]:
        return PEAK[1] + (TROUGH[1] - PEAK[1]) * ease_in_out((b - PEAK[0]) / (TROUGH[0] - PEAK[0]))
    if b < REST_AT:
        return TROUGH[1] * (1 - ease_in_out((b - TROUGH[0]) / (REST_AT - TROUGH[0])))
    return 0.0


def spring_scale(x):
    """The spring's scale along s about the foot pivot for a plate offset x (pitch)."""
    return 1.0 + x / SPRING_LEN


def keyframes(hold=HOLD_EXAMPLE, fps=60.0):
    """(times after the beat, offsets) sampled at `fps` from the first pushed frame to rest: what a CAKeyframeAnimation
    with calculationMode .linear needs (the board code samples exits the same way)."""
    t, out = -PRESS_LEAD, []
    end = hold + RELEASE_AFTER_TAIL + REST_AT
    while t <= end + 1e-9:
        out.append((round(t, 4), round(offset(t, hold), 4)))
        t += 1.0 / fps
    out.append((round(end, 4), 0.0))
    return out


# the measured frames (clip 1, t after the beat, offset p) -- the fit's evidence, kept for the proofs
MEASURED = [(-0.015, -0.0023), (0.001, -0.0829), (0.018, -0.0946), (0.035, -0.0946), (0.051, -0.1024), (0.068, -0.1096),
            (0.084, -0.0885), (0.101, -0.0443), (0.118, 0.0371), (0.134, 0.0812), (0.151, 0.0649), (0.168, 0.0264),
            (0.184, -0.0126), (0.201, -0.0295), (0.218, -0.0283), (0.234, -0.0219), (0.251, -0.0151), (0.267, -0.0078),
            (0.284, -0.0034), (0.301, 0.0), (0.317, -0.0003)]


if __name__ == "__main__":
    import sys
    err = [offset(t) - x for t, x in MEASURED]
    print("fit vs clip 1: rms %.4f p, max %.4f p" % (math.sqrt(sum(e * e for e in err) / len(err)), max(abs(e) for e in err)))
    if "--keys" in sys.argv:
        for t, x in keyframes():
            print("%+.4f  %+.4f  spring x%.3f" % (t, x, spring_scale(x)))
