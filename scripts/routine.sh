#!/bin/bash
# Gunluk fabrika surucusu — launchd her sabah 05:00 (Turkiye) calistirir.
# Siradaki ⬜ app'i alir, headless Claude Code ile bastan sona uretip submit eder,
# basariliysa ROUTINEAPPS.MD'de ✅ isaretler.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
mkdir -p logs

# .env (FASTLANE_SESSION varsa headless create_app + privacy upload icin)
set -a; [ -f .env ] && . ./.env; set +a

NEXT=$(python3 scripts/routine_next.py) || { echo "$(date) kuyruk bos — yapacak app yok"; exit 0; }
SLUG=$(echo "$NEXT" | cut -f1)
SEED=$(echo "$NEXT" | cut -f2)
STORE_NAME=$(echo "$NEXT" | cut -f3)
LOG="logs/routine-$SLUG-$(date +%Y%m%d).log"

echo "==> $(date)  app: $SLUG  seed: '$SEED'  name: '$STORE_NAME'" | tee -a "$LOG"

read -r -d '' PROMPT <<EOF || true
Bugunun gunluk app uretimi. ROUTINEAPPS.MD'deki kurallara HARFIYEN uy.

Uretilecek app:
  slug        = $SLUG
  seed keyword= $SEED   (keywords.txt'de HER ZAMAN ilk sirada)
  store adi   = $STORE_NAME   (<=30 karakter, App Store limiti)

Adimlar:
1. Bu tohum kelime icin DUSUK REKABETLI, UZUN KUYRUK (long-tail) anahtar kelime listesi
   arastir ve olustur. Seed kelime ilk sirada; alan <=100 karakter, virgulle ayir,
   virgulden sonra bosluk KOYMA, tekil formlar, name/subtitle'daki kelimeleri tekrar etme.
2. ideas.yaml'a '$SLUG' fikrini ekle: store_name '$STORE_NAME', uygun kategori/accent,
   gercek feature + pro_features, 5 fayda (FIIL + FAYDA), pricing
   { weekly_usd: 3.99, weekly_trial_days: 3, yearly_usd: 17.99, yearly_trial_days: 0 }.
3. app-factory skill'ini kullan ve Faz 0'dan 11'e kadar uygula:
   kod uret, temiz derle, isik+karanlik screenshot'lara BAK, onboarding, icon,
   RevenueCat'i baglat (rc_setup.py), ASC app kaydi + abonelikler + 3 gun trial,
   anahtar kelimeli 5 pazarlama screenshot'i (make_screenshots.py),
   ~2800-3900 karakterlik dolu ve durust description.
4. Metadata'da her locale icin linkler:
   privacy https://leomarston.github.io/manycode-legal/privacy.html
   terms   https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
   support https://leomarston.github.io/manycode-legal/support.html
5. SUBMIT ONCESI ZORUNLU KALITE KAPISI: 'python3 scripts/bug_check.py --slug $SLUG' —
   XCUITest harness'i AYDINLIK+KARANLIK modda YESIL olmali. UITests/FactoryUITests.swift'e
   bu app'in onboarding->home ve CORE FEATURE testlerini EKLE (feature butonlarina
   accessibility identifier ver, stub'lari doldur). Kirmizi test varsa duzelt, tekrar kos.
   Yesil olmadan submit YOK.
6. Imzali .ipa uret, build'i yukle. Submit'i 'python3 scripts/asc_submit.py --slug $SLUG'
   ile yap (app surumu + subscriptionGroupVersion + subscriptionVersions TEK
   reviewSubmission'da — yeni subscription group icin sart).
7. ASC API ile DOGRULA: app surumu + WEEKLY + YEARLY abonelik hepsi WAITING_FOR_REVIEW.
   Ancak o zaman 'python3 scripts/routine_done.py $SLUG submitted' calistir.
8. Herhangi bir adim 3 denemede cozulmezse apps/$SLUG/BLOCKED.md yaz, DUR, basari taklidi yapma.
Zaten yayinlanmis bir app'in en-US keywords alanina ASLA dokunma (kullaniciya ait).
Pomodoro kalitesini referans al: uzun-kuyruk keyword'ler, 5 keyword-basligli screenshot,
temiz derleme, calisan paywall, dolu description.
EOF

claude --dangerously-skip-permissions -p "$PROMPT" 2>&1 | tee -a "$LOG"

echo "==> $(date)  $SLUG bitti (durum ROUTINEAPPS.MD'de)" | tee -a "$LOG"
