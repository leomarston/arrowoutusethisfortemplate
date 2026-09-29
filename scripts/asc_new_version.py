#!/usr/bin/env python3
"""Open a new App Store version for an app whose current version is already live.

The submit pipeline (`asc_submit.py`) always operates on the LATEST iOS version record and
deliberately never creates one — for a first release there is always exactly one, created
with the app. For an UPDATE there is none: the live version is READY_FOR_SALE and cannot be
edited, so `deliver` has nothing to upload into and `asc_submit` would try to resubmit the
version that is already on sale.

This opens that record, and nothing else. Run it before `fastlane release`.

Usage:
  python3 scripts/asc_new_version.py --slug twocam --version 1.0.2
  python3 scripts/asc_new_version.py --slug twocam --version 1.0.2 --notes "Fixes ..."
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asc_submit import API, env, make_token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# States that mean "there is already somewhere to put this build".
EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
            "METADATA_REJECTED", "INVALID_BINARY", "WAITING_FOR_REVIEW", "IN_REVIEW"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--version", required=True, help="marketing version, e.g. 1.0.2")
    ap.add_argument("--notes", help="release notes; also written to every locale's "
                                    "release_notes.txt so deliver uploads them")
    args = ap.parse_args()

    e = env()
    api = API(make_token(e))
    bundle = f'{e["BUNDLE_PREFIX"]}.{args.slug}'

    st, apps = api("GET", f"/v1/apps?filter[bundleId]={bundle}")
    if not apps.get("data"):
        sys.exit(f"!! no such app on ASC: {bundle}")
    app_id = apps["data"][0]["id"]

    # filter[platform]=IOS for the same reason asc_submit does it: a stray macOS version
    # record outlives every attempt to delete it and an unfiltered query can return it.
    st, vers = api("GET", f"/v1/apps/{app_id}/appStoreVersions"
                          "?filter[platform]=IOS&limit=10")
    existing = vers.get("data", [])
    for v in existing:
        a = v["attributes"]
        if a["appStoreState"] in EDITABLE:
            print(f'= version {a["versionString"]} already open ({a["appStoreState"]}) — '
                  f"nothing to do")
            write_notes(args)
            return
        if a["versionString"] == args.version:
            sys.exit(f'!! version {args.version} exists and is {a["appStoreState"]}; '
                     f"pick a higher version")

    st, r = api("POST", "/v1/appStoreVersions", {"data": {
        "type": "appStoreVersions",
        "attributes": {"platform": "IOS", "versionString": args.version},
        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})
    if st not in (200, 201):
        sys.exit(f"!! POST /v1/appStoreVersions -> {st}\n{r}")

    print(f"+ opened version {args.version} for {bundle}")
    write_notes(args)


def write_notes(args):
    """Put the release notes in every locale so `deliver` carries them up.

    An update with an empty What's New is rejected at submit, and the field is per-locale —
    filling only en-US leaves the other 49 empty.
    """
    if not args.notes:
        return
    meta = ROOT / "apps" / args.slug / "fastlane" / "metadata"
    n = 0
    for d in sorted(meta.iterdir()):
        if not d.is_dir() or d.name == "review_information":
            continue
        (d / "release_notes.txt").write_text(args.notes.strip() + "\n", encoding="utf-8")
        n += 1
    print(f"  release notes written to {n} locales")


if __name__ == "__main__":
    main()
