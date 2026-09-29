"""Build the shipped fonts from the matched OFL source (system python3 + fontTools).

  source : google/fonts ofl/nunito/Nunito[wght].ttf and Nunito-Italic[wght].ttf (v3.602, OFL-1.1, no Reserved Font
           Name; copyright 2014 The Nunito Project Authors) — sha256 of both checked below.
  output : design/fonts/PCDisplay-Black.ttf        = static instance at wght 1000 (the heaviest master; Nunito's own
                                                     'Black' named instance is wght 900, which measured too light)
           design/fonts/PCDisplay-BlackItalic.ttf  = the italic at wght 1000 (for slanted event-title lettering such
                                                     as the 'Streak Race' logo; not measured, see fonts.md)
           design/fonts/OFL.txt                    = the licence, unchanged.
Changes (a Modified Version under OFL §3-4; renaming is always allowed and avoids a clash with the real Nunito Black):
  - instanced at wght=1000 (fvar/gvar/avar/HVAR removed by the instancer; STAT removed here),
  - name table: family 'PC Display', style 'Black' / 'Black Italic', PostScript 'PCDisplay-Black' /
    'PCDisplay-BlackItalic'; copyright (ID 0) and licence (IDs 13/14) kept; a description (ID 10) records the source,
  - the 'fi' ligature is removed from 'liga' ('fl' kept): in Turkish text a ligated fi would lose the dot of the i,
    and CoreText only applies the Turkish language system when the text carries a language tag.
usage: make_font.py SRC_DIR OUT_DIR     (SRC_DIR = the downloaded google/fonts ofl/nunito folder)"""
import sys, os, hashlib, shutil
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
SRC=sys.argv[1]; OUT=sys.argv[2]; os.makedirs(OUT, exist_ok=True)
BUILDS=[ # source file, expected sha256, style, PostScript name, italic
 ('Nunito[wght].ttf','bb55a5ca5c2042335b3991af27c4d0705d0ef41cac6164ac737fd8f2a1e85207','Black','PCDisplay-Black',False),
 ('Nunito-Italic[wght].ttf','b520cc871868b0acfca1beda875df7f4a44ebce914f8a89f83977fc9c09529c8','Black Italic','PCDisplay-BlackItalic',True),
]
FAM='PC Display'
for fn,expect,STY,PS,italic in BUILDS:
    path=os.path.join(SRC,fn)
    h=hashlib.sha256(open(path,'rb').read()).hexdigest(); assert h==expect, f'unexpected source {fn} {h}'
    inst=instancer.instantiateVariableFont(TTFont(path), {'wght':1000}, updateFontNames=False)
    name=inst['name']
    for rec in list(name.names):
        if rec.nameID in (16,17,25) or rec.nameID>=256: name.removeNames(nameID=rec.nameID)
    for pid,eid,lid in ((3,1,0x409),(1,0,0)):
        name.setName(FAM,1,pid,eid,lid); name.setName(STY,2,pid,eid,lid)
        name.setName(f'3.602;NONE;{PS}',3,pid,eid,lid); name.setName(f'{FAM} {STY}',4,pid,eid,lid)
        name.setName(PS,6,pid,eid,lid)
        name.setName(f'Static instance (wght 1000) of {fn.split("[")[0]} 3.602 by The Nunito Project Authors '
                     '(github.com/googlefonts/nunito), SIL Open Font License 1.1 (no Reserved Font Name), '
                     'renamed; fi ligature removed for Turkish.',10,pid,eid,lid)
    if 'STAT' in inst: del inst['STAT']      # its axis-value names pointed at the removed name IDs >= 256
    inst['OS/2'].usWeightClass=900
    inst['OS/2'].fsSelection=(inst['OS/2'].fsSelection & ~0b1100001) | (1 if italic else 0)   # italic bit only
    inst['head'].macStyle=2 if italic else 0
    g=inst['GSUB'].table                      # drop the fi ligature (keep fl)
    for fr in g.FeatureList.FeatureRecord:
        if fr.FeatureTag!='liga': continue
        for li in fr.Feature.LookupListIndex:
            for st in g.LookupList.Lookup[li].SubTable:
                st=getattr(st,'ExtSubTable',st)
                if hasattr(st,'ligatures') and 'f' in st.ligatures:
                    st.ligatures['f']=[l for l in st.ligatures['f'] if l.Component!=['i']]
    inst.recalcTimestamp=False            # keep head.modified from the source: byte-reproducible builds
    out=os.path.join(OUT, PS+'.ttf'); inst.save(out)
    print(out, hashlib.sha256(open(out,'rb').read()).hexdigest(), os.path.getsize(out))
shutil.copyfile(os.path.join(SRC,'OFL.txt'), os.path.join(OUT,'OFL.txt'))
