#!/bin/bash
# Magaza kareleri: her dil icin uygulamayi O DILDE acar ve ekran goruntusu alir.
#
# NEDEN simctl (XCUITest degil): XCUITest icinde dil DEGISMIYOR — launchArguments
# (-AppleLanguages), simulatorun OS ayari ve xcodebuild -testLanguage'in ucu de
# test kosucusu tarafindan eziliyor; uygulama hep Ingilizce aciliyor. `simctl launch`
# ise -AppleLanguages'i dogru uyguluyor. Gezinme icin DEBUG-only `-ShowScreen` derin
# baglantisi kullanilir, boylece dokunmaya gerek kalmaz.
#
# Kullanim: scripts/capture_locales.sh <slug> <sim-udid> <lang:locdir:locale> [...]
#   ornek:  scripts/capture_locales.sh reco ABC de:de-DE:de_DE ja:ja:ja_JP
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
SLUG="$1"; SIM="$2"; shift 2
APP_DIR="$ROOT/apps/$SLUG"
BUNDLE="com.manycode.$SLUG"
APP_PATH=$(find "$APP_DIR/DerivedData/Build/Products/Debug-iphonesimulator" -maxdepth 1 -name "*.app" ! -name "*UITests*" ! -name "*-Runner.app" | head -1)
[ -z "$APP_PATH" ] && { echo "!! build the app first"; exit 1; }

# ekran adi -> cikti dosya adi (make_screenshots.py bu isimleri bekler)
SCREENS="editor:05_editor export:06_export_sheet ringtone:06b_ringtone record:11_record_sheet home:04_home"

xcrun simctl bootstatus "$SIM" -b >/dev/null 2>&1

for triple in "$@"; do
  LANG_CODE="$(echo "$triple" | cut -d: -f1)"
  LOC_DIR="$(echo "$triple"  | cut -d: -f2)"
  LOCALE="$(echo "$triple"   | cut -d: -f3)"
  [ -z "$LOCALE" ] && LOCALE="$(echo "$LANG_CODE" | tr - _)"
  OUT="$APP_DIR/shots/raw-$LOC_DIR"
  mkdir -p "$OUT"
  echo "==> $LANG_CODE ($LOCALE) -> shots/raw-$LOC_DIR"

  # her dil icin temiz kurulum: eski dil tercihi/veritabani kalmasin
  xcrun simctl uninstall "$SIM" "$BUNDLE" >/dev/null 2>&1
  xcrun simctl install "$SIM" "$APP_PATH" >/dev/null 2>&1 || { echo "    !! install failed"; continue; }

  for pair in $SCREENS; do
    SCREEN="${pair%%:*}"; FILE="${pair##*:}"
    xcrun simctl terminate "$SIM" "$BUNDLE" >/dev/null 2>&1
    xcrun simctl launch "$SIM" "$BUNDLE" \
      -SkipOnboarding -SeedDemoAudio -ShowScreen "$SCREEN" \
      -AppleLanguages "($LANG_CODE)" -AppleLocale "$LOCALE" >/dev/null 2>&1
    # dalga formu / sheet animasyonu otursun
    if [ "$SCREEN" = "editor" ] || [ "$SCREEN" = "export" ]; then sleep 9; else sleep 6; fi
    xcrun simctl io "$SIM" screenshot --type=png "$OUT/$FILE.png" >/dev/null 2>&1
    echo "    $FILE"
  done
  xcrun simctl terminate "$SIM" "$BUNDLE" >/dev/null 2>&1
done
echo "==> done"
