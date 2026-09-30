#!/usr/bin/env python3
"""Release gate 8: the store bundle embeds only allowed SDKs and makes no tracking claim it cannot back.

    sdk_gate.py <Release .app>            the gate (a planted control runs first: it must FAIL on a bad bundle)
    sdk_gate.py selftest                  controls only

The template ships NO ad-serving, attribution or tracking SDK (docs/ROADMAP.md D2). A game that adds one lists its framework
names in the environment variable ALLOWED_FRAMEWORKS (space-separated, e.g. "FBSDKCoreKit FBSDKCoreKit_Basics FBAEMKit")
and follows docs/recipes/ad-attribution.md; ad-SERVING SDKs are never allowed. Checks:
  1. every embedded framework (Frameworks/*.framework, *.xcframework) is in ALLOWED_FRAMEWORKS;
  2. no ad-serving / attribution framework name anywhere in the bundle, allowed ones excepted;
  3. Info.plist has no ad-serving key and, unless attribution frameworks are allowed, no tracking keys
     (NSUserTrackingUsageDescription, FacebookAppID, SKAdNetworkItems);
  4. PrivacyInfo.xcprivacy: NSPrivacyTracking false with no tracking domains, unless an allowed SDK needs tracking.
Stdlib only; runs on macOS and Linux.
"""
import os
import plistlib
import shutil
import sys
import tempfile

AD_SERVING = ["GoogleMobileAds", "FBAudienceNetwork", "AppLovinSDK", "UnityAds", "IronSource", "VungleAds", "ChartboostSDK",
              "InMobiSDK", "MintegralAdSDK", "PangleSDK", "BUAdSDK", "AdColony", "Tapjoy", "YandexMobileAds"]
ATTRIBUTION = ["FBSDKCoreKit", "FBSDKCoreKit_Basics", "FBAEMKit", "FBSDKLoginKit", "FBSDKShareKit", "FBSDKGamingServicesKit",
               "AppsFlyerLib", "Adjust", "Branch", "Kochava", "SingularSDK", "TenjinSDK"]
AD_PLIST_KEYS = ["GADApplicationIdentifier", "AppLovinSdkKey", "UnityAdsGameId"]
TRACKING_PLIST_KEYS = ["NSUserTrackingUsageDescription", "FacebookAppID", "FacebookClientToken", "SKAdNetworkItems"]


def check(app, allowed):
    problems = []
    for root, dirs, _ in os.walk(app):
        for d in dirs:
            name, ext = os.path.splitext(d)
            if ext in (".framework", ".xcframework"):
                if name not in allowed:
                    problems.append(f"embedded framework not in ALLOWED_FRAMEWORKS: {os.path.relpath(os.path.join(root, d), app)}")
                if name in AD_SERVING:
                    problems.append(f"ad-SERVING SDK embedded: {name}")
            elif ext == ".bundle" and any(n in name for n in AD_SERVING + [a for a in ATTRIBUTION if a not in allowed]):
                problems.append(f"SDK resource bundle: {os.path.relpath(os.path.join(root, d), app)}")
    info_path = os.path.join(app, "Info.plist")
    info = plistlib.load(open(info_path, "rb")) if os.path.exists(info_path) else {}
    for k in AD_PLIST_KEYS:
        if k in info:
            problems.append(f"Info.plist has the ad-serving key {k}")
    attribution_allowed = any(a in allowed for a in ATTRIBUTION)
    if not attribution_allowed:
        for k in TRACKING_PLIST_KEYS:
            if k in info:
                problems.append(f"Info.plist has the tracking key {k} but no attribution SDK is allowed")
    priv_path = os.path.join(app, "PrivacyInfo.xcprivacy")
    if not os.path.exists(priv_path):
        problems.append("PrivacyInfo.xcprivacy is missing (ITMS-91053)")
    else:
        priv = plistlib.load(open(priv_path, "rb"))
        tracking, domains = priv.get("NSPrivacyTracking"), priv.get("NSPrivacyTrackingDomains") or []
        if not attribution_allowed and (tracking or domains):
            problems.append(f"PrivacyInfo declares tracking ({tracking}, {domains}) but no attribution SDK is allowed")
        if tracking and not domains:
            problems.append("PrivacyInfo: tracking true with no tracking domains (ITMS-91064)")
    return problems


def fake_bundle(d, frameworks=(), info=None, privacy=None):
    app = os.path.join(d, "X.app")
    os.makedirs(os.path.join(app, "Frameworks"), exist_ok=True)
    for f in frameworks:
        os.makedirs(os.path.join(app, "Frameworks", f + ".framework"))
    plistlib.dump(info or {"CFBundleIdentifier": "x"}, open(os.path.join(app, "Info.plist"), "wb"))
    if privacy is not False:
        plistlib.dump(privacy or {"NSPrivacyTracking": False, "NSPrivacyTrackingDomains": []},
                      open(os.path.join(app, "PrivacyInfo.xcprivacy"), "wb"))
    return app


def selftest():
    cases = [  # (description, bundle kwargs, allowed, must_pass)
        ("clean bundle", {}, set(), True),
        ("ad-serving SDK", {"frameworks": ["GoogleMobileAds"], "info": {"GADApplicationIdentifier": "ca-app-pub-1"}}, set(), False),
        ("unlisted framework", {"frameworks": ["FBSDKCoreKit"]}, set(), False),
        ("tracking key without SDK", {"info": {"NSUserTrackingUsageDescription": "x"}}, set(), False),
        ("tracking privacy without SDK", {"privacy": {"NSPrivacyTracking": True, "NSPrivacyTrackingDomains": ["a.b"]}}, set(), False),
        ("missing privacy manifest", {"privacy": False}, set(), False),
        ("allowed attribution SDK", {"frameworks": ["FBSDKCoreKit"], "info": {"FacebookAppID": "1"},
                                     "privacy": {"NSPrivacyTracking": True, "NSPrivacyTrackingDomains": ["ep1.facebook.com"]}},
         {"FBSDKCoreKit"}, True),
        ("ad-serving even if listed", {"frameworks": ["GoogleMobileAds"]}, {"GoogleMobileAds"}, False),
    ]
    ok = True
    for desc, kw, allowed, must_pass in cases:
        d = tempfile.mkdtemp()
        try:
            got = not check(fake_bundle(d, **kw), allowed)
        finally:
            shutil.rmtree(d)
        mark = "ok" if got == must_pass else "WRONG"
        ok &= got == must_pass
        print(f"  control {mark}: {desc} -> {'pass' if got else 'fail'} (want {'pass' if must_pass else 'fail'})")
    return ok


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not selftest():
        print("gate 8: the planted controls did not behave; the gate cannot be trusted")
        sys.exit(1)
    if sys.argv[1] == "selftest":
        print("gate 8 selftest: every control behaves")
        return
    allowed = set(os.environ.get("ALLOWED_FRAMEWORKS", "").split())
    problems = check(sys.argv[1], allowed)
    for p in problems:
        print("  FAIL", p)
    print(f"  gate 8: {'PASS' if not problems else 'FAIL'} (allowed frameworks: {sorted(allowed) or 'none'})")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
