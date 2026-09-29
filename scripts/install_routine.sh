#!/bin/bash
# App Factory otomatik rutinini KUR (durable, launchd).
# Her gun 05:00 ve 17:00 (Turkiye saati = Mac yerel saati, +03) siradaki ⬜ app'i
# bastan sona uretip incelemeye submit eder. Sunu SEN calistir (bilincli onay):
#   bash scripts/install_routine.sh
set -euo pipefail
PLIST="com.manycode.appfactory.routine.plist"
SRC="$(cd "$(dirname "$0")" && pwd)/launchd/$PLIST"
DEST="$HOME/Library/LaunchAgents/$PLIST"

mkdir -p "$HOME/Library/LaunchAgents" "$(cd "$(dirname "$0")/.." && pwd)/logs"
cp "$SRC" "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load -w "$DEST"

echo "OK -> launchd job yuklendi: $DEST"
if launchctl list | grep -q "com.manycode.appfactory.routine"; then
  echo "   dogrulandi: job listede."
else
  echo "   !! job listede gorunmuyor — 'launchctl list | grep manycode' ile kontrol et."
fi
echo
echo "Sonraki calisma: bugun/ yarin ilk 05:00 veya 17:00'de."
echo "Manuel bir kere calistirmak istersen:  bash scripts/routine.sh"
echo "Durdurmak icin:  launchctl unload \"$DEST\" && rm \"$DEST\""
echo
echo "=== KALAN TEK ADIM (sudo — sen calistir) ==="
echo "Mac'i her sabah 04:55'te uyandir ki 05:00 kosusu kacmasin:"
echo "  sudo pmset repeat wakeorpoweron MTWRFSU 04:55:00"
echo "(17:00 kosusu icin Mac'in aksamustu uyanik/acik olmasi yeterli.)"
