#!/usr/bin/env python3
"""VERIFY V2: roll build/compare/results.json up against tools/compare/annotations.json.
Copied as-is from apps/matchfactory/tools/compare/summarize.py (e10a076); only this docstring changed.

    tools/compare/summarize.py [--results build/compare/results.json] [--out build/compare/summary.md]

Every region over dE 6 must match an annotation rule (a finding F-nn with an owner, or an explained exception). Prints the
totals and exits 1 when an over-6 region has no rule (the V2 acceptance: "each region is within dE <= 6 or has an explained
exception").
"""
import argparse, fnmatch, json, os, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(ROOT, "build", "compare", "results.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "compare", "summary.md"))
    a = ap.parse_args()
    results = json.load(open(a.results))
    rules = json.load(open(os.path.join(ROOT, "tools", "compare", "annotations.json")))["rules"]

    def rule_for(cid, lang, region):
        for r in rules:
            if fnmatch.fnmatchcase(cid, r["id"]) and fnmatch.fnmatchcase(region, r["region"]) and r.get("lang", lang) == lang:
                return r
        return None

    total = passed = 0
    by_kind = Counter(); by_kind_pass = Counter()
    over = []; missing = []; unannotated = []
    per_finding = defaultdict(list)
    for key in sorted(results):
        v = results[key]
        if v.get("missing"):
            missing.append(key); continue
        for row in v["rows"]:
            total += 1; by_kind[row["kind"]] += 1
            if row["pass"]:
                passed += 1; by_kind_pass[row["kind"]] += 1; continue
            r = rule_for(v["id"], v["lang"], row["name"])
            over.append((key, row, r))
            if r is None:
                unannotated.append((key, row["name"], row["dE"]))
            elif r["type"] == "finding":
                per_finding[r["ref"]].append(f"{key}:{row['name']} {row['dE']:.1f}")
    captures = len([k for k in results if not results[k].get("missing")])
    lines = ["# V2 summary: every region, dE (CIEDE2000 of the region mean), pass <= 6", "",
             f"- captures compared: {captures} (EN + TR), regions: {total}, within 6: {passed} ({100 * passed / max(1, total):.1f} %)",
             "- by kind: " + ", ".join(f"{k} {by_kind_pass[k]}/{by_kind[k]}" for k in sorted(by_kind)),
             f"- over 6: {len(over)} = findings {sum(1 for o in over if o[2] and o[2]['type'] == 'finding')}, "
             f"explained exceptions {sum(1 for o in over if o[2] and o[2]['type'] == 'exception')}, unannotated {len(unannotated)}",
             f"- missing captures: {missing or 'none'}", "",
             "## Regions over 6 by finding", ""]
    for f in sorted(per_finding):
        lines.append(f"- **{f}** ({len(per_finding[f])}): " + "; ".join(per_finding[f]))
    lines += ["", "## Explained exceptions", "", "| capture | region | dE | why |", "|---|---|---|---|"]
    for key, row, r in over:
        if r and r["type"] == "exception":
            lines.append(f"| {key} | {row['name']} | {row['dE']:.1f} | {r['why']} |")
    if unannotated:
        lines += ["", "## UNANNOTATED (fix before sign-off)", ""] + [f"- {k} {n} {d:.1f}" for k, n, d in unannotated]
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))
    if unannotated:
        print("UNANNOTATED:", unannotated)
    sys.exit(1 if unannotated else 0)


if __name__ == "__main__":
    main()
