# socialsim/core.py — the exact-arithmetic primitives of Arrow Out's offline social simulation.
#
# This is the REFERENCE implementation for PathCore/Social (Swift). Rules that make Swift and Python agree bit for bit:
#   * integers: 64-bit unsigned with wrap-around (Python: & M after every * and +);
#   * doubles: only IEEE-754 correctly rounded operations (+ - * / and comparisons, floor via math.floor on a double);
#     NO exp/log/pow/sin/cos/sqrt in the model (they are not guaranteed identical across libms), NO fused multiply-add;
#   * rounding is always floor(x) or floor(x + 0.5) written out (never Python's round(), which is banker's rounding);
#   * integer division / modulo of possibly negative numbers go through floordiv()/posmod() (Swift's / and % truncate).
# The hash primitives are the ones of tools/rng_ref.py (SplitMix64 finaliser + FNV-1a 64), used STATELESSLY:
# every derived quantity is h64(seed, "label", a, b, ...) so any player / day / event can be computed in O(1).
import math

M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15

def mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)

def splitmix(x):
    return mix((x + G) & M)

def fnv1a64(label):
    h = 0xcbf29ce484222325
    for b in label.encode('utf-8'):
        h ^= b
        h = (h * 0x100000001b3) & M
    return h

_label_cache = {}
def h64(seed, label, *xs):
    """Stateless keyed hash: splitmix chain over (seed ^ fnv(label)), then each integer argument (two's complement)."""
    lf = _label_cache.get(label)
    if lf is None:
        lf = _label_cache[label] = fnv1a64(label)
    h = splitmix((seed ^ lf) & M)
    for x in xs:
        h = splitmix(h ^ (x & M))
    return h

def unit(h):
    """[0, 1) double from the top 53 bits."""
    return (h >> 11) * (1.0 / 9007199254740992.0)

def u01(seed, label, *xs):
    return unit(h64(seed, label, *xs))

def below(seed, label, n, *xs):
    """Integer in [0, n) — multiply-shift on the top 53 bits (exact, same as floor(unit * n) for n < 2^53)."""
    return int(math.floor(u01(seed, label, *xs) * n))

def floordiv(a, b):
    return a // b          # Python floors; Swift must use a floor-division helper

def posmod(a, b):
    return a % b           # Python result has the sign of b; Swift: ((a % b) + b) % b

def fl(x):
    return math.floor(x)

def round_half_up(x):
    return math.floor(x + 0.5)

# ---------------------------------------------------------------- keyed permutations (format-preserving)

def _perm_pow2(x, half, key):
    mask = (1 << half) - 1
    L = x >> half
    R = x & mask
    for r in range(4):
        F = splitmix((key ^ ((r + 1) << 56) ^ R) & M) & mask
        L, R = R, L ^ F
    return (L << half) | R

def perm(x, n, key):
    """Bijection of [0, n) keyed by `key`: a 4-round balanced Feistel network on the smallest even bit width
    whose range covers n, with cycle-walking back into [0, n). n >= 1."""
    if n <= 1:
        return 0
    bits = max(2, (n - 1).bit_length())
    if bits & 1:
        bits += 1
    half = bits // 2
    y = _perm_pow2(x, half, key)
    while y >= n:
        y = _perm_pow2(y, half, key)
    return y

def perm_inv(y, n, key):
    """Inverse of perm (used by tests only)."""
    if n <= 1:
        return 0
    bits = max(2, (n - 1).bit_length())
    if bits & 1:
        bits += 1
    half = bits // 2
    mask = (1 << half) - 1
    def inv(z):
        L = z >> half
        R = z & mask
        for r in (3, 2, 1, 0):
            F = splitmix((key ^ ((r + 1) << 56) ^ L) & M) & mask
            L, R = R ^ F, L
        return (L << half) | R
    x = inv(y)
    while x >= n:
        x = inv(x)
    return x

# ---------------------------------------------------------------- piecewise-linear tables

def interp(u, xs, ys):
    """Piecewise-linear interpolation, xs strictly increasing, clamped at both ends. Exact IEEE ops only."""
    if u <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if u <= xs[i]:
            x0 = xs[i - 1]; x1 = xs[i]
            t = (u - x0) / (x1 - x0)
            return ys[i - 1] + (ys[i] - ys[i - 1]) * t
    return ys[-1]

# ---------------------------------------------------------------- calendar

EPOCH = 1777273200          # 2026-04-27 07:00:00 UTC (a Monday): world epoch + event-day anchor
DAY = 86400
WEEK = 7 * DAY
EPOCH_UTC_DAY = 20570       # floor(2026-04-27T00:00Z / 86400)

def event_day(t):
    """Event day index (days start at 07:00 UTC)."""
    return int(math.floor((t - EPOCH) / DAY)) if isinstance(t, float) else floordiv(t - EPOCH, DAY)

def event_week(t):
    """Event week index (weeks start Monday 07:00 UTC)."""
    return int(math.floor((t - EPOCH) / WEEK)) if isinstance(t, float) else floordiv(t - EPOCH, WEEK)

def event_day_start(d):
    return EPOCH + d * DAY

def event_week_start(w):
    return EPOCH + w * WEEK

def local_day_minute(t, off_min):
    """Local calendar day number (days since 1970-01-01 in local time) and minute-of-day (double, [0,1440))."""
    ls = t + off_min * 60
    d = floordiv(int(math.floor(ls)), DAY) if isinstance(ls, float) else floordiv(ls, DAY)
    minute = (ls - d * DAY) / 60.0
    return d, minute

def dow_of_local_day(d):
    """0 = Monday ... 6 = Sunday (1970-01-01 was a Thursday)."""
    return posmod(d + 3, 7)
