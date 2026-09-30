#!/usr/bin/env python3
"""Wire one app up for Meta (Facebook) install-attribution campaigns.

Opt-in, per app, on purpose. Linking the SDK changes the app's privacy label, adds an App
Tracking Transparency prompt, and makes several sentences in the store description false. An
app you are not advertising should not pay that price, so this is never applied wholesale.

What it does:
  1. adds the facebook-ios-sdk Swift package and the FacebookCore product
  2. writes every Meta Info.plist key — including the ARRAY keys, via xcodegen's `info:`
     block, because `INFOPLIST_KEY_*` has no array form and Xcode silently discards them
  3. writes the app id + client token into App/Config.swift
  4. rewrites PrivacyInfo.xcprivacy to declare tracking honestly
  5. rewrites fastlane/metadata/app_privacy_details.json to match
  6. prints the store-description sentences that are now false and must be rewritten

Usage:
  python3 scripts/meta_sdk.py --slug procam --app-id 123456789012345 \\
      --client-token abc123... [--dry-run]
  python3 scripts/meta_sdk.py --slug procam --check     # report status, change nothing
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Meta's SKAdNetwork identifiers. Apple only credits an install to a network listed here, so
# a missing entry means installs are simply never attributed and the campaign looks dead.
# VERIFY against Meta's current published list before a first launch — networks are added
# over time and this list is a snapshot, not an API read.
SKADNETWORK_IDS = ["v9wttpbfk9.skadnetwork", "n38lu8286q.skadnetwork"]

# Apple's guidance is "short and specific", and the alert truncates a long string. This names
# Meta, says what is shared, and describes rather than instructs ("Allow tracking so we can…"
# reads as coaching the user, which reviewers dislike). 148 characters.
# Templated on the app's own display name. It was hardcoded to "FreeUp", so wiring any other
# app put a STRANGER'S app name in the system permission dialog — the one alert a user reads
# most carefully. "{app}" is filled from Config.appName.
ATT_PURPOSE_TEMPLATE = ("{app} shares which advert brought you here with Meta, so we can keep "
                        "showing it to people like you. Nothing you measure or capture is ever "
                        "shared. Saying no changes nothing.")


def att_purpose(d):
    """The ATT string, in this app's own name."""
    cfg = (d / "App" / "Config.swift").read_text()
    m = re.search(r'appName\s*=\s*"([^"]+)"', cfg)
    return ATT_PURPOSE_TEMPLATE.format(app=m.group(1) if m else "This app")


def die(msg):
    sys.exit(f"!! {msg}")


def app_dir(slug):
    d = ROOT / "apps" / slug
    if not d.exists():
        die(f"no such app: {d}")
    return d


# ---------------------------------------------------------------- project.yml

