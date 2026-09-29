#!/usr/bin/env python3
"""C1 (SPEC-architecture §4.13): an INDEPENDENT reference for the parts of PathRandom that tools/rng_ref.py (read-only,
copied from MF) does not cover yet: `levelSeed(level:salt:)` (generated levels, §4.14) and the Lemire `below(n)` draw.
Re-implemented from the algorithm descriptions (SplitMix64, FNV-1a 64, xoshiro256**, Lemire multiply-shift with
rejection), not from the Swift. RandomTests pins these values and also runs this script live.
Requested: fold `level_seed` into tools/rng_ref.py (the orchestrator owns that file).

    python3 Packages/PathCore/Tests/tools/c1_rng_ref_extra.py
"""
M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)


def splitmix(x):
    return mix((x + G) & M)


def fnv1a64(s):
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 0x100000001B3) & M
    return h


def rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & M


class Xoshiro:
    def __init__(self, seed):
        self.s = []
        sm = seed
        for _ in range(4):
            sm = (sm + G) & M
            self.s.append(mix(sm))

    def next(self):
        s = self.s
        r = (rotl((s[1] * 5) & M, 7) * 9) & M
        t = (s[1] << 17) & M
        s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45)
        return r

    def below(self, n):
        """Lemire: the high 64 bits of next()·n, rejecting low parts under (2^64 − n) mod n."""
        m = self.next() * n
        low = m & M
        if low < n:
            threshold = ((1 << 64) - n) % n
            while low < threshold:
                m = self.next() * n
                low = m & M
        return m >> 64


def level_seed(level, salt):
    h = splitmix(salt ^ fnv1a64("level"))
    h = splitmix(h ^ (level & M))
    return h


if __name__ == "__main__":
    for salt, level in ((0, 1), (0, 62), (1, 100), (1, 101), (0xC0FFEE, 5000), (42, -1)):
        print("levelSeed(level %d, salt %d) = 0x%016X" % (level, salt, level_seed(level, salt)))
    for seed, n in ((42, 6), (7, 1000), (1, 3), (0, 1 << 63)):
        x = Xoshiro(seed)
        print("below seed %d n %d:" % (seed, n), ", ".join(str(x.below(n)) for _ in range(8)))
