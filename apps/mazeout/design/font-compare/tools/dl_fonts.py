"""Download google/fonts family folders (TTFs + OFL.txt/LICENSE.txt + METADATA.pb) with curl via the GitHub contents API.
Run inside $FONTCOMPARE_WORK/gf.  usage: dl_fonts.py ofl/nunito apache/chewy ..."""
import json, subprocess, sys, os, urllib.parse
dirs=sys.argv[1:]
for d in dirs:
    out=subprocess.run(['curl','-sS','-m','30','https://api.github.com/repos/google/fonts/contents/'+d],capture_output=True,text=True).stdout
    try: items=json.loads(out)
    except Exception: print('FAIL',d,out[:200]); continue
    if isinstance(items,dict): print('ERR',d,items.get('message')); continue
    os.makedirs(d,exist_ok=True)
    for it in items:
        n=it['name']
        if n.endswith('.ttf') or n in('OFL.txt','LICENSE.txt','METADATA.pb'):
            if os.path.exists(d+'/'+n): continue
            subprocess.run(['curl','-sS','-m','60','-o',d+'/'+n,it['download_url']])
    print(d, sorted(os.listdir(d)))
