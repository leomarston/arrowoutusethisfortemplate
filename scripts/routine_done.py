#!/usr/bin/env python3
"""Bir slug'i ROUTINEAPPS.MD'de ✅ isaretler ve Log'a satir ekler.

Kullanim: routine_done.py <slug> <outcome>
"""
import re, sys, datetime
from pathlib import Path

MD = Path(__file__).resolve().parent.parent / "ROUTINEAPPS.MD"
slug = sys.argv[1]
outcome = sys.argv[2] if len(sys.argv) > 2 else "submitted"

text = MD.read_text(encoding="utf-8")
lines = text.splitlines()
for i, line in enumerate(lines):
    if f"`{slug}`" in line and "|" in line and "✅" not in line:
        # son '⬜' sutununu ✅ yap
        lines[i] = line.rsplit("⬜", 1)[0] + "✅" + line.rsplit("⬜", 1)[1] if "⬜" in line else line
        break
# Log satiri (new()/Date.now() kullanmadan — sistem tarihi)
stamp = datetime.date.today().isoformat()
out = "\n".join(lines)
if not out.endswith("\n"):
    out += "\n"
out += f"- {stamp} · {slug} · {outcome}\n"
MD.write_text(out, encoding="utf-8")
print(f"marked {slug} ✅ ({outcome})")
