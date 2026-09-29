#!/usr/bin/env python3
"""soc_freeze.py — writes / checks design/social/FROZEN, the freeze of the SHIPPED world (PUBLISH B2, PLAN-P §4.4 + G9;
design/publish/social-intl.md P0-3: "the world model has to be final at v1.0").

Every level, name and country a simulated player shows is a pure function of the files below: the T6 data (the country
table, bands, region map, names), the reference implementation that defines the model (socialsim), the Swift tables and the
shipped name bank generated from them, and the golden fixtures the Swift port matches bit for bit (Debug and -O). After
release the world may only evolve APPEND-ONLY (a new mechanism applies to join periods p >= the change's period and never
touches an existing player); changing any frozen file rewrites every board players have already seen.
SocialIntlTests.testTheShippedWorldIsFrozen recomputes the hashes; this tool refuses to re-freeze unless --refreeze is given
(an owner-level decision: note it in PLAN.md).

    python3 Packages/PathCore/Tests/tools/soc_freeze.py --check       # exit 1 when a frozen file changed
    python3 Packages/PathCore/Tests/tools/soc_freeze.py --write       # first freeze (refuses if FROZEN exists)
    python3 Packages/PathCore/Tests/tools/soc_freeze.py --refreeze    # a deliberate new freeze
"""
import hashlib, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(APP, 'design', 'social', 'FROZEN')

FILES = [
    # the T6 data (design/social/tools/v2/build_countries_v2.py, build_name_data_v2.py)
    'design/social/data_v2/buckets_v2.tsv',
    'design/social/data_v2/countries_v2.tsv',
    'design/social/data_v2/regions_v2.tsv',
    'design/social/data_v2/social_names_v2.json',
    # the reference that defines the model (v2 = shipped.py + population/names/data switches)
    'design/social/tools/socialsim/core.py',
    'design/social/tools/socialsim/data.py',
    'design/social/tools/socialsim/population.py',
    'design/social/tools/socialsim/names.py',
    'design/social/tools/socialsim/events.py',
    'design/social/tools/socialsim/shipped.py',
    'design/social/tools/socialsim/v2.py',
    # what ships, generated from the data (Tests/tools/soc_v2_tables.py, soc_ship_names.py)
    'Packages/PathCore/Sources/PathCore/Social/SocialIntlTables.swift',
    'App/Resources/Social/social_names.json',
    # the golden vectors the Swift world matches bit for bit (design/social/tools/v2/fixtures_v2.py)
    'Packages/PathCore/Tests/Fixtures/soc_v2_world.json',
    'Packages/PathCore/Tests/Fixtures/soc_v2_events.json',
    'Packages/PathCore/Tests/Fixtures/soc_v2_intl.json',
]


def sha(path):
    h = hashlib.sha256()
    with open(os.path.join(APP, path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def render(stamp):
    head = [
        '# design/social/FROZEN — the SHIPPED world model, frozen for v1.0 (PUBLISH B2; PLAN-P §4.4, gate G9; social-intl P0-3).',
        '# Model "shipped" = SocialWorldModel.shipped = design/social/tools/socialsim/v2.py (the calibrated world + M1-M11),',
        '# world epoch Monday 2026-09-07 07:00 UTC, world seed 0x41524F57204F5554. Every level, name and country a simulated',
        '# player shows is a pure function of the files below. After release the world evolves APPEND-ONLY (new mechanisms only',
        '# for join periods p >= the change\'s period); editing a frozen file rewrites every board players have already seen.',
        '# Checked by SocialIntlTests.testTheShippedWorldIsFrozen and Packages/PathCore/Tests/tools/soc_freeze.py --check.',
        '# frozen %s' % stamp,
        '# sha256<TAB>path (relative to apps/mazeout)',
    ]
    return '\n'.join(head + ['%s\t%s' % (sha(p), p) for p in FILES]) + '\n'


def parse(text):
    out = {}
    for l in text.splitlines():
        if l and not l.startswith('#'):
            h, p = l.split('\t')
            out[p] = h
    return out


def main():
    args = sys.argv[1:]
    if '--check' in args or not args:
        if not os.path.exists(OUT):
            print('NOT FROZEN: %s missing' % OUT)
            sys.exit(1)
        want = parse(open(OUT, encoding='utf-8').read())
        bad = [p for p in FILES if want.get(p) != sha(p)] + [p for p in want if p not in FILES]
        print('frozen: %d files match' % len(FILES) if not bad else 'CHANGED since the freeze: %s' % ', '.join(bad))
        sys.exit(1 if bad else 0)
    if '--write' in args and os.path.exists(OUT):
        print('FROZEN exists: use --refreeze for a deliberate new freeze (note it in PLAN.md)')
        sys.exit(1)
    stamp = time.strftime('%Y-%m-%d %H:%M %z')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(render(stamp))
    print('wrote %s (%d files, %s)' % (os.path.relpath(OUT, APP), len(FILES), stamp))


if __name__ == '__main__':
    main()
