#!/bin/bash
# Kullanım: ./scripts/new_app.sh <slug>
# template/ -> apps/<slug>/ kopyalar, token'ları doldurur, Xcode projesini üretir.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SLUG="${1:?slug gerekli (ideas.yaml içindeki)}"

# .env yükle
set -a; source .env; set +a

# Fikri oku (once degiskene al: idea.py patlarsa set -e burada dursun, eval maskelemesin)
IDEA_VARS="$(python3 scripts/idea.py get "$SLUG")"
eval "$IDEA_VARS"

DEST="apps/$SLUG"
if [ -d "$DEST" ]; then
  echo "zaten var: $DEST (devam ediliyor, token'lar tekrar YAZILMAZ)"
else
  # Once gecici dizine kur, en sonda tasi: yarim kalan is apps/'i zehirlemesin.
  TMP_DEST="apps/.${SLUG}.tmp"
  rm -rf "$TMP_DEST"; mkdir -p apps
  trap 'rm -rf "$TMP_DEST"' EXIT
  cp -R template "$TMP_DEST"
  BUNDLE_ID="${BUNDLE_PREFIX}.${SLUG}"

  # Token doldurma (BSD sed). Sıra önemli: NOSPACE önce.
  find "$TMP_DEST" -type f \( -name "*.swift" -o -name "*.yml" -o -name "Fastfile" -o -name "Appfile" -o -name "Deliverfile" -o -name "*.txt" -o -name "*.py" \) -print0 |
  while IFS= read -r -d '' f; do
    sed -i '' \
      -e "s|__APP_NAME_NOSPACE__|${APP_NAME_NOSPACE}|g" \
      -e "s|__STORE_NAME__|${STORE_NAME}|g" \
      -e "s|__APP_NAME__|${APP_NAME}|g" \
      -e "s|__APP_ID__|${SLUG}|g" \
      -e "s|__BUNDLE_PREFIX__|${BUNDLE_PREFIX}|g" \
      -e "s|__BUNDLE_ID__|${BUNDLE_ID}|g" \
      -e "s|__TEAM_ID__|${TEAM_ID}|g" \
      -e "s|__ACCENT_HEX__|${ACCENT_HEX}|g" \
      -e "s|__CATEGORY__|${CATEGORY}|g" \
      -e "s|__DEV_NAME__|${DEV_NAME}|g" \
      -e "s|__PRIVACY_URL__|${PRIVACY_URL}|g" \
      -e "s|__ENTITLEMENT_ID__|${SLUG}_pro|g" \
      -e "s|__OFFERING_ID__|${SLUG}_default|g" \
      "$f"
  done

  # NOTE: every LOCALE needs its own support_url/privacy_url. Apple rejects the whole
  # submission with ENTITY_ERROR.ATTRIBUTE.REQUIRED on supportUrl if a localization is
  # missing it — which is invisible until submit time. When you add locales, copy these
  # two files into each one (see scripts/fill_locale_urls.py).
  echo "$PRIVACY_URL"  > "$TMP_DEST/fastlane/metadata/en-US/privacy_url.txt"
  echo "$SUPPORT_URL" > "$TMP_DEST/fastlane/metadata/en-US/support_url.txt"
  # App Review iletisim bilgileri (ilk submit icin zorunlu)
  echo "$REVIEW_FIRST_NAME" > "$TMP_DEST/fastlane/metadata/review_information/first_name.txt"
  echo "$REVIEW_LAST_NAME"  > "$TMP_DEST/fastlane/metadata/review_information/last_name.txt"
  echo "$REVIEW_PHONE"      > "$TMP_DEST/fastlane/metadata/review_information/phone_number.txt"
  echo "$REVIEW_EMAIL"      > "$TMP_DEST/fastlane/metadata/review_information/email_address.txt"
  mkdir -p "$TMP_DEST/shots/raw"

  mv "$TMP_DEST" "$DEST"
  trap - EXIT
fi

# Xcode projesi
cd "$DEST"
xcodegen generate
echo ""
echo "OK -> $DEST"
echo "Sıradaki: cd $DEST && claude  (veya kökten ./factory.sh $SLUG)"
