#!/bin/sh
# mshot.sh NAME [W H X Y]  -> research/shots/meta-NNN-NAME.png (next NNN) + scratchpad view (393x852, or crop X Y W H in pt at 3x zoom)
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; R=/Users/yago/Downloads/app-factory/apps/mazeout/research
V=/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad
N=$(ls $R/shots | grep -E '^meta-[0-9]{3}' | sed -E 's/^meta-([0-9]{3}).*/\1/' | sort -n | tail -1); N=$(printf %03d $((10#${N:-0}+1)))
O=$R/shots/meta-$N-$1.png
perl -e 'alarm shift; exec @ARGV' 40 $P shot $O >/dev/null || { echo SHOT_FAILED; exit 1; }
python3 - "$O" "$V/view.png" "$2" "$3" "$4" "$5" <<'PY'
import sys
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB')
if sys.argv[3]:
    w,h,x,y=[float(v) for v in sys.argv[3:7]]; s=1178/393
    im=im.crop((int(x*s),int(y*s),int((x+w)*s),int((y+h)*s)))
else:
    im=im.resize((393,852),Image.LANCZOS)
im.save(sys.argv[2])
PY
echo "$(date +%H:%M:%S) $O"
