#!/usr/bin/env python3
"""tools/sortpuzzle/ref.py — an INDEPENDENT reference of the SortPuzzle module's level generator and solver
(Packages/PathCore/Sources/SortPuzzle; docs/architecture/PUZZLE-MODULE.md §6b). Swift and Python must agree exactly.

    python3 tools/sortpuzzle/ref.py            # prints the first levels, their solutions' lengths and hashes
    python3 tools/sortpuzzle/ref.py --write    # (re)writes the goldens fixture from App/Resources/Tuning/sort.json
    python3 tools/sortpuzzle/ref.py --check    # exit 1 when the fixture is stale (CI's Linux job); also self-checks
                                               #   every golden level: solvable by the recorded solution, no complete
                                               #   tube dealt, colour counts = capacity

The fixture (Packages/PathCore/Tests/Fixtures/sortpuzzle_goldens.json) holds the rules it was made from (sort.json without
its board section) and, for levels 1…N, the level's tag, capacity and tubes (bottom → top), an FNV-1a 64 hash of its
canonical text and the length of the solver's first solution. SortPuzzleTests decodes the same rules with the Swift
`SortRules`, generates the same levels and compares every field: the Swift side is never edited to match itself.
If the generator or the solver changes, change BOTH, re-run --write and review the diff.

The algorithm (the Swift mirrors it statement by statement):
  seed    = PathRandom.levelSeed(level, salt)   (SplitMix64 chain, tools/rng_ref.py)
  rng     = PathRandom(seed)                    (xoshiro256**, Lemire's unbiased `below`, Fisher-Yates back to front)
  deal    : units = colour-major [0]*c + [1]*c + … ; shuffle; k full tubes of c units + e empty tubes
  reject  : a dealt tube already complete (full, one colour), or no solution within `solverBudget` expanded states;
            up to `maxAttempts` deals (at least one); then the last deal with one empty tube per colour (always solvable:
            every unit can go straight to its colour's tube). A second golden set ("stress", tight rules) pins these paths
  moves   : a pour moves the source's top run (same colour) — as many units as fit — onto an empty tube or onto the
            same colour; the solver skips complete sources, a whole-tube pour into an empty tube, and every empty
            target but the first (they are alike)
  solver  : iterative depth-first search, moves onto a tube first, then into the (first) empty tube; states are
            multisets of tubes (visited once); `budget` = expanded states
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
SORT_JSON = os.path.join(APP, "App", "Resources", "Tuning", "sort.json")
GOLDENS = os.path.join(APP, "Packages", "PathCore", "Tests", "Fixtures", "sortpuzzle_goldens.json")
LEVELS = 40          # goldens for levels 1…LEVELS
FULL_LEVELS = 3      # of which the solution's moves are pinned too
# A second set under tight rules, so the goldens also pin the rejection paths (a deal the solver gives up on, a complete
# tube dealt) and the last-resort deal (one empty tube per colour). sort.json's own levels never reach them (1…200 are
# all accepted at the first deal).
STRESS_LEVELS = 12
STRESS = {"curve": [{"from": 1, "colors": 5, "capacity": 4, "empty": 1}], "maxAttempts": 4, "solverBudget": 300}
SELFCHECK_BUDGET = 200000

# ---------------------------------------------------------------------------------------------------- the RNG (PathRandom)
M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)


def splitmix(x):
    return mix((x + G) & M)


def rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & M


def fnv1a64(text):
    h = 0xCBF29CE484222325
    for b in text.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & M
    return h


class Rng:
    """xoshiro256** seeded by four SplitMix64 outputs (PathRandom.init(seed:))."""

    def __init__(self, seed):
        sm, s = seed & M, []
        for _ in range(4):
            sm = (sm + G) & M
            s.append(mix(sm))
        self.s = s

    def next(self):
        s = self.s
        r = (rotl((s[1] * 5) & M, 7) * 9) & M
        t = (s[1] << 17) & M
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = rotl(s[3], 45)
        return r

    def below(self, n):
        """PathRandom.below(UInt64): Lemire's multiply-shift with rejection."""
        m = self.next() * n
        low = m & M
        if low < n:
            threshold = ((1 << 64) - n) % n
            while low < threshold:
                m = self.next() * n
                low = m & M
        return m >> 64

    def shuffle(self, a):
        for i in range(len(a) - 1, 0, -1):
            j = self.below(i + 1)
            if i != j:
                a[i], a[j] = a[j], a[i]


def level_seed(level, salt):
    h = splitmix((salt & M) ^ fnv1a64("level"))
    return splitmix(h ^ (level & M))


