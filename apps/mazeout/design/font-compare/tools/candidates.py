"""Candidate registry for the Maze Out font match: (family, file, postscript-name-or-None, fixed axes, weight->axes/ps mapping).
Adapted from apps/arrows/design/font-compare/tools/candidates.py (commit 8e77f85): new candidate list (heavy rounded
display faces), google/fonts directory layout (gf/<licence>/<family>/<file>)."""
import os
WORK=os.environ.get('FONTCOMPARE_WORK', '/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad/fc/').rstrip('/')+'/'
GF=WORK+'gf/'   # downloaded Google Fonts TTFs: gf/ofl/<dir>/<file>, gf/apache/<dir>/<file>
SYS='/System/Library/Fonts/'
def vf(family, fname, lo, hi, extra=None, opsz=None, lic='OFL'):
    return dict(family=family, kind='vf', file=GF+fname if not fname.startswith('/') else fname, lo=lo, hi=hi, extra=extra or {}, opsz=opsz, lic=lic)
def st(family, faces, lic='OFL'):   # faces: {weight: (file, postscriptName or None)}
    return dict(family=family, kind='static', faces={w:(GF+f if not f.startswith('/') else f, ps) for w,(f,ps) in faces.items()}, lic=lic)
def one(family, fname, lic='OFL', w=400):
    return st(family, {w:(fname, None)}, lic)
C=[
 # --- the brief's list ---
 one('Lilita One','ofl/lilitaone/LilitaOne-Regular.ttf'),
 one('Titan One','ofl/titanone/TitanOne-Regular.ttf'),
 one('Luckiest Guy','apache/luckiestguy/LuckiestGuy-Regular.ttf', lic='Apache-2.0'),
 vf('Fredoka','ofl/fredoka/Fredoka[wdth,wght].ttf',300,700),
 vf('Baloo 2','ofl/baloo2/Baloo2[wght].ttf',400,800),
 vf('Baloo Bhai 2','ofl/baloobhai2/BalooBhai2[wght].ttf',400,800),
 one('Chewy','apache/chewy/Chewy-Regular.ttf', lic='Apache-2.0'),
 one('Carter One','ofl/carterone/CarterOne.ttf'),
 st('Passion One',{400:('ofl/passionone/PassionOne-Regular.ttf',None),700:('ofl/passionone/PassionOne-Bold.ttf',None),900:('ofl/passionone/PassionOne-Black.ttf',None)}),
 one('Paytone One','ofl/paytoneone/PaytoneOne-Regular.ttf'),
 vf('Rubik','ofl/rubik/Rubik[wght].ttf',300,900),
 vf('Nunito','ofl/nunito/Nunito[wght].ttf',200,1000),
 vf('Grandstander','ofl/grandstander/Grandstander[wght].ttf',100,900),
 st('Sniglet',{400:('ofl/sniglet/Sniglet-Regular.ttf',None),800:('ofl/sniglet/Sniglet-ExtraBold.ttf',None)}),
 one('Changa One','ofl/changaone/ChangaOne-Regular.ttf'),
 one('Galindo','ofl/galindo/Galindo-Regular.ttf'),
 one('Coiny','ofl/coiny/Coiny-Regular.ttf'),
 one('Rammetto One','ofl/rammettoone/RammettoOne-Regular.ttf'),
 one('Bubblegum Sans','ofl/bubblegumsans/BubblegumSans-Regular.ttf'),
 vf('Gluten','ofl/gluten/Gluten[slnt,wght].ttf',100,900),
 one('Madimi One','ofl/madimione/MadimiOne-Regular.ttf'),
 one('Dela Gothic One','ofl/delagothicone/DelaGothicOne-Regular.ttf'),
 one('Bowlby One','ofl/bowlbyone/BowlbyOne-Regular.ttf'),
 one('Bungee','ofl/bungee/Bungee-Regular.ttf'),
 one('Chango','ofl/chango/Chango-Regular.ttf'),
 one('Knewave','ofl/knewave/Knewave-Regular.ttf'),
 vf('Signika','ofl/signika/Signika[GRAD,wght].ttf',300,700),
 # --- extra rounded / heavy OFL faces ---
 st('M PLUS Rounded 1c',{w:('ofl/mplusrounded1c/MPLUSRounded1c-%s.ttf'%n,None) for w,n in [(400,'Regular'),(500,'Medium'),(700,'Bold'),(800,'ExtraBold'),(900,'Black')]}),
 one('Varela Round','ofl/varelaround/VarelaRound-Regular.ttf'),
 st('Zen Maru Gothic',{w:('ofl/zenmarugothic/ZenMaruGothic-%s.ttf'%n,None) for w,n in [(400,'Regular'),(500,'Medium'),(700,'Bold'),(900,'Black')]}),
 one('Mochiy Pop One','ofl/mochiypopone/MochiyPopOne-Regular.ttf'),
 vf('Dosis','ofl/dosis/Dosis[wght].ttf',200,800),
 one('Poetsen One','ofl/poetsenone/PoetsenOne-Regular.ttf'),
 one('Bagel Fat One','ofl/bagelfatone/BagelFatOne-Regular.ttf'),
 st('Rowdies',{300:('ofl/rowdies/Rowdies-Light.ttf',None),400:('ofl/rowdies/Rowdies-Regular.ttf',None),700:('ofl/rowdies/Rowdies-Bold.ttf',None)}),
 one('Concert One','ofl/concertone/ConcertOne-Regular.ttf'),
 # --- system (diagnostic / fallback only; not bundlable) ---
 vf('SF Pro Rounded (system)',SYS+'SFNSRounded.ttf',100,1000, lic='Apple system'),
 st('Arial Rounded MT Bold (system)',{700:(SYS+'Supplemental/Arial Rounded Bold.ttf',None)}, lic='Apple system (Monotype)'),
]
_AXDEF={}
def axis_defaults(path):
    """all non-wght/opsz axes pinned to their fvar default (CoreText otherwise may not use the default)"""
    if path not in _AXDEF:
        from fontTools.ttLib import TTFont
        f=TTFont(path, lazy=True)
        _AXDEF[path]={a.axisTag:a.defaultValue for a in f['fvar'].axes if a.axisTag not in ('wght','opsz')} if 'fvar' in f else {}
    return _AXDEF[path]
def instances(c, step=100, only=None):
    """yield (weight, file, ps, axes-without-opsz, opsz-range)"""
    if c['kind']=='vf':
        ws = only if only else sorted(set([w for w in range(100,1001,step) if c['lo']<=w<=c['hi']]+[c['hi']]))
        for w in ws:
            if not (c['lo']<=w<=c['hi']): continue
            ax=dict(axis_defaults(c['file'])); ax.update(c['extra']); ax['wght']=float(w)
            yield w, c['file'], None, ax, c['opsz']
    else:
        for w,(f,ps) in c['faces'].items():
            if only and w not in only: continue
            yield w, f, ps, None, None
def heaviest(c):
    return c['hi'] if c['kind']=='vf' else max(c['faces'])
