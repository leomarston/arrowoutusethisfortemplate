#!/usr/bin/env python3
"""Push per-locale App Store keywords straight to ASC, bypassing fastlane.

The keywords field is user-owned: `deliver` would blow away anything edited by hand in
ASC on every metadata upload, so no app in this repo keeps a `keywords.txt` under
fastlane/metadata. The researched values live in `apps/<slug>/design/keywords.json`
instead and are PATCHed onto the editable version's localizations from here.

A first version cannot be submitted with an empty keywords field, so this has to run
before scripts/asc_submit.py.

Usage:
  python3 scripts/asc_keywords.py --slug strobelight            # write
  python3 scripts/asc_keywords.py --slug strobelight --dry-run  # show the diff only
  python3 scripts/asc_keywords.py --slug strobelight --pull     # read ASC back into JSON
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asc_submit import API, env, make_token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
            "METADATA_REJECTED", "INVALID_BINARY", "WAITING_FOR_REVIEW"}
LIMIT = 100


def app_id_for(slug):
    """Read the numeric app id from the Appfile fastlane already keeps in sync."""
    appfile = ROOT / "apps" / slug / "fastlane" / "Appfile"
    bundle = None
    for line in appfile.read_text().splitlines():
        if "app_identifier" in line:
            bundle = line.split('"')[1]
    if not bundle:
        sys.exit(f"no app_identifier in {appfile}")
    return bundle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pull", action="store_true",
                    help="overwrite the local JSON with what ASC currently has")
    args = ap.parse_args()

    kwfile = ROOT / "apps" / args.slug / "design" / "keywords.json"
    if not kwfile.exists():
        sys.exit(f"missing {kwfile}")
    wanted = json.loads(kwfile.read_text())

    over = {k: len(v) for k, v in wanted.items() if len(v) > LIMIT}
    if over:
        sys.exit(f"keywords over {LIMIT} chars: {over}")

    api = API(make_token(env()))
    bundle = app_id_for(args.slug)
    st, apps = api("GET", f"/v1/apps?filter[bundleId]={bundle}")
    if st != 200 or not apps.get("data"):
        sys.exit(f"app not found for {bundle} (HTTP {st})")
    app_id = apps["data"][0]["id"]

    st, versions = api("GET", f"/v1/apps/{app_id}/appStoreVersions?limit=10")
    version = next((v for v in versions.get("data", [])
                    if v["attributes"]["appStoreState"] in EDITABLE), None)
    if not version:
        sys.exit("no editable appStoreVersion — nothing to write keywords to")
    vid = version["id"]
    print(f"{args.slug}: app {app_id} version {version['attributes']['versionString']} "
          f"({version['attributes']['appStoreState']})")

    st, locs = api("GET", f"/v1/appStoreVersions/{vid}/appStoreVersionLocalizations?limit=200")
    on_asc = {l["attributes"]["locale"]: l for l in locs.get("data", [])}

    if args.pull:
        pulled = {loc: (l["attributes"].get("keywords") or "") for loc, l in on_asc.items()}
        kwfile.write_text(json.dumps(dict(sorted(pulled.items())), ensure_ascii=False, indent=1))
        print(f"pulled {len(pulled)} locales from ASC into {kwfile}")
        return

    wrote, same, missing = 0, 0, []
    for loc, kw in sorted(wanted.items()):
        entry = on_asc.get(loc)
        if entry is None:
            missing.append(loc)
            continue
        if (entry["attributes"].get("keywords") or "") == kw:
            same += 1
            continue
        print(f"  {loc:8} {kw}")
        if not args.dry_run:
            st, body = api("PATCH", f"/v1/appStoreVersionLocalizations/{entry['id']}",
                           {"data": {"type": "appStoreVersionLocalizations",
                                     "id": entry["id"], "attributes": {"keywords": kw}}})
            if st not in (200, 201):
                print(f"    !! HTTP {st} {json.dumps(body)[:300]}")
                continue
        wrote += 1

    print(f"{'would write' if args.dry_run else 'wrote'} {wrote}, unchanged {same}, "
          f"locales not on ASC {len(missing)}")
    if missing:
        print("  not on ASC yet (upload metadata first):", " ".join(missing))


if __name__ == "__main__":
    main()
