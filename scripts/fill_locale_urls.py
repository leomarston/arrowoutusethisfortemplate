#!/usr/bin/env python3
"""Give every metadata locale a support_url/privacy_url.

Apple requires supportUrl on EVERY appStoreVersionLocalization. A locale added later
(e.g. by a translation pass) inherits nothing, and the omission only surfaces at submit
as ENTITY_ERROR.ATTRIBUTE.REQUIRED, after the upload has already succeeded.

Usage: python3 scripts/fill_locale_urls.py --slug <slug>
"""
import argparse, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def env(key: str, default: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()
    support = env("SUPPORT_URL", "https://leomarston.github.io/manycode-legal/support.html")
    privacy = env("PRIVACY_URL", "https://leomarston.github.io/manycode-legal/privacy.html")
    base = ROOT / "apps" / a.slug / "fastlane" / "metadata"
    n = 0
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name == "review_information":
            continue
        for name, url in (("support_url.txt", support), ("privacy_url.txt", privacy)):
            f = d / name
            if not f.exists() or not f.read_text().strip():
                f.write_text(url)
                n += 1
    print(f"{a.slug}: wrote {n} missing url files across {len(list(base.iterdir()))} locales")


if __name__ == "__main__":
    main()
