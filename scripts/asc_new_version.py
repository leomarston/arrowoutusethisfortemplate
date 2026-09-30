#!/usr/bin/env python3
"""Open a new App Store version for an app whose current version is already live.

The submit pipeline (`asc_submit.py`) always operates on the LATEST iOS version record and
deliberately never creates one — for a first release there is always exactly one, created
with the app. For an UPDATE there is none: the live version is READY_FOR_SALE and cannot be
edited, so `deliver` has nothing to upload into and `asc_submit` would try to resubmit the
version that is already on sale.

This opens that record and, with --notes, PATCHes "What's New" on every locale of it through
the API (docs/lessons/keywords-are-user-owned.md: never ship release_notes.txt — the game
metadata tools delete those files and `meta.py audit` rejects them). Run it before uploading
the build.

Usage:
  python3 scripts/asc_new_version.py --slug mazeout --bundle com.manycode.arrowout --version 1.0.1
  python3 scripts/asc_new_version.py --slug mazeout --bundle com.manycode.arrowout --version 1.0.1 \
      --notes "Bug fixes and smoother levels." [--dry-run]
(--bundle defaults to BUNDLE_PREFIX.<slug>, which is wrong whenever the folder name differs from the product.)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asc_submit import API, env, make_token  # noqa: E402

# States that mean "there is already somewhere to put this build".
EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
            "METADATA_REJECTED", "INVALID_BINARY", "WAITING_FOR_REVIEW", "IN_REVIEW"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--bundle", help="bundle id (default BUNDLE_PREFIX.<slug>)")
    ap.add_argument("--version", required=True, help="marketing version, e.g. 1.0.2")
    ap.add_argument("--notes", help="What's New text, PATCHed on every locale of the open version")
    ap.add_argument("--dry-run", action="store_true", help="read only: report what would change")
    args = ap.parse_args()

    e = env()
    api = API(make_token(e))
    bundle = args.bundle or f'{e["BUNDLE_PREFIX"]}.{args.slug}'

    st, apps = api("GET", f"/v1/apps?filter[bundleId]={bundle}")
    if not apps.get("data"):
        sys.exit(f"!! no such app on ASC: {bundle} (pass --bundle if the folder name differs from the product)")
    app_id = apps["data"][0]["id"]

    # filter[platform]=IOS for the same reason asc_submit does it: a stray macOS version
    # record outlives every attempt to delete it and an unfiltered query can return it.
    st, vers = api("GET", f"/v1/apps/{app_id}/appStoreVersions"
                          "?filter[platform]=IOS&limit=10")
    for v in vers.get("data", []):
        a = v["attributes"]
        if a["appStoreState"] in EDITABLE:
            print(f'= version {a["versionString"]} already open ({a["appStoreState"]}) — nothing to create')
            patch_notes(api, e, v["id"], args)
            return
        if a["versionString"] == args.version:
            sys.exit(f'!! version {args.version} exists and is {a["appStoreState"]}; '
                     f"pick a higher version")

    if args.dry_run:
        print(f"[dry-run] would open version {args.version} for {bundle}"
              + (" and PATCH What's New on every locale" if args.notes else ""))
        return
    st, r = api("POST", "/v1/appStoreVersions", {"data": {
        "type": "appStoreVersions",
        "attributes": {"platform": "IOS", "versionString": args.version},
        "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})
    if st not in (200, 201):
        sys.exit(f"!! POST /v1/appStoreVersions -> {st}\n{r}")
    print(f"+ opened version {args.version} for {bundle}")
    patch_notes(api, e, r["data"]["id"], args)


def patch_notes(api, e, version_id, args):
    """What's New on every locale of the version (an update with an empty What's New is rejected at
    submit, and the field is per-locale). A fresh token per locale: the ASC JWT lives 20 minutes
    (docs/lessons/asc-token-20min-cap.md). Every PATCH is read back."""
    if not args.notes:
        return
    notes = args.notes.strip()
    st, locs = api("GET", f"/v1/appStoreVersions/{version_id}/appStoreVersionLocalizations?limit=50")
    rows = locs.get("data", [])
    if not rows:
        sys.exit(f"!! version {version_id} has no localizations to write What's New into ({st})")
    bad = []
    for loc in rows:
        name = loc["attributes"].get("locale")
        if args.dry_run:
            print(f"[dry-run] would set What's New on {name}")
            continue
        api.tok = make_token(e)
        st, _ = api("PATCH", f"/v1/appStoreVersionLocalizations/{loc['id']}", {"data": {
            "type": "appStoreVersionLocalizations", "id": loc["id"], "attributes": {"whatsNew": notes}}})
        st2, back = api("GET", f"/v1/appStoreVersionLocalizations/{loc['id']}?fields[appStoreVersionLocalizations]=whatsNew")
        if st not in (200, 201) or (back.get("data") or {}).get("attributes", {}).get("whatsNew", "").strip() != notes:
            bad.append(f"{name} ({st})")
    if bad:
        sys.exit(f"!! What's New not confirmed on: {', '.join(bad)}")
    if not args.dry_run:
        print(f"  What's New set and read back on {len(rows)} locales")


if __name__ == "__main__":
    main()
