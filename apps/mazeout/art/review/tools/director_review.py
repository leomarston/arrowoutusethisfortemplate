#!/usr/bin/env python3
"""Writes the per-entry table of art/REVIEW.md (between the BEGIN/END TABLE markers) from art/review/grades-director.json
(round 3: each entry carries its own `gap`; round 2's file had none, so the graders' notes fill in), the graders' notes
(art/review/grades-{A,B}.json) and art/MANIFEST.json.
    cd apps/mazeout; python3 art/review/tools/director_review.py"""
import json
import os

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
D = json.load(open(os.path.join(APP, "art/review/grades-director.json")))
A = {e["id"]: e for e in json.load(open(os.path.join(APP, "art/review/grades-A.json")))["entries"]}
B = {e["id"]: e for e in json.load(open(os.path.join(APP, "art/review/grades-B.json")))["entries"]}
M = {e["id"]: e for e in json.load(open(os.path.join(APP, "art/MANIFEST.json")))["entries"]}


def short(t, n=230):
    t = " ".join(str(t or "").split()).replace("|", "/")
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + " ..."


def remaining(i):
    if i in B:
        return B[i].get("fix") or B[i].get("note", "")
    if i in A:
        return A[i].get("note", "")
    return ""


def table():
    groups = {}
    for i, g in D["entries"].items():
        grp = M.get(i, {}).get("group", "other")
        groups.setdefault(grp, []).append((i, g))
    order = ["board", "hud", "boosters", "popups", "fx", "home", "characters", "loading-win", "avatars", "events-streak",
             "events-claw", "events-skyjump", "events-rocket", "leaderboard", "profile-shop-settings", "app-icon", "other"]
    out = []
    for grp in order + sorted(set(groups) - set(order)):
        if grp not in groups:
            continue
        out.append(f"\n### {grp}\n")
        out.append("| id | grade | was (r2) | what changed (round 3) | remaining gap |")
        out.append("|---|---|---|---|---|")
        for i, g in sorted(groups[grp], key=lambda t: t[0]):
            ch = short(g["changed"], 260) if g["changed"] else "-"
            if "gap" in g:
                rem = short(g["gap"], 230) or "-"
            elif g["grade"] == "n/a":
                rem = "not shipped"
            elif g["changed"]:
                rem = "none visible at game size" if g["grade"] == "A" else short(g["changed"].split(". ")[-1], 200)
            else:
                rem = short(remaining(i)) or "-"
            out.append(f"| `{i}` | **{g['grade']}** | {g['before']} | {ch} | {rem} |")
    return "\n".join(out)


def main():
    p = os.path.join(APP, "art", "REVIEW.md")
    s = open(p).read()
    a, b = s.index("<!-- BEGIN TABLE -->"), s.index("<!-- END TABLE -->")
    s = s[: a + len("<!-- BEGIN TABLE -->")] + "\n" + table() + "\n\n" + s[b:]
    open(p, "w").write(s)
    print("wrote", p)


if __name__ == "__main__":
    main()
