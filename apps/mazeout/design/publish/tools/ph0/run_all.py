"""PH-0 (2026-09-28, phone session on the ORIGINAL v582): re-check every number in motion-catalog.md §11 and build/p/PH0/balloon.md.

Run:  nice -n 19 ~/.venvs/mf3d/bin/python design/publish/tools/ph0/run_all.py [name ...]      (no name = all; each takes seconds)
Clips: research/video/S4-*.mov (60 Hz phone recordings, iPhone 15, 393 x 852 pt; t = presentation time of the clip).
The helper scripts beside this file read clips through research/motion-tools/mf.py (mfx raw); they print one line per frame.

  tr.py CLIP S E [W] [x,y,w,h]      per-frame distance to the first/last frame, frame-to-frame change and mean luminance
  bandpos.py CLIP S E               band popup (purple or blue) extent at the screen edges + red button centroid
  panelw.py CLIP S E y0 y1          panel frame left/right extent in a row band (punch scale = width / rest width)
  slide.py CLIP "tS,tH,tL" S E      camera offset on the Shop|Home|Leaderboard strip (0 = Shop, 393 = Home, 786 = Leaderboard)
  knob.py CLIP S E                  toggle knob x (Paused panel Sound row)
  redw.py CLIP S E x0 y0 x1 y1      red button size (press scale)
  onsets.py CLIP S E "x,y;..."      first change around tap points (arrow tap = ripple frame on release)
  aon.py WAV                        audio segments above -45 dBFS (mfx audio CLIP OUT.wav first)
  balloony.py / stripx.py / track.py / badges.py   balloon rise on the page, the win-panel Balloon strip, badge motion, idle activity
  fitband2.py / fitdrop.py / fitslide.py           the curve fits quoted in the catalog (data tables inside)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

RUNS = {
    # R1: Quit Level? band drops from the top (entrance), cancel exit up, dim ramps
    'r1-entrance': ['bandpos.py', 'S4-R1a-L109-back-quit-x.mov', '2.25', '2.70'],
    'r1-entrance-2': ['bandpos.py', 'S4-R1b-L109-pause-quit-x.mov', '4.65', '5.00'],
    'r1-cancel-exit': ['bandpos.py', 'S4-R1a-L109-back-quit-x.mov', '4.94', '5.28'],
    'r1-dim': ['tr.py', 'S4-R1b-L109-pause-quit-x.mov', '7.15', '7.52', '66', '20,680,350,80'],
    'r1-fit': ['fitband2.py'],
    'band-exit-fits': ['fitdrop.py'],
    'continue-band-entrance': ['bandpos.py', 'S4-R5-L109-outoftime-x.mov', '2.33', '2.72'],
    'proceed-exit-down': ['bandpos.py', 'S4-PH0b-L112-quit-step2.mov', '2.15', '2.60'],
    'level-failed-punch': ['panelw.py', 'S4-R5-L109-continue-x.mov', '2.36', '2.62', '426', '434'],
    # Paused punch (v582 = v552) and the offer / More Lives punch
    'pause-punch': ['panelw.py', 'S4-R1b-L109-pause-quit-x.mov', '2.15', '2.40', '426', '434'],
    'lives-punch': ['panelw.py', 'S4-R4-lives-open.mov', '2.00', '2.25', '500', '508'],
    'rocket-punch': ['panelw.py', 'S4-R4-rocket-open.mov', '1.97', '2.22', '560', '568'],
    'sky-punch': ['panelw.py', 'S4-R4-sky-open.mov', '1.92', '2.17', '560', '568'],
    # R2 tabs
    'r2-home-to-shop': ['slide.py', 'S4-R2-tabs-chain.mov', '3.5,1.2,9.5', '1.9', '2.5'],
    'r2-lead-to-shop-2page': ['slide.py', 'S4-R2-tabs-chain.mov', '3.5,1.2,9.5', '10.5', '11.2'],
    'r2-coin-pill': ['slide.py', 'S4-R2-coinpill.mov', '3.0,1.8,1.8', '1.9', '2.45'],
    'r2-fit': ['fitslide.py'],
    # R3 (celebration skip) and the unskipped control
    'r3a-arrow-onsets': ['onsets.py', 'S4-R3-L109-win-taps.mov', '0.95', '8.0', '273.9,320.2;273.9,376.2;315.9,264.1;301.9,334.2;329.9,390.2', '6'],
    'r3a-timeline': ['tr.py', 'S4-R3-L109-win-taps.mov', '9.10', '10.60', '66'],
    'r3b-arrow-onsets': ['onsets.py', 'S4-R3-L112-win-taps-n6-g0.0.mov', '0.99', '4.0', '319.4,316.2;368.5,267.0;368.5,185.1', '6'],
    'r3b-timeline': ['tr.py', 'S4-R3-L112-win-taps-n6-g0.0.mov', '4.60', '5.20', '66'],
    'control-timeline': ['tr.py', 'S4-L111-win.mov', '5.55', '8.45', '66'],
    # R6 toggle + X press
    'r6-knob-off': ['knob.py', 'S4-R6-L109-pause-sound-toggle.mov', '3.9', '4.4'],
    'r6-knob-on': ['knob.py', 'S4-R6-L109-pause-sound-toggle.mov', '5.7', '6.2'],
    'r6-x-press': ['redw.py', 'S4-R6-L109-pause-sound-toggle.mov', '7.5', '8.2', '330', '225', '392', '290'],
    # R7 home idle
    'r7-activity': ['badges.py', 'S4-R7-home-idle-a.mov', '0.25'],
    'r7-rocket': ['track.py', 'S4-R7-home-idle-a.mov', '20', '280', '80', '370', 'red', '0.1'],
    'r7-balloon-badge': ['track.py', 'S4-R7-home-idle-a.mov', '315', '185', '380', '250', 'yellow', '0.1'],
    # R10 leaderboard tabs
    'r10-list': ['tr.py', 'S4-R10-leaderboard-tabs.mov', '1.0', '13', '66', '0,190,393,560'],
    # Balloon Rise page / win strip
    'balloon-open-cut': ['tr.py', 'S4-PH0b-balloon-open.mov', '1.5', '2.0'],
    'balloon-rise-on-open': ['balloony.py', 'S4-PH0b-balloon-open-after-win1.mov', '1.99', '4.2'],
    'balloon-win-strip': ['stripx.py', 'S4-L111-win.mov', '8.3', '9.8'],
}

if __name__ == '__main__':
    names = sys.argv[1:] or list(RUNS)
    for n in names:
        args = RUNS[n]
        print(f'==== {n}: {" ".join(args)}', flush=True)
        subprocess.run([PY, os.path.join(HERE, args[0]), *args[1:]], check=False)
