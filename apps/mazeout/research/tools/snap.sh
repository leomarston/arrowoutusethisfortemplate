#!/bin/sh
# snap.sh NNN NAME [ocr]  → shots/NNN-social-HHMMSS-NAME.png (lossless) + scratchpad/s.png (393x852) [+ OCR lines]
R=/Users/yago/Downloads/app-factory/apps/mazeout/research; P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone
SP=/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad
T=$(date +%H%M%S); F=$R/shots/$1-social-$T-$2.png
perl -e 'alarm shift; exec @ARGV' 40 $P shot $F >/dev/null || { echo "SHOT FAILED"; exit 1; }
python3 -c "from PIL import Image; Image.open('$F').resize((393,852)).save('$SP/s.png')"
echo "$F"
[ "$3" = ocr ] && $R/tools/ocr $F
exit 0
