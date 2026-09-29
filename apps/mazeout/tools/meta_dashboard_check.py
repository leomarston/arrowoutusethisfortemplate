#!/usr/bin/env python3
"""RFIX 2026-09-29 (review of the META build): the Meta-side facts a store build depends on, read from Meta itself.

Two things no build step could see, both on Meta's server:

  1. dashboard   The app's settings exactly as the SDK reads them at start (GET graph.facebook.com/<ver>/<app id>?fields=...,
                 the same UNAUTHENTICATED request FBSDKServerConfigurationManager makes: no token is sent):
                   - implicit purchase logging (app_events_feature_bitmask bit 1, the dashboard's "Log in-app events
                     automatically") must be OFF: with it ON, FBSDKCoreKit 18.1.1 starts its own StoreKit 2 purchase logging
                     (FBSDKAppEvents.m fetchServerConfiguration) next to MetaAds' fb_mobile_purchase = every purchase twice;
                   - auto_log_app_events_enabled must not be forced by the server (Settings+AutoLogAppEvents.swift: a server
                     value overrides the app's own switch);
                   - Automatic Advanced Matching must be OFF (aam_rules empty): with rules, FBSDK's MetadataIndexer reads text
                     fields (the game has a profile-name field) and privacy-arrow-out.html says names are not collected.
  2. token       The factory .env's META_CLIENT_TOKEN is this app's CLIENT token, not its App Secret (both are 32 lowercase
                 hex; no format check can tell them apart, and an App Secret in the IPA would be a leaked credential):
                   - '<app id>|<token>' must be accepted by Graph (GET /<app id>?fields=id -> 200; a wrong token -> 190);
                   - it must NOT work as an app access token: GET /<app id>/subscriptions (app-access-token only) must refuse it
                     with 'An access token is required' (104). '<app id>|<App Secret>' IS an app access token and would be
                     answered with data: the check then FAILS and says the pasted value is the App Secret.
                 The token is read from the factory .env through tools/meta_token.py and sent only to graph.facebook.com over
                 HTTPS inside this process (never on a command line, never printed, never written).

    python3 tools/meta_dashboard_check.py [dashboard|token|all] [--json FILE]      (default: all)

Exit 0 = every requested check passed; 1 = a check failed; 2 = Meta could not be reached / answered oddly (never a pass).
fastlane/Fastfile runs `all` before any store build (meta_token_ready!).
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_token  # noqa: E402

APP_ID = "2657116281470019"
GRAPH = "https://graph.facebook.com/v26.0/"      # FBSDK_DEFAULT_GRAPH_API_VERSION of FBSDKCoreKit 18.1.1
IMPLICIT_PURCHASE_BIT = 1 << 1                   # FBSDKServerConfigurationManagerAppEventsFeaturesImplicitPurchaseLoggingEnabled
FIELDS = ("app_events_feature_bitmask,name,supports_implicit_sdk_logging,aam_rules,auto_log_app_events_default,"
          "auto_log_app_events_enabled")


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - the system store is the fallback
        return ssl.create_default_context()


def _get(path, params, secret=None):
    """-> (http status, json dict). `secret` is scrubbed from any text that comes back."""
    url = GRAPH + path + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, context=_ctx(), timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = json.load(e)
        except Exception:  # noqa: BLE001
            body = {}
        return e.code, body
    except Exception as e:  # noqa: BLE001 - no network is "unknown", never a pass
        msg = str(e)
        if secret:
            msg = msg.replace(secret, "<token>")
        return None, {"error": {"message": msg, "type": type(e).__name__}}


def _err(body, secret=None):
    e = body.get("error") or {}
    msg = (e.get("message") or "")[:160]
    if secret:
        msg = msg.replace(secret, "<token>")
    return {"code": e.get("code"), "type": e.get("type"), "message": msg}


def dashboard():
    st, d = _get(APP_ID, {"fields": FIELDS, "os_version": "26.0"})
    out = {"http": st}
    if st != 200 or d.get("id") != APP_ID:
        out.update(state="unknown", error=_err(d))
        return 2, out
    bitmask = int(d.get("app_events_feature_bitmask") or 0)
    aam = d.get("aam_rules")
    aam_on = aam not in (None, "", "{}", {}, [])
    forced = d.get("auto_log_app_events_enabled")
    out.update(app_name=d.get("name"), app_events_feature_bitmask=bitmask,
               implicit_purchase_logging=bool(bitmask & IMPLICIT_PURCHASE_BIT),
               automatic_advanced_matching=aam_on, auto_log_app_events_enabled=forced,
               auto_log_app_events_default=d.get("auto_log_app_events_default"))
    problems = []
    if bitmask & IMPLICIT_PURCHASE_BIT:
        problems.append("'Log in-app events automatically' is ON (implicit purchase logging): every purchase would reach Meta "
                        "twice. Turn it OFF: developers.facebook.com > Arrow Out > App settings > Basic / App events.")
    if aam_on:
        problems.append("Automatic Advanced Matching is ON (aam_rules not empty): the SDK would read text fields. Turn it OFF in "
                        "Events Manager > the Arrow Out dataset > Settings.")
    if forced is True:
        problems.append("the server forces auto_log_app_events_enabled = true (dashboard auto-logging switch).")
    out["problems"] = problems
    return (1 if problems else 0), out


def token():
    state, tok = meta_token.read_token()
    out = {"env_state": state}
    if state != "present":
        out["problems"] = [f"META_CLIENT_TOKEN in the factory .env is {state}"]
        return 1, out
    access = APP_ID + "|" + tok
    st1, d1 = _get(APP_ID, {"fields": "id", "access_token": access}, secret=tok)
    st2, d2 = _get(APP_ID + "/subscriptions", {"access_token": access}, secret=tok)
    out.update(accepted_as_client_token={"http": st1, "id_matches": d1.get("id") == APP_ID, "error": _err(d1, tok)},
               app_access_token_probe={"http": st2, "has_data": "data" in d2, "error": _err(d2, tok)})
    tok = access = None                          # nothing below touches the value
    if st1 is None or st2 is None:
        out["problems"] = ["Meta could not be reached"]
        return 2, out
    problems = []
    if not (st1 == 200 and d1.get("id") == APP_ID):
        problems.append("Graph does not accept '<app id>|<token>' for this app: the .env token is not Arrow Out's client token")
    if st2 == 200 and "data" in d2:
        problems.append("the .env token works as an APP ACCESS TOKEN: it is the App SECRET, not the client token. Do not build; "
                        "replace it with Settings > Advanced > Client token and reset the App Secret (it may have been exposed)")
    elif (d2.get("error") or {}).get("code") != 104:
        problems.append(f"the app-access-token probe answered unexpectedly ({st2}, code {(d2.get('error') or {}).get('code')})")
    out["problems"] = problems
    if problems and not any("SECRET" in p or "not Arrow Out" in p for p in problems):
        return 2, out
    return (1 if problems else 0), out


def selftest():
    """Negative controls: planted Meta answers (no network) must each be caught; the clean answers must pass."""
    global _get
    real_get, real_read = _get, meta_token.read_token
    clean_cfg = {"id": APP_ID, "name": "Arrow Out", "app_events_feature_bitmask": 65557, "aam_rules": "{}",
                 "auto_log_app_events_default": True}
    cases = [
        ("dashboard clean", dashboard, lambda p, q, secret=None: (200, dict(clean_cfg)), 0),
        ("dashboard implicit purchase ON", dashboard,
         lambda p, q, secret=None: (200, dict(clean_cfg, app_events_feature_bitmask=65557 | IMPLICIT_PURCHASE_BIT)), 1),
        ("dashboard AAM ON", dashboard, lambda p, q, secret=None: (200, dict(clean_cfg, aam_rules='{"r1":{"k":"v"}}')), 1),
        ("dashboard auto-log forced", dashboard, lambda p, q, secret=None: (200, dict(clean_cfg, auto_log_app_events_enabled=True)), 1),
        ("dashboard unreachable", dashboard, lambda p, q, secret=None: (None, {"error": {"message": "offline"}}), 2),
        ("token clean", token, lambda p, q, secret=None: (200, {"id": APP_ID}) if "/" not in p
         else (400, {"error": {"code": 104, "message": "An access token is required to request this resource."}}), 0),
        ("token = App Secret", token, lambda p, q, secret=None: (200, {"id": APP_ID}) if "/" not in p else (200, {"data": []}), 1),
        ("token wrong", token, lambda p, q, secret=None: (400, {"error": {"code": 190, "message": "Invalid OAuth access token signature."}}), 1),
    ]
    meta_token.read_token = lambda path=None: ("present", "0" * 32)
    ok = True
    try:
        for name, fn, fake, want in cases:
            _get = fake
            got, _ = fn()
            good = got == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL'}  {name:34s} -> exit {got} (want {want})")
    finally:
        _get, meta_token.read_token = real_get, real_read
    print(f"selftest {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


def main(argv):
    if argv[:1] == ["selftest"]:
        return selftest()
    what = "all"
    jpath = None
    args = list(argv)
    if "--json" in args:
        i = args.index("--json")
        jpath = args[i + 1]
        del args[i:i + 2]
    if args:
        what = args[0]
    checks = {"dashboard": [dashboard], "token": [token], "all": [dashboard, token]}.get(what)
    if checks is None:
        print(__doc__)
        return 2
    worst, report = 0, {}
    for fn in checks:
        code, out = fn()
        report[fn.__name__] = dict(out, exit=code)
        worst = max(worst, code)
        tag = {0: "PASS", 1: "FAIL", 2: "UNKNOWN"}[code]
        print(f"meta_dashboard_check {fn.__name__}: {tag}")
        for k, v in out.items():
            if k != "problems":
                print(f"   {k}: {v}")
        for p in out.get("problems", []):
            print(f"   !! {p}")
    if jpath:
        with open(jpath, "w") as f:
            json.dump(report, f, indent=1)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
