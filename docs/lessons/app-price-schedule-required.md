---
name: app-price-schedule-required
description: "Submit needs a VALID free app price schedule; an existing EMPTY/invalid schedule returns GET 200 and got skipped → APP_PRICING_REQUIRED 409 on the appStoreVersion review item"
metadata:
  node_type: memory
  type: reference
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

Hit on **bluetoothmic** (2026-07-23). `asc_submit.py` failed to add the `appStoreVersion` review item with **409 `STATE_ERROR.APP_PRICING_REQUIRED`** ("App is missing required pricing", associatedError `/v2/appPrices/`) even though `ensure_submission_prereqs` printed "fiyat cizelgesi zaten var".

**Root cause:** the app already had an appPriceSchedule, but it was **invalid/empty** (no valid $0 base price). A `GET /v1/apps/{id}/appPriceSchedule` still returns **200 + data** for an invalid schedule, so the old "if schedule exists, skip" logic left the app without submittable pricing. (Also: adding `?include=baseTerritory,manualPrices` to that GET makes it **404** — a red herring; don't use that include.)

**Fix (baked into `asc_submit.py`):** for a free factory app, ALWAYS (re)create the free schedule instead of skipping — `POST /v1/appPriceSchedules` with `app` + `baseTerritory` USA + `manualPrices=[appPrice → the $0 appPricePoint]` (inline `${p1}` local id). The $0 point is found via `GET /v1/apps/{id}/appPricePoints?filter[territory]=USA&fields[appPricePoints]=customerPrice` where `customerPrice == "0.0"`. POSTing replaces any existing schedule (201). Then the appStoreVersion item adds cleanly.

Also this run: after `deliver` uploads the binary it is **VALID but NOT auto-attached** to the version — PATCH `/v1/appStoreVersions/{vid}/relationships/build` `{data:{type:builds,id:bid}}` (204) before `asc_submit`. Related: [[asc-subscription-submission]].
