#!/bin/sh
# tools/bench/release_gates.sh <path/to/Release/ArrowOut.app> [path/to/Debug/ArrowOut.app]   (VERIFY V1; GP §14,
# SPEC-architecture §6.11 / §12.2 V1, SPEC.md §2 / §5.24)
# The Release-binary gates, printed as a report; exit 0 only when every gate passes:
#  1. no dev placeholder: `strings -a` of the Release binary has 0 "PC-DEBUG-PLACEHOLDER" (DebugPlaceholder is #if DEBUG),
#     with two controls: a string every build carries ("cold launch summary", the launch_done log mark) is found (> 0) in the
#     same binary, and the marker IS found in the Debug build's code when one is given (the grep can see it);
#  2. honesty: 0 "simulat" / "simüle" / "bot " in any user-facing string (the compiled catalogues, EN + TR), and every other
#     hit in the binary or a bundled data file is listed with its context and must be explained below (the SDK's own
#     platform names in a SIMULATOR build: iphonesimulator / ios-simulator; INTEG 2026-09-25 reworded the countries.tsv
#     comment line to "player world", so a 'simulat' in a bundled data file is no longer explained);
#     A0 (SPEC.md §5 item 42, 2026-09-28): the RevenueCat SDK is linked statically since contract amend 4. Its own strings
#     (Test Store / simulator developer messages, type and symbol names) are attributed ONLY by byte-identical match with a
#     hit string of the pinned SDK's own object file (RC_OBJ, default <products dir>/RevenueCat.o, the file the linker read);
#     when the binary carries RevenueCat and that file is missing, the gate FAILS. Our strings are never in that file, so
#     every hit of ours stays UNEXPLAINED exactly as before. Plus the simulator compiler-rt availability helper that
#     RevenueCat.o pulls in (___isPlatformVersionAtLeast reads IPHONE_SIMULATOR_ROOT; absent from a device build);
#  3. brand: the original's names ("Maze", "MazeOut", "Arrow Jam", "Grand Games", "grandgames", "arrowjam") nowhere in the
#     binary or the bundle (B2: no exception — the name generator's bank ships them hashed), no file name carrying them, and the
#     product name ("Arrow Out") not spelled in the binary (Brand reads Info.plist). Note: Swift keeps literals of ≤ 15
#     UTF-8 bytes inline in the code, where `strings` cannot see them, so the SOURCE greps (BrandTests, StringsCoverageTests)
#     are the check for short literals; this gate covers the longer ones and every data file.
#  7. provenance (FIX-2 lane B, L29 / G4(c); the number is the one the FIX-2 ledger gave it): nothing from research/ or the
#     original's version history ships. EVERY file of the bundle (binary-safe, like 2b) has 0 hits of: a research path
#     ('research/', 'video-frames'), the original's version tags ('v552', 'v582'), and in text data files (json / tsv / txt /
#     strings / plist / csv) the capture-provenance JSON keys ("shot":, "capture":, "reader":, "anomalies":,
#     "occlusion_inferred":); and no BoardLab lab fixture (lab_L*.json / labb_L*.json, Debug only via project.yml) is in the
#     bundle. Control: the same scanner run on a planted sample (a level JSON with a "capture": research/ path, a binary blob
#     with 'v582') must report both, or the gate FAILS (the grep can see what it looks for).
#     FIX-2 B review (N-01): also 0 hits of the research readers' vocabulary in ANY file ('bot_time', 'phone nor video',
#     'phone JSON', 'pitch_pt', 'bbox_px'), of a level's research keys in text files ("source":, "metrics":), and of a message-
#     like string (it has a space) saying phone / video / bot_ in a Mach-O file unless RevenueCat.o holds it byte for byte;
#     the planted control grows by the old publish-form level and the old binary strings.
#     F3-B (2026-09-29) 7b: bundled-JSON key hygiene — every JSON under Art/ and UI/ (the art sync's output) carries no
#     non-runtime key (tools/strip_bundle_json.py's rule: "note" / "notes" / "baked" / "proof" / "replaces", "_" comments,
#     capture-provenance keys; sync_art.sh strips them at sync time), no bundled JSON anywhere carries "replaces" or a
#     provenance key, and the App/Resources developer comments ("_about", "note" …) are listed as WATCH; planted control.
#     F3-A (2026-09-29, at F3-B's invitation): App/Resources' developer comments are stripped (ui / game / rules.json), so
#     they FAIL too now; the one ruled exception is Levels/curve.json "/_about" (B0: the runtime compares the bundled curve
#     with the compiled CurveSpec.default, so its neutral comment stays), listed as KEPT.
#     7c (FIX-3 B 2026-09-29, SPEC.md ruling 55(b)/(c); V1-app G8's V1A-G8-1/2/3): the MAIN BINARY's symbol table (nm) and
#     its standalone words — `strings -a` never reads the symbol table, and gates 3 / 7 match phrases only (a case-sensitive
#     "Maze", message text with a space). The words (maze in any case = the original's title word AND the build tree
#     apps/mazeout in a path; recorded; video; gate 7's research/ v552 v582 bot_time) must be absent from the binary's
#     printable runs, from its `nm -ap` entries as built, and from `nm -ap` of a copy stripped like the archive (`strip`,
#     STRIP_STYLE all), except a run / symbol a statically linked SDK's own object holds byte for byte, and a run no more
#     often than that object does ($THIRD_PARTY_OBJS, default RC_OBJ; 'maze' / research words are never excused). An
#     unarchived build's debug-map stabs (source / object / module paths) are WATCH: the stripped copy must show them gone.
#     Planted control: a clang-built Mach-O carrying the words in a symbol, a literal and its debug map, plus an SDK object.
#     On the V1-app device Release product (14:42, pre-FIX-3) 7c FAILS with exactly V1A-G8-1/3's tells: 'maze', 'recorded',
#     'video' (+1 beyond RevenueCat.o's own), the two "recorded" log texts, 1,543 build-tree stabs as WATCH.
#  8. ad frameworks (META, OWNER 2026-09-29 19:33: the Meta SDK in 1.0 for the owner's app-install ads; memory meta-ads-sdk):
#     FacebookCore is ALLOWED as the owner-ordered Meta ATTRIBUTION SDK — exactly FBSDKCoreKit + FBSDKCoreKit_Basics + FBAEMKit
#     embedded, each binary's LC_UUIDs = the pinned 18.1.1 artifact's; no ad-SERVING SDK anywhere (GoogleMobileAds, Audience
#     Network, AppLovin, Unity Ads, ironSource, … and the unordered Login / Share / Gaming kits): not embedded, not loaded,
#     no ad-serving Info.plist key or identifier string; the Meta Info.plist keys hold their ruled values; FacebookClientToken
#     is 32 hex AND the factory .env's own (compared, never printed; an EMPTY token = OWNER ACTION / a verification build =
#     FAIL); PrivacyInfo tracking true with exactly ep1.facebook.com. Planted control: a bundle with GoogleMobileAds, its plist
#     key and a ca-app-pub string, a FacebookCore that is not the pinned build and an empty token must all be caught
#     (tools/bench/meta_sdk_check.py gate8).
#     META attribution in gates 2 / 2b / 7 / 7c: a hit inside a file PROVEN to be the pinned SDK's own (meta_sdk_check.py
#     attrib: framework binaries by LC_UUID, their other files byte-identical to the artifact's, the SPM resource bundles'
#     Info.plist platform names / byte-identical privacy manifests) is attributed, never a hit anywhere else; FB_ARTIFACTS /
#     FB_CHECKOUT point at the pinned artifacts when the .app was not built under build/dd-*; FacebookCore's statically linked
#     Swift overlay objects (FacebookCore.o / FacebookAEM.o / FacebookBasics.o) join 7c's THIRD_PARTY_OBJS default.
set -u
PC_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; export PC_ROOT          # 7b imports tools/strip_bundle_json.py
REL="${1:?usage: release_gates.sh <Release .app> [Debug .app]}"
DBG="${2:-}"
FAIL=0
BIN="$REL/ArrowOut"
[ -f "$BIN" ] || { echo "no binary at $BIN"; exit 2; }
TMP="${TMPDIR:-/tmp}/pc-gates.$$"; mkdir -p "$TMP"; trap 'rm -rf "$TMP"' EXIT
strings -a "$BIN" > "$TMP/rel.txt"
# RFIX 2026-09-29 (VERIFY F5): the attribution objects must be the ones THIS binary was linked from. SwiftPM builds a Measure
# build's package targets into the SAME Release-<platform> products folder (packages know only Debug / Release), so a Measure
# build in the same DerivedData rewrites or removes RevenueCat.o / FacebookCore.o / FacebookAEM.o after the Release link; gates
# 2 / 2b / 7c then attribute against the wrong objects or fail on a missing one (VERIFY run2: a false fakestore / privacy / ads
# failure). Refuse to judge — exit 2, never a pass — and say why: rebuild Release right before the gates. Skipped when the
# caller names the objects itself (RC_OBJ / THIRD_PARTY_OBJS, e.g. an archive's objects).
if [ -z "${RC_OBJ:-}${THIRD_PARTY_OBJS:-}" ]; then
  STALE=""
  want=""
  grep -q "_TtC10RevenueCat" "$TMP/rel.txt" && want="RevenueCat.o"
  grep -qx "FacebookCore" "$TMP/rel.txt" && want="$want FacebookCore.o"
  grep -qx "FacebookAEM" "$TMP/rel.txt" && want="$want FacebookAEM.o"
  for o in $want; do
    f="$(dirname "$REL")/$o"
    if [ ! -f "$f" ]; then STALE="$STALE $o (missing)"
    elif [ "$f" -nt "$BIN" ]; then STALE="$STALE $o (newer than the binary)"; fi
  done
  if [ -n "$STALE" ]; then
    echo "STALE PRODUCTS in $(dirname "$REL"):$STALE"
    echo "  a later build (a Measure build in the same DerivedData, VERIFY F5) changed the objects this binary was linked from:"
    echo "  rebuild Release and run the gates right after it. NOT JUDGED (exit 2)."
    exit 2
  fi
  echo "products preflight: $(echo $want | wc -w | tr -d ' ') attribution object(s) present and not newer than the binary"
