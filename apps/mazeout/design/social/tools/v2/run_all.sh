#!/bin/zsh
# run_all.sh — T6's whole verification of the v2 world, niced, one step at a time, logs + evidence in build/p/T6/.
#   zsh design/social/tools/v2/run_all.sh [quick]
# Steps: country table -> name data -> tests.py (reference, v552, v2) -> byte-identity of the pinned goldens -> calibration
# (phone guards at the same world age + per-country realism at 3 reference weeks) -> real-name Monte Carlo -> the v2 goldens
# (staging, for B2) -> the whole-world name audit to 2031.
set -u
APP=${0:A:h}/../../../..
APP=${APP:A}
T=$APP/design/social/tools
OUT=$APP/build/p/T6
mkdir -p $OUT
cd $APP
step() { echo "[$(date +%H:%M:%S)] $*" | tee -a $OUT/run_all.log; }
step countries; nice -n 19 python3 $T/v2/build_countries_v2.py > $OUT/countries.log 2>&1 || step "countries FAILED"
step names; nice -n 19 python3 $T/v2/build_name_data_v2.py > $OUT/names.log 2>&1 || step "names FAILED"
for m in reference v552 v2; do
  step "tests $m"; (cd $T && nice -n 19 python3 tests.py $m > $OUT/tests_$m.log 2>&1); tail -1 $OUT/tests_$m.log | tee -a $OUT/run_all.log
done
step identity; nice -n 19 python3 $T/v2/identity_check.py --out $OUT > $OUT/identity.log 2>&1; tail -2 $OUT/identity.log | tee -a $OUT/run_all.log
if [[ ${1:-} == quick ]]; then
  step calib-quick; nice -n 19 python3 $T/v2/calib_v2.py $OUT/calib_quick.json --quick > $OUT/calib.log 2>&1
else
  step calib; nice -n 19 python3 $T/v2/calib_v2.py $OUT/calib.json > $OUT/calib.log 2>&1
fi
tail -30 $OUT/calib.log | tee -a $OUT/run_all.log
step names-mc; nice -n 19 python3 $T/v2/names_mc.py $OUT/names_mc.json > $OUT/names_mc.log 2>&1
step fixtures; nice -n 19 python3 $T/v2/fixtures_v2.py $OUT/fixtures_v2 > $OUT/fixtures_v2.log 2>&1; tail -3 $OUT/fixtures_v2.log | tee -a $OUT/run_all.log
if [[ ${1:-} != quick ]]; then
  step name-audit; (cd $T && nice -n 19 python3 name_audit.py 2031-09-25 --v2 > $OUT/name_audit.log 2>&1)
  cp $APP/design/social/bench/name_audit_v2_2031-09-25.json $OUT/ 2>/dev/null
  grep -E '"verdict"|"blocked_shown"|"longer_than_16"|"players"' $OUT/name_audit.log | tee -a $OUT/run_all.log
fi
step acceptance; nice -n 19 python3 $T/v2/acceptance.py $OUT > $OUT/acceptance.log 2>&1
step done