def patch_project(d, app_id, token, dry):
    """Add the SPM package, the FacebookCore product, and every Meta plist key.

    The array-valued keys (CFBundleURLTypes, SKAdNetworkItems, LSApplicationQueriesSchemes)
    are the whole reason this goes through xcodegen's `info:` block. Written as
    INFOPLIST_KEY_* they are dropped without a warning and the failure only shows up as
    "installs are never attributed", weeks later, with no error anywhere.
    """
    p = d / "project.yml"
    s = p.read_text()

    if "facebook-ios-sdk" in s:
        print("  = package already present")
    else:
        anchor = "packages:\n"
        if anchor not in s:
            die("project.yml has no `packages:` block to extend")
        s = s.replace(anchor,
                      "packages:\n"
                      "  FacebookSDK:\n"
                      "    url: https://github.com/facebook/facebook-ios-sdk\n"
                      "    from: 17.0.0\n", 1)
        print("  + facebook-ios-sdk package")

    if "product: FacebookCore" in s:
        print("  = FacebookCore dependency already present")
    else:
        m = re.search(r"( +)- package: RevenueCat\n +product: RevenueCatUI\n", s)
        if not m:
            die("could not find the RevenueCat dependency block to append after")
        indent = m.group(1)
        s = s[:m.end()] + f"{indent}- package: FacebookSDK\n{indent}  product: FacebookCore\n" + s[m.end():]
        print("  + FacebookCore dependency")

    # The plist keys. Merge into an existing `info:` block rather than replacing it — several
    # apps already carry one for UIBackgroundModes or CADisableMinimumFrameDurationOnPhone.
    url_types = (f"        CFBundleURLTypes:\n"
                 f"          - CFBundleURLSchemes: [fb{app_id}]\n")
    schemes = "        LSApplicationQueriesSchemes: [fbapi, fb-messenger-share-api]\n"
    skad = "        SKAdNetworkItems:\n" + "".join(
        f"          - SKAdNetworkIdentifier: {i}\n" for i in SKADNETWORK_IDS)
    meta_keys = (f"        FacebookAppID: \"{app_id}\"\n"
                 f"        FacebookClientToken: \"{token}\"\n"
                 f"        FacebookDisplayName: $(PRODUCT_NAME)\n"
                 f"        FacebookAutoLogAppEventsEnabled: true\n"
                 f"        FacebookAdvertiserIDCollectionEnabled: false\n"
                 + schemes + url_types + skad)

    if "FacebookAppID" in s:
        s = re.sub(r'FacebookAppID: "[^"]*"', f'FacebookAppID: "{app_id}"', s)
        # Match the quoted form AND a stale unquoted $(BUILD_SETTING), which an earlier
        # version of this script wrote and which resolves to an EMPTY token in the shipped
        # plist — the SDK then initialises without credentials and logs nothing.
        s = re.sub(r'FacebookClientToken: (?:"[^"]*"|\$\([^)]*\))',
                   f'FacebookClientToken: "{token}"', s)
        s = re.sub(r'CFBundleURLSchemes: \[fb\d*\]', f'CFBundleURLSchemes: [fb{app_id}]', s)
        print("  = Info.plist keys already present (ids refreshed)")
    else:
        m = re.search(r"( +)info:\n +path: [^\n]+\n +properties:\n", s)
        if m:
            s = s[:m.end()] + meta_keys + s[m.end():]
            print("  + Meta keys merged into the existing info: block")
        else:
            m = re.search(r"( +)sources:\n +- path: App\n", s)
            if not m:
                die("could not find the target's `sources:` block")
            block = (f"{m.group(1)}info:\n"
                     f"{m.group(1)}  path: App/Info.plist\n"
                     f"{m.group(1)}  properties:\n" + meta_keys)
            s = s[:m.end()] + block + s[m.end():]
            print("  + info: block created with the Meta keys")

    # ATT purpose string. Without it iOS silently refuses to show the prompt, tracking is
    # never authorised, and installs are never attributed — with nothing in the build log to
    # say so. It has to land wherever THIS app keeps its plist keys, which differs per app:
    # apps that need an array key (NSBonjourServices, UIBackgroundModes, SKAdNetworkItems)
    # carry a real `info:` block, because INFOPLIST_KEY_* cannot express arrays at all.
    if "NSUserTrackingUsageDescription" in s:
        print("  = NSUserTrackingUsageDescription already present")
    else:
        m = re.search(r"( +)info:\n +path: [^\n]+\n +properties:\n", s)
        if m:
            # Inside the info: block, at the same indent as the keys just merged there.
            s = (s[:m.end()]
                 + f'        NSUserTrackingUsageDescription: "{att_purpose(d)}"\n'
                 + s[m.end():])
            print("  + NSUserTrackingUsageDescription (info: block)")
        else:
            m = re.search(r"( +)INFOPLIST_KEY_ITSAppUsesNonExemptEncryption: (?:NO|false)\n", s)
            if not m:
                die("could not find an anchor for the tracking usage description")
            s = (s[:m.end()]
                 + f'{m.group(1)}INFOPLIST_KEY_NSUserTrackingUsageDescription: "{att_purpose(d)}"\n'
                 + s[m.end():])
            print("  + NSUserTrackingUsageDescription (INFOPLIST_KEY_)")

    if not dry:
        p.write_text(s)
    return s


# ---------------------------------------------------------------- Config.swift

