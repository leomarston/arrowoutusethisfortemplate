"""pathrandom.py — bit-exact Python mirror of PathCore's PathRandom (Packages/PathCore/Sources/PathCore/Random/
PathRandom.swift; reference tools/rng_ref.py). The level generator draws EVERY random number through this class, so
C4's Swift port of the generator can reproduce design/levels.json's designed levels byte for byte (a LevelLibrary test).

Only integer arithmetic and correctly-rounded IEEE operations are used by the generator on top of it (no exp/log/sqrt).
"""
M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def _mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)


def split_mix(x):
    """PathRandom.splitMix(x) = mix(x &+ golden)."""
    return _mix((x + G) & M)


def _rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & M


def fnv1a64(label):
    h = 0xcbf29ce484222325
    for b in label.encode('utf-8'):
        h ^= b
        h = (h * 0x100000001b3) & M
    return h


def level_seed(level, salt):
    """PathRandom.levelSeed(level:salt:)."""
    h = split_mix((salt ^ fnv1a64('level')) & M)
    h = split_mix((h ^ (level & M)) & M)
    return h


class PathRandom:
    __slots__ = ('s',)

    def __init__(self, seed=0, state=None):
        if state is not None:
            self.s = list(state)
            return
        sm = seed & M
        out = []
        for _ in range(4):
            sm = (sm + G) & M
            out.append(_mix(sm))
        self.s = out

    def next(self):
        s = self.s
        r = (_rotl((s[1] * 5) & M, 7) * 9) & M
        t = (s[1] << 17) & M
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return r

    def fork(self, label):
        s = self.s
        folded = s[0] ^ _rotl(s[1], 16) ^ _rotl(s[2], 32) ^ _rotl(s[3], 48)
        return PathRandom(seed=split_mix((folded ^ fnv1a64(label)) & M))

    def unit(self):
        return (self.next() >> 11) * (2.0 ** -53)

    def below(self, n):
        """Lemire multiply-shift with rejection, exactly as PathRandom.below(UInt64)."""
        if n <= 0:
            raise ValueError('below(0)')
        m = self.next() * n
        low = m & M
        if low < n:
            threshold = ((1 << 64) - n) % n
            while low < threshold:
                m = self.next() * n
                low = m & M
        return m >> 64

    def int_in(self, lo, hi):
        """Uniform integer in [lo, hi] (closed)."""
        return lo + self.below(hi - lo + 1)

    def chance(self, p):
        return self.unit() < p

    def shuffle(self, a):
        for i in range(len(a) - 1, 0, -1):
            j = self.below(i + 1)
            if i != j:
                a[i], a[j] = a[j], a[i]
        return a

    def element(self, seq):
        return seq[self.below(len(seq))] if seq else None


if __name__ == '__main__':
    # the values RandomTests pins (must equal `python3 tools/rng_ref.py`)
    for seed in (0, 1, 42):
        x = PathRandom(seed)
        print('seed %d:' % seed, ', '.join('0x%016X' % x.next() for _ in range(8)))
    for seed, lab in ((42, 'spawn'), (42, 'hint')):
        f = PathRandom(seed).fork(lab)
        print('fork %d %s:' % (seed, lab), ', '.join('0x%016X' % f.next() for _ in range(4)))
    print('levelSeed(62, 0) = 0x%016X' % level_seed(62, 0))
