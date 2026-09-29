---
name: app-factory
description: End-to-end iOS app factory. Use this skill whenever the user asks to build, generate, produce, ship, or submit an app from the ideas queue, or says "yeni app", "sıradaki fikri üret", "app bas", "submit et", or runs factory.sh. It takes one idea from ideas.yaml and drives it all the way to App Store review submission - codegen, build loop, design pass, onboarding, icon, RevenueCat, App Store Connect, screenshots, metadata, submit. Always use this skill for any new-app production task in this repo, even if the user only mentions part of the pipeline.
---

# App Factory — Fikirden Submit'e Tek Akış

Bu skill, `ideas.yaml` içindeki TEK bir fikri alır ve App Store incelemesine gönderilmiş bir uygulamaya dönüştürür. Fazları SIRAYLA uygula. Her fazın "bitti" kriteri var — kriter sağlanmadan sonraki faza geçme.

## Sabit kurallar (her fazda geçerli)

- Asla başarı taklidi yapma. Bir adım 3 denemede çözülmezse dur, app dizinine `BLOCKED.md` yaz (ne denendi, hata çıktısı, önerilen çözüm) ve kullanıcıya raporla.
- Uygulamada ağ çağrısı YASAK — tek istisna RevenueCat SDK. Supabase, Firebase, analytics SDK, AI API yok. Tüm veri lokal (SwiftData / UserDefaults / dosya).
- Kod yazmadan önce `docs/DESIGN.md` ve `docs/ASO.md` okunmuş olmalı.
- Tüm shell komutlarını app dizini içinde çalıştır (`apps/<slug>/`).
- `.env` repo kökünde; script'ler onu kendisi okur.

## Faz 0 — Hazırlık

1. Repo kökündeki `ideas.yaml` dosyasından hedef fikri oku (kullanıcı slug verdiyse onu, vermediyse `status: pending` olan ilk kaydı).
2. **KLON/SPAM KONTROLÜ (build'den ÖNCE, zorunlu).** Apple Guideline 4.3 (Spam) tek geliştiricinin aynı çekirdek işlev/UX'e sahip birden çok app'ini işaretler ve tüm hesabı riske atar. Yeni fikri, **halihazırda submit edilmiş app'ler + kuyruktaki diğer fikirler** (`ideas.yaml` + `ROUTINEAPPS.MD`) ile karşılaştır; çekirdek işlev + kategori mevcut/kuyruktaki bir app'le ESASLI örtüşüyorsa (sadece ortak framework değil) DUR ve scaffold'dan önce kullanıcıya bildir. Bilinen klon kümeleri: `iostoandroid`/`movetoandroid`/`movetoios` (hepsi telefon-telefon veri transferi), `contactbackup`/`addressbook` (ikisi de rehber). Farklı işlevler sorun değil. **İstisna:** kullanıcı açıkça "do it" / "build it anyway" derse yine de yap — bu yalnızca tavsiye. (Bkz. PROJECT_LOG.md §3.)
3. `docs/DESIGN.md` ve `docs/ASO.md` dosyalarını oku.
4. App henüz scaffold edilmediyse: repo kökünde `./scripts/new_app.sh <slug>` çalıştır. Bu, `template/` → `apps/<slug>/` kopyalar, token'ları doldurur ve `xcodegen generate` çağırır.
5. **Bitti kriteri:** `apps/<slug>/<AppName>.xcodeproj` mevcut.

## Faz 1 — Core feature codegen

1. Fikrin `features` listesindeki her maddeyi `App/Core/` altında SwiftUI olarak yaz. `HomeView.swift` giriş noktası; gerekirse ek view/model dosyaları ekle (yeni dosya eklediysen `xcodegen generate` tekrar çalıştır — project.yml klasörü otomatik tarar).
2. Veri modeli: SwiftData (`@Model`) veya küçük durumlar için UserDefaults (`Store.swift` yardımcıları hazır).
3. Pro-gate: fikirde `pro_features` olarak işaretli özellikler `AppState.isPro == false` iken `PaywallView`'a yönlendirsin.
4. **Bitti kriteri:** Tüm feature'lar kodda var, derleme Faz 2'de doğrulanacak.

## Faz 2 — Build loop (XcodeBuildMCP)

1. XcodeBuildMCP'nin simülatör listeleme aracıyla mevcut simülatörleri çek ve en yeni iPhone Pro modelini seç (isim hardcode etme — makinedeki iOS sürümüne göre değişir). XcodeBuildMCP ile o simülatöre build al. Hata varsa oku → düzelt → tekrar. Yeşil olana kadar döngü.
2. Simülatörü boot et, app'i kur ve başlat. Ana ekranların her birine navigate edip `shots/raw/` altına screenshot al (XcodeBuildMCP'nin screenshot aracıyla). En az 5 ekran: home, ana feature, detay, settings, paywall.
3. Screenshot'lara BAK. Kırık layout, taşan text, boş ekran varsa düzelt ve tekrar çek.
4. **Bitti kriteri:** Build yeşil + `shots/raw/` içinde 5+ temiz screenshot.