def patch_config(d, app_id, token, dry):
    p = d / "App" / "Config.swift"
    s = p.read_text()
    if "metaAppID" in s:
        s = re.sub(r'static let metaAppID = "[^"]*"', f'static let metaAppID = "{app_id}"', s)
        s = re.sub(r'static let metaClientToken = "[^"]*"',
                   f'static let metaClientToken = "{token}"', s)
        print("  = Config.swift updated in place")
    else:
        anchor = "    static let privacyURL"
        if anchor not in s:
            die("Config.swift has no privacyURL anchor")
        block = (
            "    // Meta install attribution. Empty or a `__` placeholder means the SDK never\n"
            "    // initialises and nothing is collected — see MetaAds.isConfigured.\n"
            f'    static let metaAppID = "{app_id}"\n'
            f'    static let metaClientToken = "{token}"\n\n')
        s = s.replace(anchor, block + anchor, 1)
        print("  + Config.swift meta credentials")
    if not dry:
        p.write_text(s)


# ---------------------------------------------------------------- privacy

TRACKING_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- This app is advertised on Meta, so it links the Facebook SDK and this manifest
         declares tracking. An app in this factory that is NOT advertised does not ship the
         SDK and keeps NSPrivacyTracking false. -->
    <key>NSPrivacyTracking</key>
    <true/>
    <!-- MUST list at least one domain. Apple validates this pair: NSPrivacyTracking=true with
         an EMPTY NSPrivacyTrackingDomains is ITMS-91064 "invalid tracking information", and the
         build is failed as INVALID_BINARY with no readable reason anywhere in the API. Leaving it
         empty on the theory that the SDK's own manifest covers it cost three builds.

         ep1.facebook.com is exactly what FBSDKCoreKit declares in its bundled manifest, so naming
         it here changes no runtime behaviour — that domain is already subject to Apple's ATT block
         whatever we say. What must NOT go here is graph.facebook.com or www.facebook.com: those
         carry the SDK's non-tracking traffic too, and listing them makes iOS block the SDK
         outright for everyone who declines tracking. -->
    <key>NSPrivacyTrackingDomains</key>
    <array>
        <string>ep1.facebook.com</string>
    </array>
    <key>NSPrivacyCollectedDataTypes</key>
    <array>
        <dict>
            <!-- Purchase history stops being a private app-functionality signal the moment
                 logSubscription() sends the amount to Meta for campaign optimisation: it is
                 then linked to a profile and used to target advertising. -->
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypePurchaseHistory</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <true/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <true/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
                <string>NSPrivacyCollectedDataTypePurposeThirdPartyAdvertising</string>
                <string>NSPrivacyCollectedDataTypePurposeAnalytics</string>
            </array>
        </dict>
        <dict>
            <!-- Linked TRUE, matching FBSDKCoreKit's own manifest. Meta joins the IDFA to a
                 profile; declaring it unlinked while the SDK declares it linked is exactly the
                 kind of contradiction that draws an ITMS-91xxx notice. -->
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypeDeviceID</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <true/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <true/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeThirdPartyAdvertising</string>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
                <string>NSPrivacyCollectedDataTypePurposeAnalytics</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypeProductInteraction</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <true/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <true/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeThirdPartyAdvertising</string>
                <string>NSPrivacyCollectedDataTypePurposeAnalytics</string>
            </array>
        </dict>
    </array>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