# ---------------------------------------------------------------------------------------------------- the rules
def top_run(t):
    if not t:
        return 0
    n, top = 0, t[-1]
    for u in reversed(t):
        if u != top:
            break
        n += 1
    return n


def is_complete(t, c):
    return len(t) == c and top_run(t) == c


def is_solved(tubes, c):
    return all(not t or is_complete(t, c) for t in tubes)


def can_pour(tubes, s, d, c):
    if s == d or not (0 <= s < len(tubes)) or not (0 <= d < len(tubes)):
        return False
    src, dst = tubes[s], tubes[d]
    if not src or len(dst) >= c:
        return False
    return not dst or dst[-1] == src[-1]


def pour_count(tubes, s, d, c):
    return min(top_run(tubes[s]), c - len(tubes[d]))


def apply(tubes, move, c):
    s, d = move
    n = pour_count(tubes, s, d, c)
    out = [list(t) for t in tubes]
    moved = out[s][len(out[s]) - n:]
    del out[s][len(out[s]) - n:]
    out[d].extend(moved)
    return out


def has_legal_move(tubes, c):
    n = len(tubes)
    return any(can_pour(tubes, s, d, c) for s in range(n) for d in range(n))


def useful_moves(tubes, c):
    n = len(tubes)
    first_empty = next((i for i, t in enumerate(tubes) if not t), -1)
    onto, into_empty = [], []
    for s in range(n):
        src = tubes[s]
        if not src:
            continue
        top, run = src[-1], top_run(src)
        if len(src) == c and run == c:
            continue
        for d in range(n):
            if d == s:
                continue
            dst = tubes[d]
            if len(dst) >= c:
                continue
            if not dst:
                if run == len(src) or d != first_empty:
                    continue
                into_empty.append((s, d))
            elif dst[-1] == top:
                onto.append((s, d))
    return onto + into_empty


def key(tubes):
    return tuple(sorted(tuple(t) for t in tubes))


def solve(tubes, c, budget):
    """The first solution of the depth-first search (a list of (from, to)), or None (none within `budget`)."""
    if is_solved(tubes, c):
        return []
    visited = {key(tubes)}
    expanded = 1
    frames = [[tubes, useful_moves(tubes, c), 0]]
    path = []
    while frames:
        f = frames[-1]
        if f[2] >= len(f[1]):
            frames.pop()
            if path:
                path.pop()
            continue
        m = f[1][f[2]]
        f[2] += 1
        nxt = apply(f[0], m, c)
        k = key(nxt)
        if k in visited:
            continue
        visited.add(k)
        path.append(m)
        if is_solved(nxt, c):
            return path
        if expanded >= budget:
            return None
        expanded += 1
        frames.append([nxt, useful_moves(nxt, c), 0])
    return None


# ---------------------------------------------------------------------------------------------------- the generator
def band(rules, level):
    curve = rules["levels"]["curve"]
    pick = curve[0]
    for b in curve:
        if b["from"] <= level:
            pick = b
    return pick


def tag(rules, level):
    lv = rules["levels"]
    if lv["superHardEvery"] > 0 and level % lv["superHardEvery"] == 0:
        return "superHard"
    if lv["hardEvery"] > 0 and level % lv["hardEvery"] == 0:
        return "hard"
    return "normal"


def generate(rules, level):
    b = band(rules, level)
    k, c, e = max(0, b["colors"]), max(0, b["capacity"]), max(0, b["empty"])
    lv = rules["levels"]
    rng = Rng(level_seed(level, lv["salt"]))
    last = None
    for _ in range(max(1, lv["maxAttempts"])):
        units = [col for col in range(k) for _ in range(c)]
        rng.shuffle(units)
        tubes = [units[i * c:(i + 1) * c] for i in range(k)] + [[] for _ in range(e)]
        last = tubes
        if any(is_complete(t, c) for t in tubes[:k]):
            continue
        if solve(tubes, c, lv["solverBudget"]) is not None:
            return dict(level=level, tag=tag(rules, level), capacity=c, colors=k, tubes=tubes)
    tubes = last[:k] + [[] for _ in range(max(e, k))]
    return dict(level=level, tag=tag(rules, level), capacity=c, colors=k, tubes=tubes)


def canonical(lv):
    """The text the golden hash is taken over: '<level>|<tag>|c<capacity>|k<colors>|' + tubes '/'-joined, units ','."""
    return (f"{lv['level']}|{lv['tag']}|c{lv['capacity']}|k{lv['colors']}|"
            + "/".join(",".join(str(u) for u in t) for t in lv["tubes"]))