## Faz 3 — Design pass

1. `docs/DESIGN.md` checklist'ini ekran ekran uygula: tipografi ölçeği, spacing grid, empty state'ler, haptics, animasyonlar, dark mode.
2. Dark mode'da tüm ekranların screenshot'ını al, kontrast sorunlarını düzelt.
3. **Bitti kriteri:** Checklist'teki her madde için "uygulandı" diyebiliyorsun; iki modda da temiz screenshot var.

## Faz 4 — Onboarding

1. `claude-skill-app-onboarding-questionnaire` skill'ini çağır (kurulu, `~/.claude/skills/` altında). Fikrin konseptine uygun 3-5 adımlık anket akışı üretsin; çıktıyı `App/Onboarding/` içine entegre et. Akışın sonu `PaywallView`'a bağlanır (soft paywall: kapatılabilir, X sağ üstte 2sn gecikmeli).
2. Rebuild + onboarding akışının her adımının screenshot'ı.
3. **Bitti kriteri:** İlk açılışta onboarding → paywall → home akışı çalışıyor.

## Faz 5 — App icon

1. Gemini MCP `generate_image` ile 1024×1024 icon üret: fikrin konseptine uygun, tek güçlü sembol, `accent` rengi baskın, gradyan zemin, TEXT YOK, fotogerçekçilik yok. 3 varyant üret, en iyisini seç.
2. PNG'yi `App/Assets.xcassets/AppIcon.appiconset/` içine koy (tek 1024 boyut yeterli, Contents.json hazır).
3. **Bitti kriteri:** Build sonrası simülatör home ekranında icon görünüyor.

## Faz 6 — RevenueCat

1. Repo kökünde: `python3 scripts/rc_setup.py --slug <slug>`. Script; app'i RC projesine ekler, entitlement + product + offering + package kurar, app'e özel public API key'i çekip `App/Config.swift` içine yazar.
2. Script hata verirse çıktıyı oku, script'i düzelt, tekrar çalıştır (RC API v2 dokümana göre alan adları değişmiş olabilir — RevenueCat MCP bağlıysa doğrulamak için kullanabilirsin).
3. Rebuild; paywall ekranı offering'deki paketleri listeliyor olmalı (StoreKit sandbox olmadan fiyatlar boş görünebilir — paket ID'lerinin geldiğini logla, yeterli).
4. **Bitti kriteri:** `Config.swift` içinde gerçek `appl_...` key var; app RC'ye configure oluyor, crash yok.

## Faz 7 — App Store Connect

1. `apps/<slug>/` içinde: `fastlane create_app`. ASC'de app kaydı + bundle ID oluşur.
2. Repo kökünde: `python3 scripts/asc_iap.py --slug <slug>`. Subscription group + weekly/yearly abonelikleri, TUM bolgelerde fiyat (availability ONCE, sonra fiyat), localization, 3-gun trial ve **3-gun billing grace period (uretim + sandbox)** olusturur. **İlk çalıştırmada Apple'ın API şeması yüzünden hata çıkması normaldir — hatayı oku, script'i düzelt, tekrar dene.** Bir kez çalıştıktan sonra sonraki app'lerde deterministiktir.
3. **Bitti kriteri:** ASC'de app kaydı + 2 abonelik `READY_TO_SUBMIT` (MISSING_METADATA kalmadi — tum bolge fiyatlari + review screenshot + review note dolu; screenshot artik `-DemoPaywall` capture'i ile API'den otomatik yukleniyor).

## Faz 8 — App Store screenshot'ları

1. `claude-skill-aso-appstore-screenshots` skill'ini çağır. Girdi: `shots/raw/` içindeki en iyi 5 ekran + fikrin `benefits` alanı (yoksa feature'lardan 5 fayda çıkar, EYLEM FİİLİ + FAYDA formatında). Marka rengi = `accent`.
2. Skill çıktılarını `fastlane/screenshots/en-US/` altına 1290×2796 olarak koy.
3. **Bitti kriteri:** 5 adet ASC boyutunda, tutarlı setlenmiş pazarlama screenshot'ı.

## Faz 9 — Metadata (ASO)

`docs/ASO.md` kurallarıyla `fastlane/metadata/en-US/` doldur: `name.txt` (≤30), `subtitle.txt` (≤30), `keywords.txt` (≤100, virgüllü, name/subtitle'daki kelimeleri tekrar etme), `description.txt`, `promotional_text.txt`, `privacy_url.txt` (.env'deki PRIVACY_URL). `release_notes.txt`: "Initial release." Kategori zaten Deliverfile'da token'dan geliyor.

