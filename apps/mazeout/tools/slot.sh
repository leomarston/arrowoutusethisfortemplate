#!/bin/sh
# tools/slot.sh <A|B>: SOURCED by build/run/test/bench/capture scripts. Maps a slot letter to its simulator and sets the
# shared paths (GAMEPROMPT §3.3, §8.2; PLAN.md "Names and resources"). Adapted from apps/matchfactory/tools/slot.sh
# (05424db): MF Spike/MF Main -> Maze A/Maze B, MatchFactory -> ArrowOut (design/REUSE.md).
#
# Only these two UDIDs are ours. Never boot, shut down or erase any other simulator (GAMEPROMPT §3.3: a
# `simctl shutdown all` once killed another session's simulator).
case "$1" in
  A) UDID=177520B6-4889-46C2-BDD9-155813D2B175; SIM_NAME="Maze A" ;;
  B) UDID=B80EDB24-6280-4C52-A63F-E8AADD245017; SIM_NAME="Maze B" ;;
  *) echo "usage: $(basename "$0") <A|B> ..." >&2; exit 64 ;;
esac
SLOT="$1"
# ROOT = apps/mazeout. A caller in a subfolder of tools/ sets ROOT itself before sourcing this file.
if [ -z "$ROOT" ] || [ ! -f "$ROOT/tools/slot.sh" ]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
DD="$ROOT/build/dd-$SLOT"
BUNDLE_ID=com.manycode.arrowout
SCHEME=ArrowOut
PROJECT="$ROOT/ArrowOut.xcodeproj"
# WP0 amendment (SPEC-architecture §2.5 item 1): CONFIG=Release selects the Release products (every performance
# number is taken in Release: `CONFIG=Release tools/build.sh A`); build.sh / test.sh / iso-build-copy.sh pass it on.
# F3-A (SPEC.md ruling 52(a)): Release is the STORE build (no frame watch / GlitchRun / tab loop); CONFIG=Measure is
# Release's settings + PC_MEASURE (project.yml) — the configuration for every -pc.frameWatch / -pc.glitchRun run.
CONFIG="${CONFIG:-Debug}"
APP="$DD/Build/Products/${CONFIG}-iphonesimulator/ArrowOut.app"
# Console log of the last tools/run.sh launch: written INSIDE the simulator's own data/tmp (the host sandbox denies
# xpcproxy_sim access to ~/Downloads), linked from build/run-<slot>.log.
SIMLOG="$HOME/Library/Developer/CoreSimulator/Devices/$UDID/data/tmp/pc-run-$SLOT.log"
export UDID SIM_NAME SLOT ROOT DD BUNDLE_ID SCHEME PROJECT CONFIG APP SIMLOG

# --- helpers (plain sh functions; every caller already `set -e`) ---------------------------------------------------

# Booted | Shutdown | Shutting Down | Creating
sim_state() {
  xcrun simctl list devices | grep "$UDID" | sed -E 's/.*\((Booted|Shutdown|Shutting Down|Creating)\).*/\1/'
}

# Boots THIS slot's simulator if needed, then stops its ~1 GB background asset downloads (GAMEPROMPT §3.3; our UDIDs
# only; run `sim_unblock_assets` before erasing the simulator).
sim_boot() {
  if [ "$(sim_state)" != "Booted" ]; then
    xcrun simctl boot "$UDID" 2>/dev/null || true
    xcrun simctl bootstatus "$UDID" -b >/dev/null
  fi
  _c="$HOME/Library/Developer/CoreSimulator/Devices/$UDID/data/Library/Caches/com.apple.nsurlsessiond"
  if [ -d "$_c" ]; then chmod 000 "$_c" 2>/dev/null || true; fi
}

sim_unblock_assets() {
  _c="$HOME/Library/Developer/CoreSimulator/Devices/$UDID/data/Library/Caches/com.apple.nsurlsessiond"
  if [ -d "$_c" ]; then chmod 755 "$_c" 2>/dev/null || true; fi
}

# Free swap in whole MB ("vm.swapusage: total = 12288.00M  used = 10880.88M  free = 1407.12M  (encrypted)").
swap_free_mb() {
  sysctl vm.swapusage | sed -E 's/.*free = ([0-9]+)(\.[0-9]+)?M.*/\1/'
}

# GAMEPROMPT §3.4: before a build, free swap must be >= SWAP_MIN_MB (400); wait in 2-minute steps, at most
# SWAP_WAIT_MAX seconds (default 600), then give up with exit 75 (EX_TEMPFAIL) so the caller reports instead of
# pushing the machine into a swap storm. Also refuses to start with < 3 GB of disk (a full disk surfaces as codesign or
# linker errors).
wait_for_memory() {
  _who="${1:-tools}"
  _avail=$(df -g / | awk 'NR==2 {print $4}')
  if [ "${_avail:-0}" -lt 3 ]; then
    echo "$_who: only ${_avail} GB free on / (< 3 GB): stop heavy work, clean your own files, report" >&2
    exit 1
  fi
  _waited=0
  while [ "$(swap_free_mb)" -lt "${SWAP_MIN_MB:-400}" ]; do
    if [ "$_waited" -ge "${SWAP_WAIT_MAX:-600}" ]; then
      echo "$_who: free swap $(swap_free_mb) MB < ${SWAP_MIN_MB:-400} MB for ${_waited} s: stop and report" >&2
      exit 75
    fi
    echo "$_who: free swap $(swap_free_mb) MB < ${SWAP_MIN_MB:-400} MB; waiting 120 s" >&2
    sleep 120
    _waited=$((_waited + 120))
  done
}