def load_rules():
    with open(SORT_JSON, encoding="utf-8") as f:
        doc = json.load(f)
    return {k: v for k, v in doc.items() if k != "board"}


def stress_rules(rules):
    out = json.loads(json.dumps(rules))
    out["levels"].update(json.loads(json.dumps(STRESS)))
    return out


def build(rules):
    stress = stress_rules(rules)
    return dict(rules=rules, levels=build_set(rules, LEVELS),
                stress=dict(rules=stress, levels=build_set(stress, STRESS_LEVELS)))


def build_set(rules, count):
    out = []
    budget = rules["levels"]["solverBudget"]
    for n in range(1, count + 1):
        lv = generate(rules, n)
        sol = solve(lv["tubes"], lv["capacity"], budget)
        row = dict(level=n, tag=lv["tag"], capacity=lv["capacity"], colors=lv["colors"], tubes=lv["tubes"],
                   hash="%016X" % fnv1a64(canonical(lv)), solution=None if sol is None else len(sol))
        if n <= FULL_LEVELS and sol is not None:
            row["moves"] = [[s, d] for s, d in sol]
        out.append(row)
    return out


def selfcheck(doc):
    return check_set(doc["levels"]) + check_set(doc["stress"]["levels"])


def check_set(rows):
    errs = []
    for row in rows:
        c, tubes = row["capacity"], row["tubes"]
        counts = {}
        for t in tubes:
            if len(t) > c:
                errs.append(f"L{row['level']}: a tube over capacity")
            for u in t:
                counts[u] = counts.get(u, 0) + 1
        if sorted(counts) != list(range(row["colors"])) or any(v != c for v in counts.values()):
            errs.append(f"L{row['level']}: colour counts {counts} != {c} each")
        if any(is_complete(t, c) for t in tubes):
            errs.append(f"L{row['level']}: a complete tube was dealt")
        sol = solve(tubes, c, SELFCHECK_BUDGET)
        if sol is None:
            errs.append(f"L{row['level']}: no solution within {SELFCHECK_BUDGET} states")
            continue
        state = tubes
        for m in sol:
            if not can_pour(state, m[0], m[1], c):
                errs.append(f"L{row['level']}: illegal move {m} in the solution")
                break
            state = apply(state, m, c)
        if not is_solved(state, c):
            errs.append(f"L{row['level']}: the solution does not solve it")
    return errs


def dump(doc):
    """One level per line (a readable diff), stable key order."""
    lines = ["{", '  "about": "GENERATED by tools/sortpuzzle/ref.py --write (the independent reference of '
             'SortPuzzle\'s generator + solver). Do not edit.",',
             '  "rules": ' + json.dumps(doc["rules"], sort_keys=True) + ",", '  "levels": [']
    rows = [json.dumps(r, sort_keys=True) for r in doc["levels"]]
    lines += ["    " + r + ("," if i < len(rows) - 1 else "") for i, r in enumerate(rows)]
    lines += ["  ],", '  "stress": {', '    "rules": ' + json.dumps(doc["stress"]["rules"], sort_keys=True) + ",",
              '    "levels": [']
    rows = [json.dumps(r, sort_keys=True) for r in doc["stress"]["levels"]]
    lines += ["      " + r + ("," if i < len(rows) - 1 else "") for i, r in enumerate(rows)]
    lines += ["    ]", "  }", "}"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = build(load_rules())
    errs = selfcheck(doc)
    if errs:
        print("\n".join("ref.py: " + e for e in errs), file=sys.stderr)
        return 1
    text = dump(doc)
    if a.write:
        with open(GOLDENS, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"ref.py: wrote {os.path.relpath(GOLDENS, APP)} ({len(doc['levels'])} levels)")
        return 0
    if a.check:
        old = open(GOLDENS, encoding="utf-8").read() if os.path.exists(GOLDENS) else ""
        if old != text:
            print(f"ref.py: {os.path.relpath(GOLDENS, APP)} is stale (sort.json, the generator or the solver changed): "
                  "run python3 tools/sortpuzzle/ref.py --write (in the app folder) and review the diff", file=sys.stderr)
            return 1
        print(f"ref.py: goldens up to date ({len(doc['levels'])} levels, every one solvable by its recorded solution)")
        return 0
    for name, rows in (("", doc["levels"]), ("stress ", doc["stress"]["levels"])):
        for r in rows:
            print(f"{name}L{r['level']:>3} {r['tag']:<9} k{r['colors']} c{r['capacity']} tubes {len(r['tubes']):>2} "
                  f"solution {str(r['solution']):>4} hash {r['hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