## Faz 10 — Kalite kapilari (submit on kosulu)

CLAUDE.md'deki 6 kalite kapisini TEK TEK dogrula. Hepsi yesil olmadan Faz 11'e gecme; kirmizi olan varsa duzelt ve bu fazi bastan calistir.

1. Build temiz, warning'ler makul.
2. Isik + karanlik modda tum ekranlarin screenshot'i alinip GORULDU (Faz 2-3 ciktilari eskiyse tekrar cek ve bak).
3. Onboarding → paywall → home akisi calisiyor; paywall X'i 2 sn gecikmeli ve CALISIYOR — simulatorde X'e bizzat tiklayip paywall'in kapandigini dogrula (Apple reddi: kapatilamayan soft paywall).
4. Restore Purchases butonu hem Settings'te hem paywall'da var ve CALISIYOR — simulatorde ikisine de tikla, restore cagrisinin crash'siz tamamlandigini dogrula.
5. Bos durumlar (empty state) tasarlandi — hicbir ekran "bos beyazlik" degil.
6. Rating istegi onboarding'de DEGIL, anlamli aksiyonda (RatingManager kurali) — onboarding kodunda requestReview/RatingManager cagrisi olmadigini grep'le dogrula.
7. **INTERAKTIF BUG CHECK (zorunlu, otomatik)** — `python3 scripts/bug_check.py --slug <slug>`:
   XCUITest harness'ini en yeni iPhone Pro simulatorunde AYDINLIK + KARANLIK modda kosar
   (gercek dokunuslar, sadece screenshot degil). Template'ten gelen `UITests/FactoryUITests.swift`
   evrensel sozlesmeyi test eder (paywall: iki plan da secilebilir + gecikmeli X acilip kapanir +
   Restore; Settings: Restore + Upgrade→paywall). **Faz 1/10'da bu app'e ozgu testleri EKLE**:
   onboarding→home (bu app'in akisina gore) ve core feature'in her butonu — feature butonlarina
   accessibility identifier ver, dosyadaki stub'lari doldur. Herhangi bir test kalirsa script exit 1
   verir → duzelt, tekrar kos. Yesil olmadan Faz 11 YOK.

**Bitti kriteri:** 7 kapinin hepsi icin kanitiyla "dogrulandi" diyebiliyorsun.

## Faz 11 — Submit

Ön koşul: Faz 10'daki 6 kalite kapısının hepsi yeşil — değilse submit YOK.

1. Repo kökünde bir kez: `python3 scripts/signing_setup.py --slug <slug>` (cihazsiz imzalama: API'yle Distribution sertifikasi + App Store profili; Xcode cloud signing Admin key istedigi icin kullanilmaz).
2. `apps/<slug>/` içinde: `fastlane release`. Archive (imzasiz) → export (manual imza) → upload → metadata + screenshot'lar. Signing/provisioning hatasında: `-allowProvisioningUpdates` zaten açık; hatayı oku ve düzelt (çoğu hata TEAM_ID veya bundle ID kaydından çıkar).
3. **Submit — `fastlane` submit_for_review YETMEZ**: yeni subscription group'un abonelikleri app version ile OTOMATIK bundle olmaz ve `READY_TO_SUBMIT`'te takilir (Apple reddi riski). Repo kökünde: `python3 scripts/asc_submit.py --slug <slug>`. Bu, TEK reviewSubmission'da appStoreVersion + subscriptionGroupVersion + her subscriptionVersion item'ini gonderir. Detay: memory [[asc-subscription-submission]].
4. `python3 scripts/asc_submit.py` çıktısında reviewSubmission `WAITING_FOR_REVIEW` olmalı; API'yle app version + her subscription state'inin `WAITING_FOR_REVIEW` olduğunu ayrıca doğrula.
5. İşlem bitince `ideas.yaml`'da fikrin `status` alanını `submitted` yap, ROUTINEAPPS.MD satırını ✅ yap.
6. Kullanıcıya kısa rapor: app adı, bundle ID, abonelik fiyatları, ASC linki, varsa manuel kalan işler.

## Manuel kalan işler (kullanıcıya her raporda hatırlat)

- Apple'ın abonelik "review screenshot" alanı ARTIK OTOMATIK — DEBUG `-DemoPaywall` ile temiz bir paywall capture'ı çekilip ASC API ile (subscriptionAppStoreReviewScreenshots: reserve→upload→commit) her aboneliğe yüklenir. Elle gerekmiyor.
- İlk app'te Paid Apps sözleşmesi/banka zaten bağlı olmalı (kullanıcıda mevcut).
- RevenueCat StoreKit-2 In-App Purchase Key + ASC API key `rc_setup.py` içinde otomatik bağlanır (Faz 6).