"""

# The App Store label and PrivacyInfo.xcprivacy are checked against each other; a data type
# that is Linked in one and not the other is what produces an ITMS-91xxx notice or a 5.1.2
# rejection. These entries mirror TRACKING_MANIFEST above one for one.
# Only DATA_LINKED_TO_YOU / DATA_NOT_LINKED_TO_YOU / DATA_USED_TO_TRACK_YOU / DATA_NOT_COLLECTED
# are accepted by Spaceship — verified in the installed fastlane.
ASC_PRIVACY = [
    {"category": "PURCHASE_HISTORY",
     "purposes": ["APP_FUNCTIONALITY", "THIRD_PARTY_ADVERTISING", "ANALYTICS"],
     "data_protections": ["DATA_LINKED_TO_YOU", "DATA_USED_TO_TRACK_YOU"]},
    {"category": "DEVICE_ID",
     "purposes": ["THIRD_PARTY_ADVERTISING", "APP_FUNCTIONALITY", "ANALYTICS"],
     "data_protections": ["DATA_LINKED_TO_YOU", "DATA_USED_TO_TRACK_YOU"]},
    {"category": "PRODUCT_INTERACTION",
     "purposes": ["THIRD_PARTY_ADVERTISING", "ANALYTICS"],
     "data_protections": ["DATA_LINKED_TO_YOU", "DATA_USED_TO_TRACK_YOU"]},
    # Declared by FBSDKCoreKit's own manifest, so the label has to cover them too.
    {"category": "CRASH_DATA", "purposes": ["APP_FUNCTIONALITY"],
     "data_protections": ["DATA_NOT_LINKED_TO_YOU"]},
]


def patch_privacy(d, dry):
    if not dry:
        (d / "App" / "PrivacyInfo.xcprivacy").write_text(TRACKING_MANIFEST)
        (d / "fastlane" / "metadata" / "app_privacy_details.json").write_text(
            json.dumps(ASC_PRIVACY, indent=2) + "\n")
    print("  + PrivacyInfo.xcprivacy declares tracking")
    print("  + app_privacy_details.json declares DEVICE_ID + PRODUCT_INTERACTION as tracking")


# ---------------------------------------------------------------- copy audit

# Sentences that become false the moment the SDK ships. These are in the live listing in every
# shipped locale, and leaving them is both a 2.3.1 metadata problem and a lie to the reader.
#
# Matching English substrings ONLY finds en-US. A previous version of this script did exactly
# that and cheerfully reported "1 locales" for an app whose other nine descriptions carried the
# same sentence translated — "keine Analyse, kein Tracking", "解析もトラッキングもありません",
# "没有分析，没有追踪". The operator was told nine locales were clean when none of them were.
#
# So: the English list locates the claim in the SOURCE locale, and every other locale is then
# reported as needing the same rewrite. A locale is never called clean on the strength of a
# failed English substring match.
# Claims about DATA. Every one of these is made false by an attribution SDK, because the SDK
# exists to send data off the device.
FALSE_CLAIMS = [
    "no analytics", "no tracking", "nothing is uploaded", "never uploaded",
    "no account and no analytics", "nothing leaves your phone",
    "fully offline", "no network", "third-party",
]

# Claims about FUNCTION, which an attribution SDK does NOT break. A detector whose sensing
# runs on-device still works with the radio off; the SDK simply queues its events. Flagging
# these as false cost a true, useful sentence on the listing before this distinction was
# drawn, so they are reported separately and only as something to re-read.
FUNCTION_CLAIMS = ["airplane mode", "works offline"]

# The store listing is not the only place these promises are made. The in-app strings are worse,
# because a reviewer opens the app; and the review notes are read first of all.
IN_APP_GLOBS = ["App/Resources/*.lproj/Localizable.strings", "design/strings_en.json"]
NOTES_GLOB = "fastlane/metadata/review_information/notes.txt"


def _flat(text):
    """Collapse whitespace before matching.

    Store descriptions and reviewer notes are hard-wrapped, so a claim like "nothing is uploaded"
    is routinely split across a line break and a raw substring search walks straight past it. That
    is exactly how a blanket claim survived a clean audit in the reviewer notes.
    """
    return " ".join(text.lower().split())


def audit_copy(d):
    """Returns {surface: {locale: [claims]}} — store, in-app and reviewer notes."""
    meta = d / "fastlane" / "metadata"
    out = {"store": {}, "in-app": {}, "notes": {}}

    # 1. store descriptions. Find the claim in en-US, then flag EVERY locale that ships.
    source_hits = set()
    en = meta / "en-US" / "description.txt"
    if en.exists():
        text = _flat(en.read_text(errors="ignore"))
        source_hits = {c for c in FALSE_CLAIMS if c in text}
    for f in sorted(meta.glob("*/description.txt")) + sorted(meta.glob("*/promotional_text.txt")):
        loc = f.parent.name
        text = _flat(f.read_text(errors="ignore"))
        found = {c for c in FALSE_CLAIMS if c in text}
        # A non-English locale carries the translated claim even when no English substring hits.
        if source_hits and f.name == "description.txt":
            found |= {f"(translated) {c}" for c in source_hits} if not found else set()
        if found:
            out["store"].setdefault(loc, set()).update(found)

    # 2. in-app copy, same logic against the English source of truth.
    en_json = d / "design" / "strings_en.json"
    if en_json.exists():
        blob = _flat(en_json.read_text(errors="ignore"))
        in_app_hits = {c for c in FALSE_CLAIMS if c in blob}
        if in_app_hits:
            for lproj in sorted((d / "App" / "Resources").glob("*.lproj")):
                out["in-app"][lproj.name.replace(".lproj", "")] = set(in_app_hits)

    # 3. reviewer notes.
    notes = d / NOTES_GLOB
    if notes.exists():
        text = _flat(notes.read_text(errors="ignore"))
        found = {c for c in FALSE_CLAIMS if c in text}
        if found:
            out["notes"]["review_information"] = found

    return {k: v for k, v in out.items() if v}


def report_copy(hits):
    """Prints the audit and returns True when something must be rewritten."""
    if not hits:
        print("  = no false privacy claims found in store, in-app or reviewer copy")
        return False
    for surface, locales in hits.items():
        total = len(locales)
        print(f"  !! {surface}: {total} locale(s) assert something the SDK makes false")
        for loc in sorted(locales):
            print(f"       {loc}: {sorted(locales[loc])}")
    return True

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--app-id", help="Meta app ID from developers.facebook.com")
    ap.add_argument("--client-token", help="Client token from the same app's Settings > Advanced")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="report status only")
    args = ap.parse_args()

    d = app_dir(args.slug)

    if args.check:
        s = (d / "project.yml").read_text()
        print(f"{args.slug}: SDK linked = {'facebook-ios-sdk' in s}")
        report_copy(audit_copy(d))
        return

    if not args.app_id or not args.client_token:
        die("--app-id and --client-token are required (get them from developers.facebook.com "
            "> your app > Settings > Basic, and Settings > Advanced > Client token)")
    if not args.app_id.isdigit():
        die("--app-id should be the numeric Meta app ID")

    print(f"Meta SDK: {args.slug}" + ("  [DRY RUN]" if args.dry_run else ""))
    patch_project(d, args.app_id, args.client_token, args.dry_run)
    patch_config(d, args.app_id, args.client_token, args.dry_run)
    patch_privacy(d, args.dry_run)

    print("\n-- copy that the SDK has just made false ------------------------------------")
    dirty = report_copy(audit_copy(d))
    if dirty:
        print("   The app now collects a device identifier for advertising. Any sentence "
              "promising no tracking, no analytics or offline-only operation is false, in "
              "EVERY language it ships in.")

    print("""
-- what this script CANNOT do for you ------------------------------------------
  1. THE PRIVACY POLICY. Config.privacyURL points at a page shared by every app in
     this factory, and that page says "no advertising SDKs, no analytics SDKs, no
     third-party tracking". It is now false for THIS app and still true for the
     others, so it cannot be edited in place — publish a separate page and point
     this app at it.
  2. THE APP STORE PRIVACY LABEL. app_privacy_details.json has been rewritten, but
     nothing uploads it: data usages are not in the public ASC API, so it needs
     `upload_app_privacy_details_to_app_store` with an Apple ID session, or a
     human in App Store Connect. A binary that shows an ATT prompt while the live
     label says "not used to track you" is a 5.1.2 rejection.
  3. THE COPY ABOVE. Rewrite it, then re-translate it.

-- then ------------------------------------------------------------------------
  xcodegen generate && build && verify the SDK is actually linked (a build with no
  FacebookCore silently compiles every MetaAds call to a no-op).""")

    if dirty:
        sys.exit(1)


if __name__ == "__main__":
    main()