fi
# A0: the RevenueCat attribution set (see the header, gate 2)
RC_OBJ="${RC_OBJ:-$(dirname "$REL")/RevenueCat.o}"
: > "$TMP/rc-hits.txt"
if grep -q "_TtC10RevenueCat" "$TMP/rel.txt"; then
  if [ -f "$RC_OBJ" ]; then
    strings -a "$RC_OBJ" | grep -i "simulat\|simüle\|bot " > "$TMP/rc-hits.txt"
    echo "RevenueCat linked: its hit strings come from $RC_OBJ ($(wc -l < "$TMP/rc-hits.txt" | tr -d ' ') lines)"
  else
    echo "RevenueCat linked but its object file is missing ($RC_OBJ): its strings cannot be attributed (set RC_OBJ) -> FAIL"
    FAIL=1; RC_OBJ=""
  fi
else
  RC_OBJ=""
fi
# META: the files of the bundle proven to be the pinned Facebook SDK's own (gates 2 / 2b / 7 attribute hits there only)
FB_JSON="$TMP/fb.json"; export FB_JSON
python3 "$PC_ROOT/tools/bench/meta_sdk_check.py" attrib "$REL" > "$FB_JSON" 2>/dev/null || echo '{"files": {}, "problems": ["meta_sdk_check.py attrib failed"]}' > "$FB_JSON"
FB_FILES="$TMP/fb-files.txt"
python3 -c 'import json,sys; [print(k) for k in json.load(open(sys.argv[1]))["files"]]' "$FB_JSON" > "$FB_FILES"
echo "FacebookCore (META): $(wc -l < "$FB_FILES" | tr -d ' ') bundle file(s) proven the pinned SDK's own; $(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["problems"]))' "$FB_JSON") unproven (gate 8 fails on those)"
FB_OBJS=""
for o in FacebookCore.o FacebookAEM.o FacebookBasics.o; do [ -f "$(dirname "$REL")/$o" ] && FB_OBJS="$FB_OBJS $(dirname "$REL")/$o"; done
THIRD_PARTY_OBJS="${THIRD_PARTY_OBJS:-$RC_OBJ$FB_OBJS}"
echo "Release app: $REL"
echo "binary: $(stat -f '%z bytes, %Sm' "$BIN"); dylibs in the app: $(ls "$REL" | grep -c 'debug.dylib') debug dylib(s)"

