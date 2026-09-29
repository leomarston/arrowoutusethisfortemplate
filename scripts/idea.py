#!/usr/bin/env python3
"""ideas.yaml kuyruk yardımcısı.
  idea.py next                 -> ilk 'pending' fikrin slug'ını yazar
  idea.py get <slug>           -> fikri KEY=VALUE satırları olarak yazar (shell eval için)
  idea.py json <slug>          -> fikri JSON olarak yazar
  idea.py mark <slug> <status> -> status günceller (pending/in_progress/submitted/blocked)
"""
import sys, json, shlex
from pathlib import Path

import yaml  # pip: pyyaml

ROOT = Path(__file__).resolve().parent.parent
IDEAS = ROOT / "ideas.yaml"


def load():
    return yaml.safe_load(IDEAS.read_text()) or []


def save(data):
    IDEAS.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def find(data, slug):
    for it in data:
        if it.get("slug") == slug:
            return it
    sys.exit(f"idea not found: {slug}")


def main():
    cmd = sys.argv[1]
    data = load()
    if cmd == "next":
        for it in data:
            if it.get("status", "pending") == "pending":
                print(it["slug"])
                return
        sys.exit("no pending ideas")
    elif cmd == "get":
        it = find(data, sys.argv[2])
        flat = {
            "SLUG": it["slug"],
            "APP_NAME": it["name"],
            # App Store listing name (leads with the seed keyword). Falls back to the
            # display name. Used for `fastlane create_app` + name.txt — NOT the short
            # on-device name. See memory [[app-naming-keyword-first]].
            "STORE_NAME": it.get("store_name", it["name"]),
            "APP_NAME_NOSPACE": "".join(w[:1].upper() + w[1:] for w in it["name"].split()),
            "CATEGORY": it.get("category", "UTILITIES"),
            "ACCENT_HEX": it.get("accent", "#4F46E5"),
            "MONTHLY_USD": str(it.get("pricing", {}).get("monthly_usd", 4.99)),
            "YEARLY_USD": str(it.get("pricing", {}).get("yearly_usd", 29.99)),
        }
        for k, v in flat.items():
            print(f"{k}={shlex.quote(str(v))}")
    elif cmd == "json":
        print(json.dumps(find(data, sys.argv[2]), ensure_ascii=False, indent=2))
    elif cmd == "mark":
        it = find(data, sys.argv[2])
        it["status"] = sys.argv[3]
        save(data)
        print(f"{it['slug']} -> {sys.argv[3]}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
