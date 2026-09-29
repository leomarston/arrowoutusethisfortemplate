#!/usr/bin/env python3
"""ROUTINEAPPS.MD'deki ilk tamamlanmamis (⬜) sirayi dondurur.

Cikti (stdout, tek satir):  slug\tseed_keyword\tstore_name
Kuyruk bittiyse cikis kodu 1.
"""
import re, sys
from pathlib import Path

MD = Path(__file__).resolve().parent.parent / "ROUTINEAPPS.MD"
row = re.compile(
    r"^\|\s*\d+\s*\|\s*(?P<kw>[^|]+?)\s*\|\s*`(?P<slug>[^`]+)`\s*\|\s*(?P<name>[^|]+?)\s*\|"
    r"[^|]*\|[^|]*\|\s*(?P<status>[^|]+?)\s*\|\s*$"
)
for line in MD.read_text(encoding="utf-8").splitlines():
    m = row.match(line)
    if m and "✅" not in m.group("status"):
        print(f"{m.group('slug')}\t{m.group('kw')}\t{m.group('name')}")
        sys.exit(0)
sys.exit(1)
