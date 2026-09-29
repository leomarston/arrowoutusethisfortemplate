#!/bin/sh
# Waits (max ~14 min) until other owners' files have been quiet for 90 s and swap has >= 400 MB free, then builds the
# scratch copy; retries a failed build after the next quiet window.
cd "$(dirname "$0")/../.."
for attempt in 1 2 3 4 5; do
  i=0
  while :; do
    now=$(date +%s)
    newest=$(find App/Shell App/Board App/Audio App/FX App/Support App/Contracts Packages/MFCore/Sources -name '*.swift' -exec stat -f %m {} + | sort -n | tail -1)
    free=$(sysctl vm.swapusage | awk '{print $10}' | tr -d M | cut -d. -f1)
    [ $((now - newest)) -ge 90 ] && [ "${free:-0}" -ge 400 ] && break
    i=$((i + 1)); [ $i -ge 60 ] && break
    sleep 5
  done
  echo "attempt $attempt quiet=$((now - newest))s swapfree=${free}M $(date +%H:%M:%S)"
  if ./build/g1/iso.sh build-for-testing > build/g1/iso-build.log 2>&1; then echo "BUILD OK $(date +%H:%M:%S)"; exit 0; fi
  grep -E "error:" build/g1/iso-build.log | head -3
done
echo "BUILD GAVE UP"; exit 1
