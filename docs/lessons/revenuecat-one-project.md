---
name: revenuecat-one-project
description: "Factory uses ONE shared RevenueCat project for all apps (user's confirmed choice); RC can't create projects via API; per-app migration later is safe"
metadata: 
  node_type: memory
  type: project
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

Confirmed 2026-07-22: the factory keeps **one shared RevenueCat project** (`proj5f4f704a`, named "Recortar Audio - Reco" after the first app) that holds **all** apps as separate app entries — each with its own bundle, `appl_` public key, entitlement (`<slug>_pro`), offering (`<slug>_default`), and products. `rc_setup.py` stays fully automated (zero manual RC step per app). The user considered separate-project-per-app but chose shared after learning the constraint below.

**Constraint:** the `RC_SECRET_KEY` in `.env` is **project-scoped** — it sees only this one project and CANNOT create projects (`POST /v2/projects` → 401). RevenueCat only creates projects in the dashboard, so "separate project per app" can never be fully hands-off — it always needs a manual dashboard step per app. That's why shared-project is the automated default.

**Migrating an app to its own project later is safe — no lost customers.** Real subscriptions live in **Apple's** system (tied to the user's Apple ID), not RevenueCat; RC only reads Apple's transactions. Point the app to a new project (new `appl_` key in a new build), configure that project's ASC In-App Purchase Key ([[revenuecat-asc-key-required]]), and RC re-syncs each customer's Apple purchases into the new project on launch (StoreKit 2 / receipt sync) so Pro entitlements resolve. Costs: a new build + release, and historical RC analytics/events stay in the old project. Existing Reco + Pomodoro stay in the shared project (already submitted). Related: [[revenuecat-asc-key-required]].
