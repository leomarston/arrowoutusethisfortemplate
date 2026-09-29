# Independent reference for MFRandom (SPEC-architecture §4.13): SplitMix64 seeding + xoshiro256** (Blackman & Vigna).
M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15
def mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)
def splitmix(x):            # one SplitMix64 step from state x (returns the output)
    return mix((x + G) & M)
def rotl(x, k): return ((x << k) | (x >> (64 - k))) & M
class X:
    def __init__(self, seed=None, state=None):
        if state is not None: self.s = list(state); return
        sm = seed; out = []
        for _ in range(4):
            sm = (sm + G) & M; out.append(mix(sm))
        self.s = out
    def next(self):
        s = self.s
        r = (rotl((s[1] * 5) & M, 7) * 9) & M
        t = (s[1] << 17) & M
        s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45)
        return r
def fnv1a64(label):
    h = 0xcbf29ce484222325
    for b in label.encode('utf-8'):
        h ^= b; h = (h * 0x100000001b3) & M
    return h
def fork(x, label):
    s = x.s
    folded = s[0] ^ rotl(s[1], 16) ^ rotl(s[2], 32) ^ rotl(s[3], 48)
    return X(seed=splitmix(folded ^ fnv1a64(label)))
def attempt_seed(install, level, attempt):
    h = splitmix(install ^ fnv1a64("attempt"))
    h = splitmix(h ^ (level & M))
    h = splitmix(h ^ (attempt & M))
    return h

print("splitmix64(seed 0) first outputs:", [hex(v) for v in [mix((0 + G*i) & M) for i in (1,2,3,4)]])
v = X(state=[1,2,3,4]); print("xoshiro256** state(1,2,3,4):", [v.next() for _ in range(4)])
for seed in (0, 1, 42):
    x = X(seed=seed)
    print(f"seed {seed}:", ", ".join("0x%016X" % x.next() for _ in range(8)))
for seed, lab in ((42, "spawn"), (42, "hint")):
    f = fork(X(seed=seed), lab)
    print(f"fork {seed} {lab}:", ", ".join("0x%016X" % f.next() for _ in range(4)))
print("attemptSeed(42,1,1) = 0x%016X" % attempt_seed(42, 1, 1))
print("attemptSeed(42,1,2) = 0x%016X" % attempt_seed(42, 1, 2))
print("attemptSeed(42,2,1) = 0x%016X" % attempt_seed(42, 2, 1))
print("fnv1a64('spawn') = 0x%016X" % fnv1a64("spawn"), " fnv1a64('') = 0x%016X" % fnv1a64(""))
x = X(seed=42); print("unit() x4 from seed 42:", [ (x.next() >> 11) * 2.0**-53 for _ in range(4)])
