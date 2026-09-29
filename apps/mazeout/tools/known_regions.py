#!/usr/bin/env python3
"""tools/known_regions.py: sets the Xcode project's knownRegions (A0, SPEC.md §5 item 42).

XcodeGen derives knownRegions only from the localized resources it finds (today: en + tr from Localizable.xcstrings) and
has no spec option for them, so project.yml runs this as its `options.postGenCommand` (XcodeGen runs it in the spec's
directory after every `tools/gen.sh`). The ruled 13 locales (SPEC.md §5 item 37a: en de fr es it pt-BR tr ja ko zh-Hans pl sk
sl) come from the command line, in that order, after Base; any region XcodeGen found that is not listed is kept after
them. Idempotent; touches nothing but the one `knownRegions = ( … );` block.

usage: python3 tools/known_regions.py <project.pbxproj> <region> [<region> …]
"""
import re
import sys


def quote(r: str) -> str:
    return r if re.fullmatch(r"[A-Za-z0-9_]+", r) else f'"{r}"'


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    path, wanted = sys.argv[1], sys.argv[2:]
    text = open(path, encoding="utf-8").read()
    m = re.search(r"(\n(\t+)knownRegions = \(\n)(.*?)(\n\t+\);)", text, re.S)
    if not m:
        print(f"known_regions: no knownRegions block in {path}", file=sys.stderr)
        return 1
    indent = m.group(2) + "\t"
    found = [x.strip().rstrip(",").strip('"') for x in m.group(3).split("\n") if x.strip()]
    regions = ["Base"] + [r for r in wanted if r != "Base"]
    regions += [r for r in found if r not in regions]
    body = "\n".join(f"{indent}{quote(r)}," for r in regions)
    new = text[: m.start(3)] + body + text[m.end(3):]
    if new != text:
        open(path, "w", encoding="utf-8").write(new)
    print(f"known_regions: {len(regions)} ({', '.join(regions)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
