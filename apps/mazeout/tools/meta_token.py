#!/usr/bin/env python3
"""META (OWNER 2026-09-29 19:33): the Meta client token, from the factory .env into the BUILT Info.plist — and nowhere else.

The token is read ONLY from the factory's .env (key META_CLIENT_TOKEN; `factory_env()`: PC_FACTORY_ENV, else the first
ancestor holding .env + apps/ — the same file from the main tree and from build/owner-phone.sh's snapshot). It is never written
to a tracked file, never becomes a build setting (Xcode exports every build setting into every script phase's environment,
and a verbose build log prints those exports) and never appears in any output of this tool: it prints "present" / "absent" /
"malformed" and a fingerprint length at most.

    meta_token.py check    project.yml preBuildScripts, the target's FIRST phase. Debug: always passes (MetaAds stays in its
                           log-only mode without a token). Release / Measure: FAILS the build at once unless the .env holds a
                           well-formed token (32 lowercase hex characters) — a store build can never ship an empty token.
                           PC_META_VERIFICATION_BUILD=1 (environment) lets an INTERNAL Release / Measure build through with an
                           EMPTY token (FIX-3's archive-style path proof, the release-gates dry runs): it warns, and the
                           fastlane lanes refuse to build or upload with that variable set (fastlane/Fastfile meta_token_ready!).
    meta_token.py inject   project.yml postBuildScripts, ordered after ProcessInfoPlistFile by its input file
                           $(TARGET_BUILD_DIR)/$(INFOPLIST_PATH): writes FacebookClientToken into that built plist (keeping its
                           binary / XML format) when the .env holds a token; otherwise leaves it empty (Debug; verification).
    meta_token.py status   the state of the .env key, for a person (never the value).

Environment read from Xcode: CONFIGURATION, ACTION, SRCROOT, TARGET_BUILD_DIR, INFOPLIST_PATH.
"""
import os
import plistlib
import re
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def factory_env(app=APP, environ=os.environ):
    """The factory .env. RFIX 2026-09-29 (VERIFY F1): the app folder's ../../.env held only for the main tree; a SNAPSHOT
    (build/owner-phone.sh builds apps/mazeout/build/owner-phone/tree) resolved to apps/mazeout/build/.env, which never exists,
    so every phone Release / Measure build stopped at the token gate. Now: PC_FACTORY_ENV (an absolute path, exported by
    owner-phone.sh) if set, else the FIRST ancestor of the app folder that holds both a .env file and an apps/ folder (the
    factory root, from the main tree and from any snapshot inside it). The token itself is never copied anywhere."""
    override = environ.get("PC_FACTORY_ENV", "").strip()
    if override:
        return os.path.abspath(override)
    d = os.path.abspath(app)
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(os.path.join(app, "..", "..", ".env"))    # no factory above: the old spelling (absent)
        d = parent
        if os.path.isfile(os.path.join(d, ".env")) and os.path.isdir(os.path.join(d, "apps")):
            return os.path.join(d, ".env")


ENV_FILE = factory_env()
KEY = "META_CLIENT_TOKEN"
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
STORE_CONFIGS = {"Release", "Measure"}


def read_token(path=None):
    """-> (state, token): state is 'present', 'absent' (no file / no key / empty) or 'malformed'."""
    path = path or ENV_FILE
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return "absent", None
    value = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("export "):
            s = s[len("export "):].lstrip()
        if not s.startswith(KEY + "="):
            continue
        v = s[len(KEY) + 1:].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1].strip()
        value = v                                   # the last assignment wins, as in a shell
    if not value:
        return "absent", None
    if not TOKEN_RE.match(value):
        return "malformed", None
    return "present", value


def err(msg):
    # Xcode shows "error: ..." lines in the issue navigator and fails the phase on a non-zero exit
    print("error: " + msg, file=sys.stderr)


def check():
    config = os.environ.get("CONFIGURATION", "")
    state, _ = read_token()
    if config not in STORE_CONFIGS:
        print(f"meta_token: {config or 'unknown'} configuration: token {state} (not required; MetaAds is log-only in DEBUG)")
        return 0
    if state == "present":
        print(f"meta_token: {config}: META_CLIENT_TOKEN present in the factory .env (the built Info.plist gets it)")
        return 0
    if os.environ.get("PC_META_VERIFICATION_BUILD") == "1":
        print(f"warning: META VERIFICATION BUILD ({config}): META_CLIENT_TOKEN {state}; FacebookClientToken stays EMPTY and "
              "MetaAds stays off. This product must never reach App Store Connect (the fastlane lanes refuse it).")
        return 0
    why = "has no META_CLIENT_TOKEN" if state == "absent" else "has a META_CLIENT_TOKEN that is not 32 lowercase hex characters"
    err(f"{config} build stopped: the factory .env ({ENV_FILE}) {why}. A store build must carry the Meta client token "
        "(developers.facebook.com > Arrow Out > App settings > Advanced > Client token). Add the line "
        "META_CLIENT_TOKEN=<token> to the factory .env and build again. Internal verification builds only: "
        "PC_META_VERIFICATION_BUILD=1 (never uploaded).")
    return 1


def inject():
    built = os.path.join(os.environ.get("TARGET_BUILD_DIR", ""), os.environ.get("INFOPLIST_PATH", ""))
    if not os.environ.get("TARGET_BUILD_DIR") or not os.path.isfile(built):
        err(f"meta_token inject: no built Info.plist at {built!r} (TARGET_BUILD_DIR / INFOPLIST_PATH)")
        return 1
    state, token = read_token()
    with open(built, "rb") as f:
        raw = f.read()
    fmt = plistlib.FMT_BINARY if raw.startswith(b"bplist") else plistlib.FMT_XML
    info = plistlib.loads(raw)
    if "FacebookAppID" not in info:
        err("meta_token inject: the built Info.plist has no FacebookAppID (project.yml info: block not generated?)")
        return 1
    config = os.environ.get("CONFIGURATION", "")
    if state != "present":
        if config in STORE_CONFIGS and os.environ.get("PC_META_VERIFICATION_BUILD") != "1":
            err(f"meta_token inject: {config} build without META_CLIENT_TOKEN (the check phase should have stopped it)")
            return 1
        if info.get("FacebookClientToken"):
            info["FacebookClientToken"] = ""       # a stale token from an earlier build of this product never survives
            with open(built, "wb") as f:
                plistlib.dump(info, f, fmt=fmt)
        print(f"meta_token: {config}: token {state}; FacebookClientToken left empty in the built Info.plist")
        return 0
    if info.get("FacebookClientToken") != token:
        info["FacebookClientToken"] = token
        tmp = built + ".meta.tmp"
        with open(tmp, "wb") as f:
            plistlib.dump(info, f, fmt=fmt)
        os.replace(tmp, built)
    print(f"meta_token: {config}: FacebookClientToken written into the built Info.plist ({'binary' if fmt == plistlib.FMT_BINARY else 'xml'})")
    return 0


def status():
    state, _ = read_token()
    print(f"META_CLIENT_TOKEN in {ENV_FILE}: {state}")
    return 0 if state == "present" else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"check": check, "inject": inject, "status": status}.get(cmd, status)())