echo "== 1. dev placeholder"
# the control must be a literal of > 15 UTF-8 bytes (shorter Swift literals live inline in the code, invisible to `strings`):
# "cold launch summary" = the launch_done log mark (§9.3), printed by every build
n=$(grep -c "PC-DEBUG-PLACEHOLDER" "$TMP/rel.txt"); c=$(grep -c "cold launch summary" "$TMP/rel.txt")
echo "  Release: PC-DEBUG-PLACEHOLDER $n (must be 0); control 'cold launch summary' $c (must be > 0)"
[ "$n" -eq 0 ] && [ "$c" -gt 0 ] || FAIL=1
if [ -n "$DBG" ]; then
  d=0
  for f in "$DBG/ArrowOut" "$DBG/ArrowOut.debug.dylib"; do
    [ -f "$f" ] && d=$((d + $(strings -a "$f" | grep -c "PC-DEBUG-PLACEHOLDER")))
  done
  echo "  Debug control: PC-DEBUG-PLACEHOLDER $d (must be > 0: the grep sees the marker when it is compiled in)"
  [ "$d" -gt 0 ] || FAIL=1
fi

echo "== 2. honesty (simulat / simüle / bot )"
# the user-facing catalogues — B3 L10N-APP (2026-09-28): all 13 languages of SPEC.md ruling 37a (was en tr); each must exist
# and pass plutil -lint (the compiled Localizable.strings of every .lproj)
u=0
for l in en tr de fr es it pt-BR ja ko zh-Hans pl sk sl; do
  plutil -lint "$REL/$l.lproj/Localizable.strings" >/dev/null 2>&1 || { echo "  $l.lproj/Localizable.strings missing or not a valid plist"; FAIL=1; continue; }
  plutil -convert json -o "$TMP/$l.json" "$REL/$l.lproj/Localizable.strings" 2>/dev/null || { echo "  no $l catalogue"; FAIL=1; continue; }
  k=$(grep -ci "simulat\|simüle\|bot " "$TMP/$l.json"); u=$((u + k))
  echo "  $l.lproj/Localizable.strings: $k hit(s); $(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$TMP/$l.json") strings"
done
[ "$u" -eq 0 ] || FAIL=1
# the binary + every data file: list, then classify
: > "$TMP/honesty.txt"
grep -i "simulat\|simüle\|bot " "$TMP/rel.txt" | sed 's/^/binary: /' >> "$TMP/honesty.txt"
find "$REL" -type f \( -name '*.json' -o -name '*.txt' -o -name '*.tsv' -o -name '*.plist' \) | while read -r f; do
  r="${f#$REL/}"
  case "$f" in *.plist) plutil -convert xml1 -o - "$f" 2>/dev/null ;; *) cat "$f" ;; esac | grep -in "simulat\|simüle\|bot " | sed "s|^|$r:|" >> "$TMP/honesty.txt"
