"""level_reorder/feat.py — per-level features of design/levels.json (read-only; no solver runs: units from tapes, the rest from the stored metrics)."""
import json
import os
import re

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
LEVELS = os.path.join(APP, 'design', 'levels.json')
KIND = dict(tape='tape', door='door', pipe='pipe', box='box', curtain='box', elevator='elevator', corner='corner')


def research_number(l):
    """The number this board had in the ORIGINAL game's order, when it is known (VERIFIED from the capture path / _from)."""
    cap = l.get('capture') or ''
    m = re.search(r'[/-]L0*(\d+)-', cap)
    if l['source'] == 'recorded' and m:
        return ('v552', int(m.group(1)))
    if l['source'] == 'video':
        m2 = re.search(r'/(V[12])/L0*(\d+)-start', cap)
        if l.get('_from', '').startswith('V2-L'):
            return ('older-build', int(re.match(r'V2-L0*(\d+)', l['_from']).group(1)))
        if m2:
            return ('older-build', int(m2.group(2)))
    return None


def features(l):
    obs = l['obstacles']
    tapes = [o for o in obs if o['kind'] == 'tape']
    units = len(l['arrows']) - sum(len(t['arrows']) - 1 for t in tapes)
    doors = sum(1 for o in obs if o['kind'] == 'door')
    kinds = frozenset(KIND[o['kind']] for o in obs if o['kind'] in KIND)
    m = l['metrics']
    return dict(n=l['level'], tag=l['tag'], timer=l['timer_s'], units=units, waves=m['rounds'], free=m['free_at_start'],
                arrows=m['arrows'], cells=m['cells'], cols=l['cols'], rows=l['rows'], doors=doors, kinds=kinds,
                bot_left=m['bot_time_left'], pressure=round(1 - m['bot_time_left'] / l['timer_s'], 4),
                source=l['source'], origin=research_number(l), stand_in=l.get('_from', '').startswith('designed stand-in'),
                twin_of=(int(re.search(r'repeat of L0*(\d+)', l['_from']).group(1))
                         if l.get('_from', '').startswith('designed stand-in') else None),
                unlock=l.get('unlock'))


def load():
    doc = json.load(open(LEVELS))
    return doc, [features(l) for l in doc['levels']]


if __name__ == '__main__':
    doc, F = load()
    for f in F:
        print(f['n'], f['tag'], f['timer'], f['units'], f['waves'], f['free'], '%dx%d' % (f['cols'], f['rows']),
              sorted(f['kinds']), f['source'], f['origin'], f['twin_of'], f['pressure'])
