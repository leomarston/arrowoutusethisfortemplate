#!/usr/bin/env python3
"""soc_model.py — the parameter-set switch of the social-simulation REFERENCE (design/social/tools/socialsim).

The Swift port (PathCore/Social) has two pinned parameter sets:
  * reference — the social designer's prototype exactly (design/social/fixtures/*.json pin it);
  * v552      — the SHIPPED world: the reference code with the shipped parameters and the shipped mechanisms switched on,
                as written in design/social/tools/socialsim/shipped.py (SOC1: the session-1 boards; SOC1b: phone session 2,
                research/social-dynamics.md). See SocialModel.swift / RaceBots.swift / Names.swift for the Swift side.
  * v2      — the world that SHIPS since PUBLISH B2 (Swift `SocialWorldModel.shipped`): v552 + the international
                mechanisms M1-M11 of design/social/tools/socialsim/v2.py (T6); its fixtures come from
                design/social/tools/v2/fixtures_v2.py (soc_fixtures.py's logic run on the v2 model + the intl sections).
`use('v552')` / `use('v2')` patch the imported reference IN MEMORY (never on disk), so every fixture comes from the reference
code itself. Import this module before anything else from socialsim.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
REF = os.path.join(APP, 'design', 'social', 'tools')
sys.path.insert(0, REF)

from socialsim import core as K, data as D, population as Pp, names as Nm, events as E, shipped as SH   # noqa: E402

MODEL = 'reference'


def use(name):
    """Select the parameter set (call once, before building any World)."""
    global MODEL
    MODEL = name
    if name == 'reference':
        return
    assert name in ('v552', 'v2'), name
    if name == 'v2':
        from socialsim import v2 as V2      # noqa: E402 (applies shipped.py first)
        V2.apply()
    else:
        SH.apply()


def weekly_cls():
    return SH.Weekly if MODEL in ('v552', 'v2') else E.WeeklyContest


def streak_cls():
    return SH.Streak if MODEL in ('v552', 'v2') else E.StreakRace
