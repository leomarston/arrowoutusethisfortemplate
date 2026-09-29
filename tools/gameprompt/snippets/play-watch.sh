#!/bin/zsh
# Keeps the latest Arrows build running on the user's "Arrows Play" simulator.
# Installs the first good build immediately, later builds at most every 8 minutes (so play isn't interrupted constantly).
UDID=A9DA09AD-3444-4FCB-A5D0-1E2DC3C2159F
APP=/Users/yago/Downloads/app-factory/apps/arrows/build/DD/Build/Products/Debug-iphonesimulator/Arrows.app
STAGE=/private/tmp/claude-501/-Users-yago-Downloads-app-factory/0c154f3b-15af-44af-adf5-6b546962dd29/scratchpad/play-stage
last=""; lastInstall=0
while true; do
  if [ -f "$APP/Arrows" ]; then
    m=$(stat -f %m "$APP/Arrows"); now=$(date +%s)
    if [ "$m" != "$last" ] && [ $((now - m)) -ge 25 ] && { [ $lastInstall -eq 0 ] || [ $((now - lastInstall)) -ge 480 ]; }; then
      if codesign -v "$APP" 2>/dev/null; then
        rm -rf "$STAGE"; mkdir -p "$STAGE"; cp -R "$APP" "$STAGE/"
        xcrun simctl terminate $UDID com.manycode.arrows >/dev/null 2>&1
        if xcrun simctl install $UDID "$STAGE/Arrows.app" && xcrun simctl launch $UDID com.manycode.arrows >/dev/null; then
          last=$m; lastInstall=$now; echo "$(date '+%H:%M:%S') installed + launched build from $(date -r $m '+%H:%M:%S')"
        fi
      fi
    fi
  fi
  sleep 20
done
