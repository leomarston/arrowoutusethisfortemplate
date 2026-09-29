#!/usr/bin/env python3
"""tools/strip_bundle_json.py — F3-B (2026-09-29): bundle hygiene for the art JSON the app ships.

    strip_bundle_json.py strip <dir>...    rewrite every *.json under the dirs WITHOUT the non-runtime keys (in place)
    strip_bundle_json.py scan  <dir>...    list every non-runtime key left; exit 1 when there is one

tools/sync_art.sh copies the puppets' `<id>_rig/rig.json`, the `char_*.json` placement sidecars and
`char_loading_layout.json` from art/out into <app>/Art, and calls `strip` on the copies right after, so art/out keeps
its notes and the .app does not. tools/bench/release_gates.sh gate 7 imports `non_runtime_keys` (the same rule) to fail
a Release bundle that still carries one.

A NON-RUNTIME key, at any depth of an object:
  - the art pipeline's notes: "note", "notes", "baked" (how the default layers were baked), "proof" (the art lane's
    recomposition error numbers), "replaces" (char_loading_layout.json: the retired figure id each slot replaced —
    those ids name the reference's characters);
  - a "_"-prefixed comment key ("_about", "_from", "_sources" …);
  - a capture-provenance key ("shot", "capture", "reader", "anomalies", "occlusion_inferred", "source", "metrics",
    "research", "provenance").
None of them is read by the app (App/Shell/Home/PuppetRig.swift reads character / frame_pt / full / placement_pt /
layers[name, file, z, rect_pt, pivots_pt, group, default, overlay, parent] / groups; App/Shell/LoadingScreen.swift reads
characters[file, frame_pt, x, y, z]; the char_*.json sidecars are read by no code). The rewrite keeps key order and
values (floats round-trip exactly through Python's json), UTF-8, compact separators.
"""
import json
import os
import sys

NOTE_KEYS = {"note", "notes", "baked", "proof", "replaces"}
PROVENANCE_KEYS = {"shot", "capture", "reader", "anomalies", "occlusion_inferred", "source", "metrics", "research",
                   "provenance"}


def is_non_runtime(key):
    return key in NOTE_KEYS or key in PROVENANCE_KEYS or key.startswith("_")


def non_runtime_keys(obj, path=""):
    """Every (json-path, key) of a non-runtime key in obj, at any depth."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s/%s" % (path, k)
            if is_non_runtime(k):
                out.append((p, k))
            else:
                out.extend(non_runtime_keys(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(non_runtime_keys(v, "%s[%d]" % (path, i)))
    return out


def stripped(obj):
    if isinstance(obj, dict):
        return {k: stripped(v) for k, v in obj.items() if not is_non_runtime(k)}
    if isinstance(obj, list):
        return [stripped(v) for v in obj]
    return obj


def json_files(dirs):
    for d in dirs:
        if os.path.isfile(d) and d.endswith(".json"):
            yield d
            continue
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.endswith(".json"):
                    yield os.path.join(root, f)


def main(argv):
    if len(argv) < 3 or argv[1] not in ("strip", "scan"):
        sys.stderr.write(__doc__)
        return 64
    mode, dirs = argv[1], argv[2:]
    files = list(json_files(dirs))
    changed = removed = left = 0
    for f in files:
        with open(f, "rb") as fh:
            obj = json.loads(fh.read().decode("utf-8"))
        keys = non_runtime_keys(obj)
        if mode == "scan":
            for p, _ in keys:
                print("%s: %s" % (f, p))
            left += len(keys)
            continue
        if not keys:
            continue
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(stripped(obj), fh, ensure_ascii=False, separators=(",", ":"))
        changed += 1
        removed += len(keys)
        with open(f, "rb") as fh:                         # belt and braces: the rewrite parses and carries none
            again = non_runtime_keys(json.loads(fh.read().decode("utf-8")))
        if again:
            sys.stderr.write("strip_bundle_json.py: %s still carries %s\n" % (f, again))
            return 1
    if mode == "scan":
        print("strip_bundle_json.py scan: %d JSON file(s), %d non-runtime key(s)" % (len(files), left))
        return 1 if left else 0
    print("strip_bundle_json.py: %d JSON file(s), %d rewritten, %d non-runtime key(s) removed" % (len(files), changed, removed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