done
unexplained=0
while IFS= read -r line; do
  case "$line" in
    binary:*iphonesimulator*|binary:*ios-simulator*|binary:*iPhoneSimulator*) why="SDK platform name of a simulator build (absent from a device build)";;
    Info.plist:*"<string>iPhoneSimulator</string>"*|Info.plist:*"<string>iphonesimulator"*) why="Info.plist DTPlatformName / DTSDKName / CFBundleSupportedPlatforms of a simulator build (a device build says iPhoneOS)";;
    RevenueCat_RevenueCat.bundle/Info.plist:*"<string>iPhoneSimulator</string>"*|RevenueCat_RevenueCat.bundle/Info.plist:*"<string>iphonesimulator"*) why="the RevenueCat resource bundle's Info.plist platform names of a simulator build (a device build says iPhoneOS)";;
    Frameworks/FB*|Facebook_Facebook*.bundle/*) if grep -Fxq -- "${line%%:*}" "$FB_FILES"; then why="FacebookCore SDK file, proven the pinned 18.1.1 SDK's own (META; meta_sdk_check.py attrib)"; else why="UNEXPLAINED"; unexplained=$((unexplained + 1)); fi;;
    binary:*) if [ -s "$TMP/rc-hits.txt" ] && grep -Fxq -- "${line#binary: }" "$TMP/rc-hits.txt"; then why="RevenueCat SDK's own string (byte-identical in $(basename "$RC_OBJ"): developer log / Test Store code, never shown with an appl_ key)"
              elif [ "${line#binary: }" = "IPHONE_SIMULATOR_ROOT" ]; then why="simulator compiler-rt availability helper pulled in by RevenueCat.o (absent from a device build)"
              else why="UNEXPLAINED"; unexplained=$((unexplained + 1)); fi;;
    *) why="UNEXPLAINED"; unexplained=$((unexplained + 1));;
  esac
  echo "  $(echo "$line" | cut -c1-150)  -> $why"
done < "$TMP/honesty.txt"
echo "  total $(wc -l < "$TMP/honesty.txt" | tr -d ' ') hit(s), unexplained $unexplained (must be 0)"
[ "$unexplained" -eq 0 ] || FAIL=1
# 2b (V1-FINAL 2026-09-28): EVERY file of the bundle, binary-safe (macOS `strings -a` does not read the Mach-O symbol table,
# and the list above skips Assets.car, fonts, sounds …). Each NUL-delimited string that carries a hit is classified; anything
# else fails. Measured on build-4: the simulator binary's symbol table holds ~700 toolchain/DerivedData paths with
# "iphonesimulator" (debug-map stabs); an unsigned device-SDK Release build of the same tree had 0 hits in its binary and
# Info.plist, and only the Assets.car stamp below (build/v1/final/device-sdk-check.log).
python3 - "$REL" "$RC_OBJ" <<'PY' || FAIL=1
import os, re, sys, collections
root = sys.argv[1]; hit = re.compile(rb'(?i)simulat|sim\xc3\xbcle|bot ')
why = collections.Counter(); bad = []
def segs(b):
    out = set()
    for m in hit.finditer(b):
        s = b.rfind(b'\0', 0, m.start()) + 1; e = b.find(b'\0', m.end()); out.add(b[s:(e if e >= 0 else len(b))])
    return out
# A0: every NUL-delimited hit string of the pinned RevenueCat object file (empty when RevenueCat is not linked)
rc = segs(open(sys.argv[2], 'rb').read()) if len(sys.argv) > 2 and sys.argv[2] else set()
import json
fb = json.load(open(os.environ['FB_JSON']))['files'] if os.environ.get('FB_JSON') else {}      # META: the pinned SDK's own files
for d, _, fs in os.walk(root):
    for f in fs:
        p = os.path.join(d, f); r = os.path.relpath(p, root); b = open(p, 'rb').read()
        for m in hit.finditer(b):
            s = b.rfind(b'\0', 0, m.start()) + 1; e = b.find(b'\0', m.end()); t = b[s:(e if e >= 0 else len(b))]
            if r == 'ArrowOut' and b'/' in t and b'iphonesimulator' in t.lower():
                k = 'binary: toolchain / DerivedData path of a simulator build (symbol-table debug map; absent from a device build)'
            elif r == 'ArrowOut' and re.search(rb'(x86_64|arm64)-apple-ios-simulator', t):
                k = 'binary: Swift target triple of a simulator build (absent from a device build)'
            elif r == 'ArrowOut' and t in rc:
                k = 'binary: RevenueCat SDK string, byte-identical in the pinned RevenueCat.o (developer log / Test Store code / symbols)'
            elif r == 'ArrowOut' and rc and t == b'IPHONE_SIMULATOR_ROOT':
                k = 'binary: simulator compiler-rt availability helper pulled in by RevenueCat.o (absent from a device build)'
            elif r in fb:
                k = 'FacebookCore SDK file proven the pinned 18.1.1 SDK\'s own (META: %s)' % fb[r].split(' (')[0]
            elif r == 'RevenueCat_RevenueCat.bundle/Info.plist' and re.search(rb'iphonesimulator|iPhoneSimulator', t):
                k = 'RevenueCat_RevenueCat.bundle/Info.plist: platform names of a simulator build'
            elif r == 'Info.plist' and re.search(rb'iphonesimulator|iPhoneSimulator', t):
                k = 'Info.plist: DTPlatformName / DTSDKName / CFBundleSupportedPlatforms of a simulator build'
            elif r.endswith('Assets.car') and b'via AssetCatalogSimulatorAgent' in t:
                k = 'Assets.car: AssetStorageVersion stamp of Xcode\'s asset compiler (every Xcode-built catalog, device too; never displayed)'
            else:
                bad.append('%s: %s' % (r, re.sub(rb'[^\x20-\x7e]', b'.', t[:150]).decode()))
                continue
            why[k] += 1
for k, n in why.most_common(): print('  %5d  %s' % (n, k))
for x in bad: print('  UNEXPLAINED  %s' % x)
print('  whole-bundle sweep: %d hit(s), unexplained %d (must be 0)' % (sum(why.values()) + len(bad), len(bad)))
sys.exit(1 if bad else 0)
PY

echo "== 3. brand"
b=$(grep -c "Maze\|MazeOut\|Arrow Jam\|Grand Games\|grandgames\|arrowjam" "$TMP/rel.txt"); a=$(grep -c "Arrow Out" "$TMP/rel.txt")
echo "  binary: original's names $b (must be 0); 'Arrow Out' literal $a (must be 0)"
[ "$b" -eq 0 ] && [ "$a" -eq 0 ] || FAIL=1
names=$(find "$REL" -mindepth 1 | sed "s|^$REL/||" | grep -i "maze\|grand\|arrowjam" | wc -l | tr -d ' ')
echo "  file names with maze/grand/arrowjam: $names (must be 0)"
[ "$names" -eq 0 ] || FAIL=1
bad=0
for f in $(find "$REL" -type f \( -name '*.json' -o -name '*.txt' -o -name '*.tsv' -o -name '*.strings' \)); do
  r="${f#$REL/}"
  case "$f" in *.strings) plutil -convert json -o - "$f" 2>/dev/null ;; *) cat "$f" ;; esac > "$TMP/one.txt"
  if grep -qi "mazeout\|maze out\|arrow jam\|arrowjam\|grand games\|grandgames" "$TMP/one.txt" || grep -q "Maze" "$TMP/one.txt"; then
    # B2 (PLAN-P G4(c)): no exception — the shipped name bank stores the original's names hashed (soc_ship_names.py)
    echo "  $r: ORIGINAL'S NAME"; bad=$((bad + 1))
  fi
done
echo "  data files with the original's names: $bad (must be 0; no file is exempt)"
[ "$bad" -eq 0 ] || FAIL=1
plutil -p "$REL/Info.plist" | grep -E '"(CFBundleDisplayName|PCBrandName)"' | sed 's/^/  Info.plist /'

echo "== 7. provenance (research paths, capture keys, the original's version tags, lab fixtures)"
python3 - "$REL" "$RC_OBJ" <<'PY' || FAIL=1
import os, re, sys, tempfile
EVERY = re.compile(rb'research/|video-frames|v552|v582')
# FIX-2 B review (N-01): the research readers' vocabulary — the bot's metric key, the phone / video schema names and the
# research JSON's pixel keys — in ANY file, the executable included (PathCore compiles them for macOS tools only: PC_RESEARCH)
RESEARCH = re.compile(rb'bot_time|phone nor video|phone JSON|pitch_pt|bbox_px')
# ... and, in text files, a level's research keys: where it was read (source recorded / video) and how it was measured
TEXT_KEYS = re.compile(rb'"(shot|capture|reader|anomalies|occlusion_inferred|source|metrics)"\s*:')
TEXT_EXT = {'.json', '.tsv', '.txt', '.strings', '.plist', '.csv', '.md'}
# ... and (the N-01 ledger: "scan the binary's strings for phone / video / bot_ provenance words in log text") every
# printable string of a Mach-O file that reads like a message (it has a space) and says phone / video / bot_, unless the
# statically linked RevenueCat SDK's object file holds the same string byte for byte (its paywall-video code and logs)
LOGWORD = re.compile(rb'(?i)(?<![a-z])(phone|video|bot_)')
PRINTABLE = re.compile(rb'[\x20-\x7e]{6,}')
RC = set(PRINTABLE.findall(open(sys.argv[2], 'rb').read())) if len(sys.argv) > 2 and sys.argv[2] and os.path.exists(sys.argv[2]) else set()
LAB = re.compile(r'^labb?_L\d+\.json$')
import json
FB = json.load(open(os.environ['FB_JSON']))['files'] if os.environ.get('FB_JSON') else {}      # META (see the header)

def scan(root):
    hits, labs = [], []
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f); r = os.path.relpath(p, root)
            if LAB.match(f): labs.append(r)
            b = open(p, 'rb').read()
            pats = [EVERY, RESEARCH] + ([TEXT_KEYS] if os.path.splitext(f)[1].lower() in TEXT_EXT else [])
            if b[:4] in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe') and r not in FB:   # Mach-O: its message strings
                # (META: a framework binary proven the pinned Facebook SDK's own by LC_UUID is Meta's text, attributed)
                for st in PRINTABLE.findall(b):
                    if b' ' in st and LOGWORD.search(st) and st not in RC:
                        hits.append((r, 'log text: ' + LOGWORD.search(st).group(0).decode(), st[:120].decode('latin-1')))
            for pat in pats:
                for m in pat.finditer(b):
                    s = max(b.rfind(b'\0', 0, m.start()) + 1, m.start() - 60); e = b.find(b'\0', m.end())
                    e = min(e if e >= 0 else len(b), m.end() + 60)
                    hits.append((r, m.group(0).decode('latin-1'), re.sub(rb'[^\x20-\x7e]', b'.', b[s:e]).decode()))
    return hits, labs

# control: the scanner must see a planted research path + capture key in a level file and a version tag in a binary blob
with tempfile.TemporaryDirectory() as t:
    os.makedirs(os.path.join(t, 'Levels'))
    open(os.path.join(t, 'Levels', 'level_9999.json'), 'w').write('{"level":9999,"capture":"research/shots/001-L1-start.png"}')
    open(os.path.join(t, 'planted.bin'), 'wb').write(b'\x00\xcf\xfa\xed\xfe\x00built from v582\x00')
    open(os.path.join(t, 'lab_L032.json'), 'w').write('{}')
    # N-01 plants: the old publish form of a level (source + the bot's metrics) and the binary's old error string
    open(os.path.join(t, 'Levels', 'level_9998.json'), 'w').write('{"level":9998,"metrics":{"bot_time_left":166.8},"source":"recorded"}')
    open(os.path.join(t, 'planted2.bin'), 'wb').write(b'\x00level JSON: neither bundle, phone nor video schema\x00bot_time_left\x00')
    open(os.path.join(t, 'planted3.bin'), 'wb').write(b'\xcf\xfa\xed\xfe\x00\x00: counter missing (not in the phone JSON)\x00')
    ch, cl = scan(t)
    seen = {(r, k) for r, k, _ in ch}
    control = {('Levels/level_9999.json', 'research/'), ('Levels/level_9999.json', '"capture":'), ('planted.bin', 'v582'),
               ('Levels/level_9998.json', '"source":'), ('Levels/level_9998.json', '"metrics":'), ('Levels/level_9998.json', 'bot_time'),
               ('planted2.bin', 'phone nor video'), ('planted2.bin', 'bot_time'), ('planted3.bin', 'log text: phone')} <= seen \
              and cl == ['lab_L032.json']
print('  control (planted sample): %s' % ('caught' if control else 'NOT CAUGHT -> the scanner is blind'))
hits, labs = scan(sys.argv[1])
for r, k, ctx in hits[:40]: print('  HIT  %s  %r  …%s…' % (r, k, ctx))
if len(hits) > 40: print('  … %d more' % (len(hits) - 40))
for r in labs: print('  LAB FIXTURE  %s' % r)
files = sum(len(fs) for _, _, fs in os.walk(sys.argv[1]))
print('  %d files scanned: %d provenance hit(s), %d lab fixture(s) (both must be 0)' % (files, len(hits), len(labs)))

# 7b (F3-B 2026-09-29): bundled-JSON key hygiene. The art sync (tools/sync_art.sh) strips the art JSON's NON-RUNTIME keys at
# sync time (tools/strip_bundle_json.py: "note" / "notes" / "baked" / "proof" / "replaces", "_" comments, capture-provenance
# keys); every JSON under Art/ and UI/ must carry none. Every OTHER bundled JSON (App/Resources: Levels, Tuning, Social) must
# carry no "replaces" and no capture-provenance key; its "_" / "note" developer comments (Tuning/*.json, Levels/curve.json;
# the Resources phase copies them as-is) are listed as WATCH, not failed: their text is scanned above and by gates 2 / 3.
# F3-A: they FAIL now (App/Resources is stripped at the source, TuningTests.testShippedResourceJSONCarriesNoDeveloperNotes),
# except KEPT = Levels/curve.json /_about (B0's ruling curve:_comment); a curve.json with any other comment key fails.
# Control: a planted Art/ rig.json with a layer "note", a char_*.json with "replaces" and a "_from", and a Tuning JSON with a
# "replaces" must all be reported, a clean planted Art/ JSON must not, or the gate FAILS (the scan can see what it looks for).
import importlib.util, json
sp = importlib.util.spec_from_file_location('strip_bundle_json', os.path.join(os.environ.get('PC_ROOT', '.'), 'tools', 'strip_bundle_json.py'))
sbj = importlib.util.module_from_spec(sp); sp.loader.exec_module(sbj)
ALWAYS = {'replaces'} | sbj.PROVENANCE_KEYS
KEPT = {('Levels/curve.json', '/_about')}                     # F3-A: B0's ruled exception (the compiled curve's own comment)

def json_keys(root):
    fail, watch = [], []
    for d, _, fs in os.walk(root):
        for f in sorted(fs):
            if not f.endswith('.json'): continue
            p = os.path.join(d, f); r = os.path.relpath(p, root)
            try: obj = json.load(open(p, 'rb'))
            except Exception as e: fail.append((r, 'unreadable JSON: %s' % e)); continue
            art = r.split(os.sep)[0] in ('Art', 'UI')
            for path, k in sbj.non_runtime_keys(obj):
                (watch if (r, path) in KEPT and not art and k not in ALWAYS else fail).append((r, path))
    return fail, watch

with tempfile.TemporaryDirectory() as t:
    os.makedirs(os.path.join(t, 'Art', 'x_rig')); os.makedirs(os.path.join(t, 'Tuning'))
    json.dump({'frame_pt': [1, 2], 'layers': [{'name': 'a', 'file': 'a@3x.png', 'rect_pt': [0, 0, 1, 1], 'note': 'n'}]}, open(os.path.join(t, 'Art', 'x_rig', 'rig.json'), 'w'))
    json.dump({'characters': {'c': {'file': 'c@3x.png', 'replaces': 'char_old'}}, '_from': 'x'}, open(os.path.join(t, 'Art', 'char_x.json'), 'w'))
    json.dump({'case': 'char_ok', 'frame_pt': [1, 2]}, open(os.path.join(t, 'Art', 'char_ok.json'), 'w'))
    json.dump({'k': {'replaces': 'y'}, '_about': 'dev note'}, open(os.path.join(t, 'Tuning', 'x.json'), 'w'))
    # F3-A: a Tuning layer "note" fails; curve.json's "_about" is KEPT, its any other comment key fails
    os.makedirs(os.path.join(t, 'Levels'))
    json.dump({'win': {'layers': {'a': {'z': 1, 'note': 'dev'}}}}, open(os.path.join(t, 'Tuning', 'y.json'), 'w'))
    json.dump({'_about': 'curve', '_from': 'x', 'salt': 1}, open(os.path.join(t, 'Levels', 'curve.json'), 'w'))
    cf, cw = json_keys(t)
    seen = set(cf)
    kcontrol = {('Art/x_rig/rig.json', '/layers[0]/note'), ('Art/char_x.json', '/characters/c/replaces'), ('Art/char_x.json', '/_from'),
                ('Tuning/x.json', '/k/replaces'), ('Tuning/x.json', '/_about'), ('Tuning/y.json', '/win/layers/a/note'),
                ('Levels/curve.json', '/_from')} <= seen and not any(r == 'Art/char_ok.json' for r, _ in cf) \
               and set(cw) == {('Levels/curve.json', '/_about')}
print('  7b bundled-JSON keys: control (planted sample) %s' % ('caught' if kcontrol else 'NOT CAUGHT -> the key scan is blind'))
kf, kw = json_keys(sys.argv[1])
for r, p in kf[:30]: print('  KEY  %s  %s' % (r, p))
if len(kf) > 30: print('  … %d more' % (len(kf) - 30))
wf = sorted({r for r, _ in kw})
print('  KEPT   ruled developer comment(s) (B0: curve.json = the compiled CurveSpec.default): %s' % (', '.join('%s %s' % (r, p) for r, p in kw) or 'none'))
njson = sum(1 for _, _, fs in os.walk(sys.argv[1]) for f in fs if f.endswith('.json'))
print('  7b: %d bundled JSON file(s): %d non-runtime key(s) outside the ruled exception (must be 0)' % (njson, len(kf)))
sys.exit(0 if control and not hits and not labs and kcontrol and not kf else 1)
PY

# 7c (FIX-3 B, see the header): the main binary's words, its nm symbols as built, and nm of an archive-style stripped copy.
# THIRD_PARTY_OBJS: the object files of statically linked SDKs whose own runs / symbols are attributed (default RC_OBJ).
echo "== 7c. binary words + nm symbols (as built, and stripped like the archive)"
python3 - "$BIN" ${THIRD_PARTY_OBJS:-$RC_OBJ} <<'PY' || FAIL=1
import collections, os, re, shutil, subprocess, sys, tempfile
WORDS = re.compile(rb'(?i)maze|recorded|video|research/|v552|v582|bot_time')
NEVER_SDK = re.compile(rb'(?i)maze|research/|v552|v582|bot_time')     # never excused by an SDK match (our tree / title / research)
RUN = re.compile(rb'[\x20-\x7e]{4,}')
STAB = re.compile(rb'^[0-9a-f ]{16} - [0-9a-f]{2} [0-9a-f]{4} +(\S+) ?(.*)$')
SYM = re.compile(rb'^[0-9a-f ]{16} (\S) (.*)$')

def nm(path):
    """[(kind, name)]: kind 'stab:<TYPE>' for a debug-map entry, else nm's type letter; None when nm fails."""
    r = subprocess.run(['nm', '-ap', path], capture_output=True)
    if r.returncode != 0: return None
    out = []
    for ln in r.stdout.splitlines():
        m = STAB.match(ln)
        if m: out.append(('stab:' + m.group(1).decode(), m.group(2))); continue
        m = SYM.match(ln)
        if m: out.append((m.group(1).decode(), m.group(2)))
    return out

def strings_a(path):
    """`strings -a -n 4` as a multiset of runs (None when it fails)."""
    r = subprocess.run(['strings', '-a', '-n', '4', path], capture_output=True)
    return collections.Counter(r.stdout.splitlines()) if r.returncode == 0 else None

def scan(binp, third):
    """(fail, watch, attributed, stripped_fail, stripped_nm_count) for one Mach-O.
    fail: `strings -a` runs + nm entries (as built) with a word; watch: the debug map's entries with a word (as built);
    stripped_fail: the archive-style stripped copy's nm entries with a word, and its raw printable runs (load commands,
    what is left of the symbol table, the signature) with a word that no SDK can excuse (maze / research / version tags).
    Its SECTIONS are the unstripped binary's (strip only drops symbols), so their recorded / video runs are `strings -a`'s,
    attributed by exact run: a raw run is cut at any non-printable byte (Swift's symbolic references split mangled names),
    so raw fragments of the SDK's names cannot be matched exactly and are not scanned for the SDK-excusable words."""
    tp, tpn = set(), collections.Counter()
    for o in third:
        tp |= set(RUN.findall(open(o, 'rb').read())) | {n for _, n in (nm(o) or [])}
        tpn += strings_a(o) or collections.Counter()
    def sdk(x): return x in tp and not NEVER_SDK.search(x)
    fail, watch, attr = [], [], []
    runs = strings_a(binp)
    if runs is None: fail.append(('strings', b'strings -a could not read the binary'))
    for run, k in sorted((runs or {}).items()):
        if not WORDS.search(run): continue
        # attributed only up to the SDK's own count of that exact run: a run the SDK also spells ("video") that the binary
        # carries MORE often than the SDK's object is ours too (V1A-G8-3's raw value hid behind RevenueCat's own "video")
        own = 0 if NEVER_SDK.search(run) else min(k, tpn[run])
        if own: attr.append(('strings', run))
        if k > own: fail.append(('strings' if not own else 'strings+%d' % (k - own), run))
    built = nm(binp)
    if built is None: fail.append(('nm', b'nm could not read the binary'))
    for kind, name in built or []:
        if not WORDS.search(name): continue
        if kind.startswith('stab:') or kind == 'a': watch.append((kind, name))      # an unarchived build's debug map
        elif sdk(name): attr.append(('nm ' + kind, name))
        else: fail.append(('nm ' + kind, name))
    sfail, nstrip = [], 0
    with tempfile.TemporaryDirectory() as t:
        q = os.path.join(t, 'stripped'); shutil.copyfile(binp, q)
        if subprocess.run(['strip', q], capture_output=True).returncode != 0:
            sfail.append(('strip', b'strip failed on a copy'))
        else:
            after = nm(q) or []
            nstrip = len(after)
            sfail += [('nm ' + k, n) for k, n in after if WORDS.search(n) and not sdk(n)]
            sfail += [('bytes', r) for r in sorted(set(RUN.findall(open(q, 'rb').read()))) if NEVER_SDK.search(r)]
    return fail, watch, attr, sfail, nstrip

# control: a planted Mach-O built here — its source folder is named like the tree (so its debug map carries it), a function
# and a literal carry the words; a planted third-party object holds one more literal, which must be attributed, not failed
control = False
with tempfile.TemporaryDirectory() as t:
    d = os.path.join(t, 'apps', 'mazeout-ctl'); os.makedirs(d)
    open(os.path.join(d, 'ctl.c'), 'w').write('const char *msg = "a recorded video of the maze";\n'
        'const char *sdk = "third party video text";\nint recorded_video_maze(void) { return msg[0] + sdk[0]; }\n'
        'int main(void) { return recorded_video_maze(); }\n')
    open(os.path.join(d, 'sdk.c'), 'w').write('const char *sdk = "third party video text";\n')
    ok = subprocess.run(['xcrun', 'clang', '-g', '-O0', 'ctl.c', '-o', 'ctl'], cwd=d, capture_output=True).returncode == 0 \
         and subprocess.run(['xcrun', 'clang', '-c', 'sdk.c', '-o', 'sdk.o'], cwd=d, capture_output=True).returncode == 0
    if ok:
        cf, cw, ca, cs, _ = scan(os.path.join(d, 'ctl'), [os.path.join(d, 'sdk.o')])
        control = any(k == 'strings' and b'a recorded video of the maze' in n for k, n in cf) \
            and any(k.startswith('nm ') and b'recorded_video_maze' in n for k, n in cf) \
            and any(b'mazeout-ctl' in n for _, n in cw) \
            and any(b'third party video text' in n for _, n in ca) and not any(b'third party video text' in n for _, n in cf + cs) \
            and any(k == 'bytes' and b'a recorded video of the maze' in n for k, n in cs) and not any(b'mazeout-ctl' in n for _, n in cs)
print('  7c control (planted Mach-O: literal, symbol, debug map, SDK attribution, strip): %s'
      % ('caught' if control else 'NOT CAUGHT -> the scan is blind (or clang / nm / strip unavailable)'))
third = [o for o in sys.argv[2:] if o and os.path.exists(o)]
fail, watch, attr, sfail, nstrip = scan(sys.argv[1], third)
def show(n): return re.sub(rb'[^\x20-\x7e]', b'.', n[:150]).decode()
for k, n in fail[:30]: print('  HIT  %-9s %s' % (k, show(n)))
if len(fail) > 30: print('  … %d more' % (len(fail) - 30))
for k, n in sfail[:30]: print('  HIT  stripped %-9s %s' % (k, show(n)))
if len(sfail) > 30: print('  … %d more' % (len(sfail) - 30))
tree = sum(1 for _, n in watch if b'/apps/mazeout/' in n)
print('  third-party attributed (byte-identical in %s; never a maze / research hit): %d run(s) / symbol(s)'
      % (', '.join(os.path.basename(o) for o in third) or 'none', len(attr)))
print("  WATCH  as built: %d debug-map entr%s carry a word (%d name the build tree /apps/mazeout/): an unarchived build's "
      "debug map, which the archive strip removes (the stripped copy below proves it)" % (len(watch), 'y' if len(watch) == 1 else 'ies', tree))
print("  stripped copy (the archive's strip, STRIP_STYLE all): %d nm entries; %d unattributed hit(s) in its nm + bytes (must be 0)" % (nstrip, len(sfail)))
print("  7c: %d unattributed hit(s) in the binary's strings -a / nm as built (must be 0)" % len(fail))
sys.exit(0 if control and not fail and not sfail else 1)
PY

# 8 (META, see the header): FacebookCore allowed as the owner-ordered attribution SDK, no ad-serving SDK; planted control.
echo "== 8. ad frameworks (FacebookCore = the owner-ordered Meta attribution SDK; no ad-SERVING SDK)"
python3 "$PC_ROOT/tools/bench/meta_sdk_check.py" gate8 "$REL" || FAIL=1

echo "== RESULT: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $FAIL
