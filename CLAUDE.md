# App Factory — Calisma Kurallari

Bu repo, ideas.yaml'daki fikirleri App Store'a submit edilmis iOS uygulamalarina donusturen bir fabrikadir.

## Her yeni app isinde
- HER ZAMAN `app-factory` skill'ini kullan ve fazlarini SIRAYLA uygula.
- Kod yazmadan once `docs/DESIGN.md` ve `docs/ASO.md` oku.
- **`PROJECT_LOG.md` (kok dizin) = tasinabilir tam hafiza.** Yeni bir oturuma/makineye
  gecince ONCE onu oku: tum kararlar, kurallar, "ruled out" edilenler, app durumlari,
  teknik tuzaklar/duzeltmeler orada. Onemli bir sey degisince PROJECT_LOG.md'yi guncelle.

## Sert kisitlar
- SUNUCU/BACKEND YOK. Asil kural bu: calistirilmasi/bakimi gereken hicbir servis kurma
  (Firebase/Supabase, kendi API'n, analytics backend'i, AI API vb.). Uygulama tek basina, cihazda calisir.
- Ag cagrisi ancak zorunlu ve zararsizsa. Varsayilan tek dis servis RevenueCat SDK (abonelik durumu).
  ISTISNA (2026-07-22 politikasi): app'in ASIL islevi ag gerektiriyorsa (or. speed test / WiFi tester),
  ITIBARLI bir PUBLIC endpoint kullanilabilir (or. speed.cloudflare.com'un ucretsiz __down/__up uclari,
  ping icin 1.1.1.1) — kullanicinin CALISTIRDIGI/bakimini yaptigi bir backend olmadigi icin "sunucu yok"
  kurali bozulmaz. YINE DE: analytics/tracking/AI cagrisi YOK; kendi/Firebase/Supabase backend'i YOK;
  tum kullanici verisi lokal (SwiftData/UserDefaults/dosya).
- Veri lokal: SwiftData veya UserDefaults (`Support/Store.swift`) + dosyalar.
- Istemci-tarafi (offline, ag kullanmayan) kutuphaneler GEREKTIGINDE eklenebilir — or. MP3 encode icin LAME.
  Bunlar sunucu degildir, kurali bozmaz. Yine de varsayilan SwiftUI + sistem framework'leridir; gereksiz bagimlilik sismesinden kacin.
- Placeholder metin/Lorem ile submit YOK. Gercek, ozenli copy yaz.

## Kalite kapilari (submit oncesi hepsi yesil olmali)
1. Build temiz, warning'ler makul.
2. Isik + karanlik modda tum ekranlarin screenshot'i alinip GORULDU.
3. Onboarding -> paywall -> home akisi calisiyor; paywall X'i 2 sn gecikmeli ve CALISIYOR (Apple reddi: kapatilamayan soft paywall).
4. Restore Purchases butonu var ve calisiyor (Settings + paywall).
5. Bos durumlar (empty state) tasarlandi — hicbir ekran "bos beyazlik" degil.
6. Rating istegi onboarding'de DEGIL, anlamli aksiyonda (RatingManager kurali).

## Durum yonetimi
- Fikir durumlari: pending -> in_progress -> submitted (veya blocked).
- `python3 scripts/idea.py mark <slug> <status>` ile guncelle.
- Takilirsan app dizinine BLOCKED.md yaz ve dur; asla basari taklidi yapma.
