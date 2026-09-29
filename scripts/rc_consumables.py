#!/usr/bin/env python3
"""RevenueCat (API v2): an app with consumable products + a NON-current offering, from a catalog JSON.

rc_setup.py is built for subscriptions (slug-derived bundle, `<slug>_pro` entitlement, $rc_* packages,
App/Config.swift). A coin game needs none of that. This script, for the shared project in .env:

  python3 scripts/rc_consumables.py --bundle com.manycode.arrowout --name "Arrow Out" \\
      --catalog apps/mazeout/design/publish/iap.json \\
      [--offering arrowout_shop] [--config-file apps/mazeout/App/Shell/Shop/StoreConfig.swift] \\
      [--dry-run] [--readback out.json]

  1. App entry (type app_store, bundle_id)                  GET/POST /projects/{p}/apps
  2. ASC In-App Purchase Key + ASC API key on that app       POST /projects/{p}/apps/{id}  (rc_setup step 1b)
     -> read back: subscription_key_configured AND app_store_connect_api_key_configured must be true
  3. The production public key (appl_...)                   GET  /apps/{id}/public_api_keys
  4. One product per catalog row, type "consumable"         GET/POST /projects/{p}/products
     (no entitlement: consumables unlock nothing persistent)
  5. Offering --offering (default <last bundle segment>_shop) with one package per product
     (lookup key = catalog id with "." -> "_", never $rc_*), each attached to its product.
     The offering is NEVER made current. Offerings belong to the whole shared project, and factory
     paywalls fall back to `offerings.current`; a coin shop there would break every other app. The
     script refuses to create it unless another offering is already current, and verifies afterwards
     that the current offering did not change.
  6. --config-file: writes `rcAPIKey = "appl_..."` into an EXISTING file (never creates one).

--dry-run: GET requests only (writes raise inside the HTTP layer); ends with the per-method count.
Exit codes: 0 ok / 1 error or failed verification / 3 dry-run: a real run has work to do or would stop.
Idempotent: everything is looked up before anything is created.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc_setup          # noqa: E402  (env, call)
import asc_consumables   # noqa: E402  (load_catalog + the shared self-check)

ROOT = Path(__file__).resolve().parent.parent
RC_TYPE = {"CONSUMABLE": "consumable", "NON_CONSUMABLE": "non_consumable",
           "NON_RENEWING_SUBSCRIPTION": "non_renewing_subscription"}


class DryRunWrite(RuntimeError):
    pass


class Rc:
    def __init__(self, key, project, dry):
        self.key, self.P, self.dry, self.count = key, f"/projects/{project}", dry, {}

    def get(self, path):
        self.count["GET"] = self.count.get("GET", 0) + 1
        return rc_setup.call("GET", path, self.key)

    def must_get(self, path):
        st, j = self.get(path)
        if st != 200:
            print(f"\n!! GET {path} -> HTTP {st}\n{json.dumps(j, indent=1)[:1200] if isinstance(j, dict) else j}")
            sys.exit(1)
        return j

    def items(self, path):
        out, p = [], path
        while p:
            j = self.must_get(p)
            out += j.get("items", [])
            p = j.get("next_page")
        return out

    def write(self, method, path, body, what, ok=(200, 201)):
        if self.dry:
            raise DryRunWrite(f"dry-run refused {method} {path}")
        self.count[method] = self.count.get(method, 0) + 1
        st, j = rc_setup.call(method, path, self.key, body)
        return rc_setup.must(st, j, what, ok=ok)


def plan(rc, msg):
    print(("  [dry-run] would " if rc.dry else "  + ") + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--name", help="RC app display name (default: catalog appName)")
    ap.add_argument("--offering", help="offering lookup key (default: <last bundle segment>_shop)")
    ap.add_argument("--locales", help="comma list passed to the catalog self-check (default: factory 13)")
    ap.add_argument("--config-file", help="existing Swift file holding `rcAPIKey = \"...\"`")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--readback", help="write the verification summary to this JSON file")
    args = ap.parse_args()

    required = ([asc_consumables.norm_locale(x.strip()) for x in args.locales.split(",")]
                if args.locales else asc_consumables.FACTORY_LOCALES)
    products, _ = asc_consumables.load_catalog(args.catalog, required)
    foreign = [p["productId"] for p in products if not p["productId"].startswith(args.bundle + ".")]
    if foreign:     # a catalog pointed at the wrong app would create another app's products
        sys.exit(f"!! product ids do not start with '{args.bundle}.': {foreign[:4]}")
    raw = json.loads(Path(args.catalog).read_text())
    name = args.name or (raw.get("appName") if isinstance(raw, dict) else None)
    if not name:
        sys.exit("!! --name is required (or put appName in the catalog)")
    off_key = args.offering or f"{args.bundle.split('.')[-1]}_shop"
    if off_key.startswith("$rc_"):
        sys.exit("!! the offering lookup key must not start with $rc_")
    pkgs = []
    for i, p in enumerate(products, start=1):
        # "." -> "_"; the "$" of RevenueCat's reserved $rc_* keys can never survive this.
        lk = re.sub(r"[^A-Za-z0-9_]", "_", p["short"] or p["productId"])
        pkgs.append((i, lk, p))
    if len({lk for _, lk, _ in pkgs}) != len(pkgs):
        sys.exit("!! package lookup keys are not unique")
    cfg = Path(args.config_file) if args.config_file else None
    if cfg and not args.dry_run:
        if not cfg.exists() or not re.search(r'rcAPIKey\s*=\s*".*?"', cfg.read_text()):
            sys.exit(f"!! --config-file {cfg} must exist and contain rcAPIKey = \"...\" (never created here)")

    e = rc_setup.env()
    rc = Rc(e["RC_SECRET_KEY"], e["RC_PROJECT_ID"], args.dry_run)
    P = rc.P
    mode = "DRY-RUN (GET only)" if args.dry_run else "WRITE"
    print(f"RevenueCat consumables [{mode}]: {name} ({args.bundle})  products={len(products)}  "
          f"offering={off_key}")
    todo, problems, out = 0, [], {"bundle": args.bundle, "offering": off_key}
    code = 0
    try:
        # 1. App
        app = next((a for a in rc.items(f"{P}/apps?limit=100")
                    if (a.get("app_store") or {}).get("bundle_id") == args.bundle), None)
        if app is None:
            todo += 1
            plan(rc, f"create app '{name}' (app_store, {args.bundle})")
            if not rc.dry:
                app = rc.write("POST", f"{P}/apps", {"name": name, "type": "app_store",
                                                     "app_store": {"bundle_id": args.bundle}}, "app")
        else:
            print(f"  = app {app['id']} ({app.get('name')})")
        app_id = app["id"] if app else None
        out["app_id"] = app_id

        # 2. ASC keys (rc_setup step 1b; same .p8 for both credentials)
        flags = {}
        if app_id:
            st, g = rc.get(f"{P}/apps/{app_id}")
            flags = (g.get("app_store") or {}) if st == 200 else {}
        both = bool(flags.get("subscription_key_configured")) and bool(flags.get("app_store_connect_api_key_configured"))
        if both:
            print("  = ASC In-App Purchase Key + API key configured")
        else:
            todo += 1
            plan(rc, "attach the ASC In-App Purchase Key + ASC API key (.env key)")
            if not rc.dry:
                p8 = Path(ROOT, e["ASC_KEY_PATH"].replace("~", str(Path.home()))).read_text()
                rc.write("POST", f"{P}/apps/{app_id}", {"app_store": {
                    "bundle_id": args.bundle,
                    "subscription_private_key": p8, "subscription_key_id": e["ASC_KEY_ID"],
                    "subscription_key_issuer": e["ASC_ISSUER_ID"],
                    "app_store_connect_api_key": p8, "app_store_connect_api_key_id": e["ASC_KEY_ID"],
                    "app_store_connect_api_key_issuer": e["ASC_ISSUER_ID"]}}, "ASC keys")

        # 3. Public key (production)
        pub = None
        for attempt in range(1 if rc.dry else 5):     # a just-created app's key can lag a moment
            if not app_id:
                break
            keys = rc.must_get(f"{P}/apps/{app_id}/public_api_keys").get("items", [])
            prod = [k for k in keys if str(k.get("key", "")).startswith("appl_")
                    and k.get("environment", "production") == "production"]
            pub = prod[0]["key"] if prod else None
            if pub:
                break
            time.sleep(2)
        if app_id:
            print(f"  public key: {pub[:10] + '...' if pub else 'none yet'}")

        # 4. Products
        have = {}
        if app_id:
            for it in rc.items(f"{P}/products?app_id={app_id}&limit=100"):
                have[it.get("store_identifier")] = it
        prod_ids = {}
        for p in products:
            want_type = RC_TYPE[p["type"]]
            cur = have.get(p["productId"])
            if cur:
                if cur.get("type") != want_type:
                    sys.exit(f"!! RC product {p['productId']} exists as {cur.get('type')}, want {want_type}; "
                             "RC cannot change a product's type.")
                print(f"  = product {p['productId']} ({cur.get('type')})")
                prod_ids[p["productId"]] = cur["id"]
                continue
            todo += 1
            plan(rc, f"create product {p['productId']} ({want_type})")
            if not rc.dry:
                pr = rc.write("POST", f"{P}/products", {
                    "store_identifier": p["productId"], "app_id": app_id, "type": want_type,
                    "display_name": p["locales"]["en-US"]["name"] if "en-US" in p["locales"] else p["referenceName"]},
                    f"product {p['productId']}")
                prod_ids[p["productId"]] = pr["id"]

        # 5. Offering (never current) + packages
        offs = rc.items(f"{P}/offerings?limit=100")
        current = [o for o in offs if o.get("is_current")]
        mine = next((o for o in offs if o.get("lookup_key") == off_key), None)
        out["current_before"] = [o["lookup_key"] for o in current]
        if mine and mine.get("is_current"):
            sys.exit(f"!! CRITICAL: offering {off_key} is the project's CURRENT offering. Every factory app "
                     "without its own offering now falls back to this coin shop. Make another offering "
                     "current in the RC dashboard, then re-run. Nothing was changed.")
        if mine is None:
            if not current:
                sys.exit("!! the shared project has NO current offering; RevenueCat may make a new one "
                         "current. Refusing to create the shop offering until one is current.")
            todo += 1
            plan(rc, f"create offering {off_key} (not current; current stays {current[0]['lookup_key']})")
            if not rc.dry:
                mine = rc.write("POST", f"{P}/offerings", {"lookup_key": off_key,
                                                           "display_name": f"{name} Shop"}, "offering")
        else:
            print(f"  = offering {off_key} ({mine['id']}, current={mine.get('is_current')})")
        off_id = mine["id"] if mine else None
        have_pk = {}
        if off_id:
            for it in rc.items(f"{P}/offerings/{off_id}/packages?limit=100"):
                have_pk[it.get("lookup_key")] = it
        for pos, lk, p in pkgs:
            pk = have_pk.get(lk)
            if pk is None:
                todo += 1
                plan(rc, f"create package {lk} (position {pos})")
                if not rc.dry:
                    pk = rc.write("POST", f"{P}/offerings/{off_id}/packages",
                                  {"lookup_key": lk, "display_name": p["locales"].get("en-US", {}).get("name")
                                   or p["referenceName"], "position": pos}, f"package {lk}")
            attached = []
            if pk:
                attached = [(it.get("product") or {}).get("store_identifier")
                            for it in rc.items(f"{P}/packages/{pk['id']}/products?limit=50")]
            others = [s for s in attached if s != p["productId"]]
            if others:
                sys.exit(f"!! package {lk} carries other products {others}; fix it in RC (never guessed here)")
            if p["productId"] not in attached:
                todo += 1
                plan(rc, f"attach {p['productId']} -> package {lk}")
                if not rc.dry:
                    rc.write("POST", f"{P}/packages/{pk['id']}/actions/attach_products",
                             {"products": [{"product_id": prod_ids[p["productId"]],
                                            "eligibility_criteria": "all"}]},
                             f"attach {lk}", ok=(200, 201))

        # 6. Config file (existing file only)
        if cfg:
            if not cfg.exists():
                todo += 1
                print(f"  ! config file {cfg} does not exist yet (a real run stops before any write)")
            elif pub:
                src = cfg.read_text()
                new = re.sub(r'rcAPIKey\s*=\s*".*?"', f'rcAPIKey = "{pub}"', src, count=1)
                if new == src:
                    print(f"  = {cfg.name} already holds the key")
                else:
                    todo += 1
                    if rc.dry:
                        print(f"  [dry-run] would write the appl_ key into {cfg.name}")
                    else:
                        cfg.write_text(new)
                        print(f"  + {cfg.name}: rcAPIKey written")

        # 7. Verify by reading
        print("\nverify (read back):")
        if app_id:
            st, g = rc.get(f"{P}/apps/{app_id}")
            f2 = (g.get("app_store") or {}) if st == 200 else {}
            out["key_flags"] = {k: f2.get(k) for k in ("subscription_key_configured",
                                                        "app_store_connect_api_key_configured")}
            if not all(out["key_flags"].values()):
                problems.append(f"key flags {out['key_flags']}")
            got = {it.get("store_identifier"): it.get("type")
                   for it in rc.items(f"{P}/products?app_id={app_id}&limit=100")}
            out["products"] = {p["productId"]: got.get(p["productId"]) for p in products}
            bad = [k for k, v in out["products"].items() if v != RC_TYPE[next(
                q["type"] for q in products if q["productId"] == k)]]
            if bad:
                problems.append(f"products missing/wrong type: {bad}")
            out["public_key_present"] = bool(pub)
            if not pub:
                problems.append("no production appl_ public key")
        else:
            problems.append("no RC app yet")
        offs2 = rc.items(f"{P}/offerings?limit=100")
        cur2 = [o["lookup_key"] for o in offs2 if o.get("is_current")]
        out["current_after"] = cur2
        if cur2 != out["current_before"]:
            print(f"!! CRITICAL: the current offering changed {out['current_before']} -> {cur2}")
            problems.append("current offering changed")
            code = 1
        mine2 = next((o for o in offs2 if o.get("lookup_key") == off_key), None)
        if not mine2:
            problems.append(f"offering {off_key} missing")
        else:
            if mine2.get("is_current"):
                problems.append(f"offering {off_key} is current")
                code = 1
            ok_pk = 0
            by_lk = {it.get("lookup_key"): it for it in rc.items(f"{P}/offerings/{mine2['id']}/packages?limit=100")}
            for _, lk, p in pkgs:
                pk = by_lk.get(lk)
                if pk and [(it.get("product") or {}).get("store_identifier")
                           for it in rc.items(f"{P}/packages/{pk['id']}/products?limit=50")] == [p["productId"]]:
                    ok_pk += 1
            out["packages_ok"] = ok_pk
            if ok_pk != len(pkgs):
                problems.append(f"packages attached {ok_pk}/{len(pkgs)}")
        out["problems"] = problems
        for k, v in out.items():
            if k != "products":
                print(f"  {k}: {v}")
        if out.get("products"):
            print(f"  products: {sum(1 for v in out['products'].values() if v)}/{len(products)} present "
                  f"({sorted(set(out['products'].values()), key=str)})")
        if args.readback:
            Path(args.readback).parent.mkdir(parents=True, exist_ok=True)
            Path(args.readback).write_text(json.dumps(out, indent=1))
            print(f"readback -> {args.readback}")
        if problems:
            code = code or (3 if rc.dry else 1)
        elif rc.dry and todo:
            code = 3
    except DryRunWrite as ex:
        print(f"\n!! {ex}")
        code = 1
    print(f"\nHTTP calls: {json.dumps(rc.count, sort_keys=True)}")
    if rc.dry:
        print(f"dry-run: {rc.count.get('GET', 0)} GET, {sum(v for k, v in rc.count.items() if k != 'GET')} "
              f"writes; {todo} change(s) a real run would make")
    sys.exit(code)


if __name__ == "__main__":
    main()
