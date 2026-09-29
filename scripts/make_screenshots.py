#!/usr/bin/env python3
"""App Store screenshot uretici — cok dilli, CJK-uyumlu.

Girdi:  apps/<slug>/shots/final/*.png        (simulatorden alinmis ham ekranlar)
        apps/<slug>/design/captions/<loc>.json  {"captions":[{"headline","subline"},...5]}
Cikti:  apps/<slug>/fastlane/screenshots/<loc>/NN_iphone69.png  (1290x2796)

SF Pro'da CJK glifi YOKTUR; her dil icin dogru fontu secmek sart, yoksa
tofu (kare) basar. Basliklar kenar payina sigana kadar otomatik kuculur.

Kullanim: python3 scripts/make_screenshots.py --slug reco [--locales de-DE ja ...]
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
# App Store asset sizes. The iPhone 6.9" set was the only one this factory needed until
# `soundanalyzer` became a universal app — an app that supports iPad MUST also ship iPad
# screenshots, or the listing cannot be submitted.
DEVICES = {
    "iphone69": {"size": (1290, 2796), "suffix": "iphone69"},
    "ipad13":   {"size": (2064, 2752), "suffix": "ipad13"},
}

W, H = DEVICES["iphone69"]["size"]
BOTTOM, MARGIN = H - 84, 70


def assert_rendered(path, shot):
    """Refuse to build a frame from a raw shot that never rendered.

    A cold `simctl launch` can be screenshotted while the launch screen is still up, which
    yields a flat white phone. It looks fine in a directory listing, it passes a file-size
    check, and it sails through a count-based verification — camdetect shipped exactly that
    as screenshot 1 to all 50 storefronts, and Apple approved it, because nobody LOOKED.

    A real app screen is not one flat colour. Anything more than 88% a single tone is the
    launch screen, a crashed view, or an empty state that should not be advertised.
    """
    small = shot.convert("L").resize((90, 180))
    px = list(small.getdata())
    hist = {}
    for v in px:
        hist[v // 8] = hist.get(v // 8, 0) + 1
    flat = max(hist.values()) / len(px)

    # Flatness alone is not enough. A launch screen is flat AND featureless; a legitimately
    # flat design — mater's yellow ruler face — is flat but carries hundreds of hard tick
    # edges. Rejecting on colour alone threw that out (measured 89% flat, perfectly good
    # screenshot), so the test is flat AND no detail.
    edges = 0
    for y in range(180):
        row = px[y * 90:(y + 1) * 90]
        edges += sum(1 for i in range(1, 90) if abs(row[i] - row[i - 1]) > 24)
    detail = edges / (90 * 180)

    if flat > 0.88 and detail < 0.012:
        raise SystemExit(
            f"!! {path.name}: {flat*100:.0f}% one flat tone and almost no detail "
            f"({detail*100:.1f}%) — it did not render. Re-capture it; do not ship this.")


def use_device(name: str):
    """Point the module-level canvas metrics at one of DEVICES."""
    global W, H, BOTTOM
    W, H = DEVICES[name]["size"]
    BOTTOM = H - int(84 * H / 2796)

LATIN_BOLD = "/Library/Fonts/SF-Pro-Display-Heavy.otf"
LATIN_SUB = "/Library/Fonts/SF-Pro-Display-Bold.otf"
# (path, ttc_index) — dogrulanmis kalin yuzler
# One entry per script that SF Pro can't draw. SF Pro Display covers Latin *plus Greek
# and Cyrillic*, so el/ru/uk need nothing here — but every script below rendered as solid
# tofu boxes until it was added (verified by rendering a sheet and looking at it; an
# ink-pixel count is useless because tofu boxes have ink too).
# Face indices were chosen by rendering each locale's sample text through every face in
# the .ttc and keeping the boldest one with zero missing glyphs.
FONTS = {
    "zh": ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2),   # W6
    "ja": ("/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc", 0),  # W7
    "ko": ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6),   # Bold
    "ar": ("/System/Library/Fonts/GeezaPro.ttc", 1),           # Bold
    "he": ("/System/Library/Fonts/SFHebrew.ttf", 0),
    "th": ("/System/Library/Fonts/ThonburiUI.ttc", 0),
    "hi": ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 1),   # Bold
    "mr": ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 1),   # Bold
    "bn": ("/System/Library/Fonts/KohinoorBangla.ttc", 1),                      # Semibold
    "gu": ("/System/Library/Fonts/KohinoorGujarati.ttc", 0),                    # Bold
    "kn": ("/System/Library/Fonts/NotoSansKannada.ttc", 5),                     # SemiBold
    "ml": ("/System/Library/Fonts/ZitherMalayalam.otf", 0),
    "or": ("/System/Library/Fonts/NotoSansOriya.ttc", 1),                       # Bold
    "pa": ("/System/Library/Fonts/Supplemental/Gurmukhi MN.ttc", 1),            # Bold
    "ta": ("/System/Library/Fonts/ZitherTamil.otf", 0),
    "te": ("/System/Library/Fonts/KohinoorTelugu.ttc", 1),                      # Semibold
    # Urdu is Arabic script but Naskh (GeezaPro) reads wrong for it — Nastaliq is the
    # form Urdu readers expect.
    "ur": ("/System/Library/Fonts/NotoNastaliq.ttc", 2),                        # Bold
}


def shape(text: str, locale: str) -> str:
    """RTL locales: PIL has no libraqm, so do the shaping ourselves.

    Arabic AND Urdu are cursive — the letters must be joined into their contextual forms
    first, then reordered right-to-left. Hebrew letters don't join, so it only needs the
    bidi reorder. Getting this wrong doesn't produce tofu, it produces text that renders
    'fine' but reads backwards or disconnected, which is why it has to be looked at.
    """
    lang = locale.split("-")[0].lower()
    if lang not in ("ar", "ur", "he"):
        return text
    try:
        from bidi.algorithm import get_display
        if lang in ("ar", "ur"):
            import arabic_reshaper
            return get_display(arabic_reshaper.reshape(text))
        return get_display(text)
    except Exception:
        # Never silently ship unshaped RTL — it looks subtly wrong to a native reader.
        raise RuntimeError(
            f"{locale}: RTL shaping unavailable — pip install arabic-reshaper python-bidi"
        )
# ham ekran -> (gradyan ustu, gradyan alti, ust kirpma)
# Her app kendi kare setini FRAMES_BY_SLUG'da tanimlar; yoksa varsayilan (reco) kullanilir.
FRAMES_DEFAULT = [
    ("01_home.png",        (59, 130, 246), (30, 58, 138), 0),    # route + live meter (light)
    ("03_onboarding.png",  (59, 130, 246), (30, 58, 138), 0),    # hero
    ("04_recordings.png",  (59, 130, 246), (30, 58, 138), 120),  # saved sessions
    ("d_home.png",         (37,  99, 235), (17, 24,  60), 0),    # gain/EQ/reverb (dark)
    ("05_settings.png",    (59, 130, 246), (30, 58, 138), 120),  # themes / customization
]

# ProCam — cine-instrument, matte black → blue accent gradients matching the app.
FRAMES_BY_SLUG = {
    # 2 3 4 Player Games Offline — the app's own ground is warm paper cream, so the frames go
    # to saturated colour and alternate the two hues the product is actually built out of: the
    # ember of HAUL (its icon game) and the lagoon of PARRY. Deliberately NOT the category's sky
    # blue: five of the fourteen competitors' grounds are a red/blue split and four are
    # four-colour quadrants, so a warm frame is the only one in the search results that is not a
    # rainbow. Keyword order drives which frame goes where (captions = the first five keywords).
    "partypack": [
        ("1_menu.png",    (224,  89,  47), (122,  40,  18), 0),   # 1 2 3 4 player games (the ten tiles)
        ("2_haul.png",    ( 46, 158, 168), ( 16,  74,  80), 0),   # 2 two player games offline (4 ropes)
        ("3_bump.png",    (224,  89,  47), (122,  40,  18), 0),   # 3 4 player games one phone (4 corner pads)
        ("4_pairs.png",   ( 46, 158, 168), ( 16,  74,  80), 0),   # 4 party games no wifi (simultaneous board)
        ("5_firefly.png", (224,  89,  47), (122,  40,  18), 0),   # 5 mini games (the 3-seat case)
    ],
    # Couch (Universal TV Remote) — the app is a black remote body on warm ground with one LED
    # green accent, so the frames alternate graphite and a deep forest that lets the green read.
    # Keyword order drives which frame goes where (captions = the first five keywords).
    "tvremote": [
        ("01-remote.png",        (38, 36, 33), (12, 12, 11), 0),   # 1 universal tv remote (dark, strip green)
        ("02-remote-drawer.png", (16, 44, 24), (5, 14, 8),   0),   # 2 smart tv remote (numbers/inputs open)
        ("03-finder-scan.png",   (38, 36, 33), (12, 12, 11), 0),   # 3 wifi tv remote (finder mid-scan)
        ("04-keyboard.png",      (16, 44, 24), (5, 14, 8),   0),   # 4 tv keyboard
        ("05-remote-volume.png", (38, 36, 33), (12, 12, 11), 0),   # 5 tv volume (light mode, ripple)
    ],
    # Storage Cleaner — the app itself is warm archival paper, so the frames go dark and
    # alternate espresso-copper with graphite to let the light screens and the real photographs
    # inside them pop. Keyword order drives which frame goes where.
    # The cleaner category's own backdrop, sampled off the 710,000-rating leader's frames:
    # #47A2FB down to #0A72F0, the SAME pair on all five. Alternating hues is what makes a
    # set look like five unrelated apps; every leader in this category runs one blue.
    "storagecleaner": [
        ("01_storage_cleaner.png",       (71, 162, 251), (10, 114, 240), 0),  # 1 storage cleaner
        ("02_clean_up_storage.png",      (71, 162, 251), (10, 114, 240), 0),  # 2 clean up storage for iphone
        ("03_cleanup_phone_storage.png", (71, 162, 251), (10, 114, 240), 0),  # 3 cleanup phone storage cleaner
        ("04_photo_cleaner.png",         (71, 162, 251), (10, 114, 240), 0),  # 4 photo cleaner
        ("05_measured_not_guessed.png",  (71, 162, 251), (10, 114, 240), 0),  # 5 measured, not guessed
    ],
    # Spin the Wheel — the app itself is a bright multicoloured wheel on a light ground, so
    # the frames go dark and alternate crimson-plum with deep indigo to let it pop. Keyword
    # order drives which frame goes where.
    "spinwheel": [
        ("01_spin_the_wheel.png",     (122, 12, 56), (34, 4, 16), 0),   # 1 spin the wheel
        ("02_spinner_wheel_app.png",  (36, 32, 84),  (10, 9, 26), 0),   # 2 spinner wheel app
        ("03_finger_chooser.png",     (122, 12, 56), (34, 4, 16), 0),   # 3 finger chooser
        ("04_tiny_decision.png",      (36, 32, 84),  (10, 9, 26), 0),   # 4 tiny decision
        ("05_check_it_yourself.png",  (122, 12, 56), (34, 4, 16), 0),   # 5 check it yourself
    ],
    # LED Banner — the app is amber lamps on a near-black board, so the frames alternate
    # graphite and a deep amber-brown. Keyword order drives which frame goes where.
    "ledbanner": [
        ("01_led_banner.png",     (26, 30, 36), (9, 11, 14), 0),    # 1 led banner
        ("02_scrolling_text.png", (92, 56, 4),  (32, 19, 2), 0),    # 2 scrolling text
        ("03_led_scroller.png",   (26, 30, 36), (9, 11, 14), 0),    # 3 led scroller
        ("04_text_led.png",       (92, 56, 4),  (32, 19, 2), 0),    # 4 text led
        ("05_hold_it_up.png",     (26, 30, 36), (9, 11, 14), 0),    # 5 hold it up
    ],
    # Boxing Timer — arena dark and corner red, the app's own gym-signage palette. The
    # amber frame sits under the final-ten shot so the gradient matches what's on screen.
    "boxingtimer": [
        ("01_boxing_timer.png",       (140, 24, 24), (44, 8, 8), 0),    # 1 boxing timer (red ring)
        ("02_boxing_round_timer.png", (24, 24, 30), (8, 8, 11), 0),     # 2 boxing round timer (corner)
        ("03_boxing_timer_app.png",   (20, 74, 150), (7, 26, 54), 0),   # 3 boxing timer app (blue rest)
        ("04_interval_timer.png",     (24, 24, 30), (8, 8, 11), 0),     # 4 interval timer (library)
        ("05_timekeepers_kit.png",    (128, 78, 6), (44, 26, 2), 0),    # 5 the timekeeper's kit (amber)
    ],
    # PodFind — the app is a temperature, so the five frames alternate cold indigo and
    # warm ember. Order follows the keyword list.
    "podfind": [
        ("01_earbud_finder.png",            (36, 46, 96), (8, 12, 26), 0),   # 1 earbud finder
        ("02_find_lost_earbuds.png",        (124, 58, 16), (24, 12, 10), 0), # 2 find lost earbuds
        ("03_bluetooth_device_locator.png", (36, 46, 96), (8, 12, 26), 0),   # 3 bluetooth device locator
        ("04_headphones_tracker.png",       (124, 58, 16), (24, 12, 10), 0), # 4 headphones tracker
        ("05_wireless_earbuds_finder.png",  (36, 46, 96), (8, 12, 26), 0),   # 5 wireless earbuds finder
    ],
    # Water Eject — the app is pool-tile cyan on a light ground, so the frames sit on deep
    # water: near-black ocean alternating with a mid teal. Keyword order drives which frame
    # goes where.
    "watereject": [
        ("01_water_eject.png",           (6, 42, 66), (2, 16, 28), 0),   # 1 water eject
        ("02_eject_water_from_phone.png", (10, 88, 120), (3, 36, 54), 0), # 2 eject water from phone
        ("03_clear_speaker_water.png",   (6, 42, 66), (2, 16, 28), 0),   # 3 clear speaker water
        ("04_fix_muffled_speaker.png",   (10, 88, 120), (3, 36, 54), 0), # 4 fix muffled speaker
        ("05_speaker_cleaner_sound.png", (6, 42, 66), (2, 16, 28), 0),   # 5 speaker cleaner sound
    ],
    # NM — hi-vis chartreuse on ink, the app's own palette. Panels alternate deep ink and
    # dark olive (the accent held back so white headlines stay readable). Keyword order
    # drives which frame goes where.
    "noisemeter": [
        ("01_noise_level_meter.png",   (22, 24, 29), (10, 11, 14), 0),  # 1 noise level meter
        ("02_db_meter.png",            (58, 66, 10), (22, 26,  4), 0),  # 2 db meter
        ("03_decibel_meter.png",       (22, 24, 29), (10, 11, 14), 0),  # 3 decibel meter
        ("04_sound_meter_db.png",      (58, 66, 10), (22, 26,  4), 0),  # 4 sound meter db
        ("05_noise_decibel_meter.png", (22, 24, 29), (10, 11, 14), 0),  # 5 noise decibel meter
    ],
    # Stakeout — aubergine ink, bone accent. Alternating deep/plum so the five read as a set.
    "bugdetector": [
        ("01_tape.png",     (44, 27, 61), (16,  9, 24), 0),   # 1 bug detector
        ("02_events.png",   (26, 16, 36), (10,  6, 16), 0),   # 2 hidden bug detector
        ("03_archive.png",  (44, 27, 61), (16,  9, 24), 0),   # 3 anti spy tone log
        ("04_selftest.png", (26, 16, 36), (10,  6, 16), 0),   # 4 spy detector
        ("05_limits.png",   (44, 27, 61), (16,  9, 24), 0),   # 5 near-ultrasonic scan
    ],
    # HD — the app itself is light chart paper, so the frame sits on plotter magenta.
    "hiddendevice": [
        ("01_hidden_device_detector.png", (176, 23, 107), (84, 10, 51), 0),  # 1
        ("02_detect_hidden_devices.png",  (124, 15,  75), (52,  6, 32), 0),  # 2
        ("03_magnetic_field.png",         (176, 23, 107), (84, 10, 51), 0),  # 3
        ("04_hidden_detector.png",        (124, 15,  75), (52,  6, 32), 0),  # 4
        ("05_spy_detector.png",           (176, 23, 107), (84, 10, 51), 0),  # 5
    ],
    "procam": [
        ("01_home.png",      (30, 58, 110), (6, 10, 20), 0),  # 1 professional camera
        ("03_edit.png",      (26, 52, 100), (6, 10, 20), 0),  # 2 film look presets
        ("02_monitor.png",   (30, 58, 110), (6, 10, 20), 0),  # 3 focus peaking camera
        ("05_presets.png",   (26, 52, 100), (6, 10, 20), 0),  # 4 raw photo camera
        ("04_paywall.png",   (30, 58, 110), (6, 10, 20), 0),  # 5 manual camera app
    ],
    # HearMe — clinical chart: deep charcoal panels alternating with the rose accent, so
    # the five frames read as one set. Keyword order drives which frame goes where.
    "hearingtest": [
        ("01.png", (32, 28, 38), (10, 9, 14), 0),     # 1 hearing test
        ("02.png", (214, 52, 84), (96, 18, 38), 0),   # 2 audiogram chart
        ("03.png", (32, 28, 38), (10, 9, 14), 0),     # 3 hearing age test
        ("04.png", (214, 52, 84), (96, 18, 38), 0),   # 4 pure tone audiometry
        ("05.png", (32, 28, 38), (10, 9, 14), 0),     # 5 hearing check at home
    ],
    # TD — scanner console: near-black chassis alternating with signal lime, deliberately
    # nothing like Sweep's violet. Keyword order drives which frame goes where.
    "trackdetect": [
        ("01.png", (18, 24, 12), (6, 8, 4), 0),      # 1 tracking device detector
        ("02.png", (110, 168, 18), (34, 54, 6), 0),  # 2 find hidden trackers
        ("03.png", (18, 24, 12), (6, 8, 4), 0),      # 3 anti stalking scanner
        ("04.png", (110, 168, 18), (34, 54, 6), 0),  # 4 bluetooth tag scan
        ("05.png", (18, 24, 12), (6, 8, 4), 0),      # 5 tag scanner
    ],
    # hearUP — calm teal control room; panels alternate light slate and teal so the five
    # frames read as one set. Keyword order drives which frame goes where.
    "hearup": [
        ("01.png", (18, 46, 44), (7, 20, 19), 0),     # 1 hearing amplifier
        ("02.png", (0, 168, 146), (0, 74, 66), 0),    # 2 sound amplifier app
        ("03.png", (18, 46, 44), (7, 20, 19), 0),     # 3 amplify voices around you
        ("04.png", (0, 168, 146), (0, 74, 66), 0),    # 4 listen to quiet sounds
        ("05.png", (18, 46, 44), (7, 20, 19), 0),     # 5 super hearing
    ],
    # LD — cold steel counter-surveillance console; panels alternate deep navy and
    # electric cyan. Deliberately NOT Sweep's violet. Keyword order drives the frames.
    "listendetect": [
        ("01.png", (10, 30, 42), (4, 12, 18), 0),    # 1 listening device detector
        ("02.png", (0, 150, 190), (0, 58, 78), 0),   # 2 bug detector
        ("03.png", (10, 30, 42), (4, 12, 18), 0),    # 3 device detector
        ("04.png", (0, 150, 190), (0, 58, 78), 0),   # 4 hidden microphone finder
        ("05.png", (10, 30, 42), (4, 12, 18), 0),    # 5 room sweep app
    ],
    # Sweep — violet instrument panel; keyword order drives which frame goes where.
    "rfdetector": [
        ("01_rf.png",    (36, 30, 62), (12, 10, 22), 0),   # 1 rf signal detector
        ("06_rf_free.png",(124, 77, 255), (58, 30, 140), 0),# 2 bluetooth signal finder
        ("02_field.png", (36, 30, 62), (12, 10, 22), 0),   # 3 magnetic field meter
        ("03_net.png",   (124, 77, 255), (58, 30, 140), 0),# 4 network device scanner
        ("01_rf.png",    (36, 30, 62), (12, 10, 22), 0),   # 5 ble scanner
    ],
    # LightUP — black instrument chassis alternating with the amber readout colour, the
    # same two tones the app itself uses. Keyword order drives which frame goes where.
    "strobelight": [
        ("01_strobe.png",     (26, 22, 6), (8, 7, 3), 0),      # 1 strobe light
        ("02_flashlight.png", (255, 190, 10), (140, 96, 0), 0),# 2 flashlight
        ("03_torch.png",      (26, 22, 6), (8, 7, 3), 0),      # 3 torch
        ("04_police.png",     (255, 190, 10), (140, 96, 0), 0),# 4 flashing police lights
        ("05_disco.png",      (26, 22, 6), (8, 7, 3), 150),    # 5 disco lights (trim the
                                                               #   clipped preset cards)
    ],
    # WN — night-blue chassis alternating with the periwinkle accent, the same two tones
    # the app uses. Keyword order drives which frame goes where.
    "whitenoise": [
        ("01_white_noise.png",   (22, 28, 46), (6, 8, 14), 0),      # 1 white noise
        ("02_brown_noise.png",   (155, 180, 255), (58, 74, 140), 0),# 2 brown noise
        ("03_sleep_sounds.png",  (22, 28, 46), (6, 8, 14), 0),      # 3 sleep sounds
        ("04_sleep_timer.png",   (155, 180, 255), (58, 74, 140), 0),# 4 sleep timer
        ("05_sound_machine.png", (22, 28, 46), (6, 8, 14), 0),      # 5 sound machine
    ],
    # StopDog — graphite + brass, matching the icon; keyword order drives the frames.
    "stopdog": [
        ("01_cues.png",    (44, 48, 56), (16, 18, 22), 0),   # 1 dog whistle
        ("02_playing.png", (212, 160, 23), (120, 88, 12), 0),# 2 dog whistle to stop barking
        ("03_clicker.png", (44, 48, 56), (16, 18, 22), 0),   # 3 dog training clicker
        ("02_playing.png", (212, 160, 23), (120, 88, 12), 0),# 4 anti bark whistle
        ("04_silent.png",  (44, 48, 56), (16, 18, 22), 0),   # 5 silent dog whistle
    ],
    # TwoCam — bright category blue; each frame carries its keyword in order.
    "twocam": [
        ("01_pip.png",     (47, 155, 255), (10, 40, 92), 0),   # 1 dual camera
        ("05_swap.png",    (30, 120, 220), (8, 30, 78), 0),    # 2 front and back camera
        ("06_video.png",   (47, 155, 255), (10, 40, 92), 0),   # 3 dual camera recorder
        ("02_circle.png",  (30, 120, 220), (8, 30, 78), 0),    # 4 picture in picture cam
        ("03_split.png",   (47, 155, 255), (10, 40, 92), 0),   # 5 split screen camera
    ],
    # Kitz — playful deep-indigo → black so the colorful themed game shots pop.
    "kitz": [
        ("01_root_mouse.png", (36, 30, 66), (8, 8, 18), 0),   # 1 game for cats
        ("04_firefly.png",    (26, 40, 74), (8, 8, 18), 0),   # 2 cat games for cats
        ("07_laser.png",      (30, 26, 62), (8, 8, 18), 0),   # 3 laser pointer for cats
        ("size_large.png",    (36, 30, 66), (8, 8, 18), 0),   # 4 mouse chase game
        ("03_game_fish.png",  (26, 40, 74), (8, 8, 18), 0),   # 5 fish game for kittens
    ],
    # Spectrum — lab instrument: near-black panels alternating with a signal-green
    # gradient, so the five frames read as one set. Keyword order drives the frames.
    "soundanalyzer": [
        ("spectrum.png",  (16, 52, 38), (5, 8, 11), 0),    # 1 sound analyzer
        ("waterfall.png", (26, 140, 84), (7, 44, 29), 0),  # 2 audio spectrum analyzer
        ("measuring.png", (16, 52, 38), (5, 8, 11), 0),    # 3 decibel meter
        ("history.png",   (26, 140, 84), (7, 44, 29), 0),  # 4 noise level meter
        ("bands.png",     (16, 52, 38), (5, 8, 11), 0),    # 5 music note detector
    ],
    # Spot — the app's own screens are near-black by design (a detector viewfinder), so a
    # dark backdrop swallowed them: at store-thumbnail size the old set read as five empty
    # rectangles. Bright alarm red instead, alternating two depths, with the white device
    # body from DEVICE_FRAME_SLUGS separating the black screen from the red. Keyword order
    # drives which screen goes with which frame.
    "camdetect": [
        ("rack.png",      (232, 52, 74), (146, 20, 44), 0),  # 1 hidden camera detector
        ("network.png",   (170, 26, 52), (86, 10, 28), 0),   # 2 spy camera detector
        ("checklist.png", (232, 52, 74), (146, 20, 44), 0),  # 3 hotel room scan
        ("glint.png",     (170, 26, 52), (86, 10, 28), 0),   # 4 find hidden lens
        ("infrared.png",  (232, 52, 74), (146, 20, 44), 0),  # 5 infrared camera finder
    ],
    # Mater — a tape measure: brand yellow alternating with the darker gold of a level
    # body, black headline ink. Light backdrops because the app's own screens are dark,
    # and a dark-on-dark set reads as five black rectangles at thumbnail size.
    "mater": [
        ("01_ruler.png",     (255, 226, 60), (242, 190, 0),  0),  # 1 ruler measuring tape
        ("02_tape.png",      (255, 207, 47), (226, 163, 0),  0),  # 2 ar tape measure
        ("03_height.png",    (255, 226, 60), (242, 190, 0),  0),  # 3 measure height
        ("04_level.png",     (255, 207, 47), (226, 163, 0),  0),  # 4 bubble level
        ("05_floorplan.png", (255, 226, 60), (242, 190, 0),  0),  # 5 floor plan maker
    ],
    # Conduit Bending Calculator — the electrician-tool category's own identity is iOS
    # system blue; the leader's store canvas measures exactly #007AFF -> #006ADC and every
    # competitor sits in the same blue. Alternating two depths so the five read as one set.
    "conduitbend": [
        ("01_offset.png",  (0, 122, 255), (0, 106, 220), 0),   # 1 conduit bending calculator
        ("02_angles.png",  (0, 106, 220), (0, 86, 180), 0),    # 2 emt offset multiplier
        ("03_saddle.png",  (0, 122, 255), (0, 106, 220), 0),   # 3 three point saddle
        ("04_benders.png", (0, 106, 220), (0, 86, 180), 0),    # 4 pipe bender tool
        ("05_stub.png",    (0, 122, 255), (0, 106, 220), 0),   # 5 stub up deduct
    ],
    # VinCam — warm analog, sunset-orange → deep amber gradients matching the app.
    "vincam": [
        ("01_home.png",      (196, 78, 22), (60, 22, 8), 0),  # 1 vintage camera
        ("03_import.png",    (210, 96, 30), (60, 22, 8), 0),  # 2 35mm film filter
        ("02_develop.png",   (196, 78, 22), (60, 22, 8), 0),  # 3 retro film camera
        ("05_rolls.png",     (210, 96, 30), (60, 22, 8), 0),  # 4 disposable camera app
        ("04_paywall.png",   (196, 78, 22), (60, 22, 8), 0),  # 5 old camera effects
    ],
}


# Apps whose store frames draw the shot inside a phone body rather than as a bare rounded
# rectangle. Every leading app in the cleaner category does this, and a naked screenshot beside
# them reads as a web page rather than an app.
# A white phone body. Worth it for any app whose own screens are dark: it gives the
# black screen a hard edge against the backdrop instead of bleeding into it.
# Headline ink, per slug. Default is white, which suits a dark or saturated backdrop.
# An app whose brand colour is LIGHT (mater's tape yellow) needs black or the caption
# vanishes. Opt-in only — every slug not listed keeps the white it already ships with.
HEADLINE_COLOR_BY_SLUG = {"mater": "101010"}


DEVICE_FRAME_SLUGS = {"storagecleaner", "camdetect", "mater"}


def frames_for(slug: str):
    return FRAMES_BY_SLUG.get(slug, FRAMES_DEFAULT)


def font_for(locale: str, size: int, bold: bool = True):
    lang = locale.split("-")[0].lower()
    if locale.lower().startswith("zh"):
        lang = "zh"
    if lang in FONTS:
        path, idx = FONTS[lang]
        return ImageFont.truetype(path, size, index=idx)
    return ImageFont.truetype(LATIN_BOLD if bold else LATIN_SUB, size)


def fit(draw, text, locale, start, floor, bold=True):
    size = start
    while size > floor:
        f = font_for(locale, size, bold)
        if draw.textlength(text, font=f) <= W - 2 * MARGIN:
            return f
        size -= 4
    return font_for(locale, floor, bold)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_TEXTPNG = ROOT / "scripts" / ".bin" / "textpng"
_TEXTPNG_SRC = ROOT / "scripts" / "textpng.swift"


def _ensure_textpng() -> Path:
    """Compile the CoreText helper on first use / after an edit."""
    if not _TEXTPNG.exists() or _TEXTPNG_SRC.stat().st_mtime > _TEXTPNG.stat().st_mtime:
        _TEXTPNG.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(_TEXTPNG_SRC), "-o", str(_TEXTPNG)], check=True)
    return _TEXTPNG


def render_headline(text: str, locale: str, max_width: int,
                    size: int = 132, min_size: int = 58,
                    color: str = "FFFFFF") -> Image.Image:
    """Render a caption through CoreText and return it as an RGBA image.

    PIL cannot lay out complex scripts: its wheels have no Raqm/HarfBuzz, so Indic
    vowel reordering, conjuncts, Thai mark stacking and Arabic/Nastaliq joining all
    come out wrong — while still producing ink, so a pixel check calls it a pass.
    CoreText is the engine iOS uses; it shapes every one of the 50 App Store locales
    correctly and picks the right system font per script, which also means there is
    no per-language font table to keep in sync.
    """
    exe = _ensure_textpng()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out_path = tmp.name
    try:
        subprocess.run([
            str(exe), "--text", text, "--out", out_path,
            "--locale", locale, "--size", str(size), "--minsize", str(min_size),
            "--maxwidth", str(max_width), "--weight", "heavy", "--color", color,
        ], check=True, capture_output=True)
        return Image.open(out_path).convert("RGBA").copy()
    finally:
        os.unlink(out_path)


def build(slug: str, locale: str, captions: list, device: str = "iphone69",
          raw_dir: str | None = None) -> int:
    app = ROOT / "apps" / slug
    # --raw-dir may carry a {loc} placeholder so an iPad set can live beside the iPhone one.
    raw = (app / "shots" / raw_dir.format(loc=locale)) if raw_dir else app / "shots" / f"raw-{locale}"
    if not raw.exists():
        raw = app / "shots" / "final"       # geri donus: tek dilli ham kareler
    out = app / "fastlane" / "screenshots" / locale
    out.mkdir(parents=True, exist_ok=True)
    frames = frames_for(slug)
    made = 0
    spec = DEVICES[device]
    # Everything below was tuned against the 1290x2796 iPhone canvas; scale rather than
    # re-tune so both sets stay visually identical.
    k = H / 2796
    head_y, floor_y, radius = int(210 * k), int(470 * k), int(68 * k)
    # An iPad frame is much squarer than a phone, so a 0.80 width would run off the
    # bottom. Give the wider canvas a narrower shot.
    # An iPad frame is squarer, so the same fraction yields a shorter image; at 0.68 the
    # composition bottom-anchored and left a dead band under the headline. 0.80 fills the
    # canvas the way the phone set does.
    shot_frac = 0.80
    for i, ((src, ctop, cbot, crop), cap) in enumerate(zip(frames, captions), 1):
        shot_path = raw / src
        if not shot_path.exists():
            print(f"  !! missing raw shot {src}", file=sys.stderr)
            continue
        canvas = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(canvas)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=lerp(ctop, cbot, y / H))

        # ONLY the keyword is drawn — no subline, no extra copy (user rule).
        # Rendered by CoreText, not PIL: see render_headline().
        head = cap.get("headline", "")
        if head:
            band = render_headline(head, locale, max_width=int(W * 0.88),
                                   color=HEADLINE_COLOR_BY_SLUG.get(slug, "FFFFFF"))
            canvas.paste(band, ((W - band.width) // 2, head_y - band.height // 2), band)

        shot = Image.open(shot_path).convert("RGB")
        assert_rendered(shot_path, shot)
        if crop:
            shot = shot.crop((0, crop, shot.width, shot.height))
        tw = int(W * shot_frac)
        th = int(tw * shot.height / shot.width)
        y0 = max(floor_y, BOTTOM - th)
        if y0 + th > BOTTOM:
            th = BOTTOM - y0
            shot = shot.crop((0, 0, shot.width, int(th * shot.width / tw)))
        framed = slug in DEVICE_FRAME_SLUGS
        # The body is drawn OUTSIDE the shot, so the shot itself keeps its full width and the
        # bezel eats into the margin instead of into the screen. A bezel taken out of `tw` shrinks
        # the UI on every frame and the text inside stops being legible at store thumbnail size.
        bezel = int(14 * k) if framed else 0
        shot = shot.resize((tw, th), Image.LANCZOS)
        r = radius
        mask = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, tw, th], radius=r, fill=255)
        x = (W - tw) // 2

        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x - bezel - 6, y0 - bezel + 18,
                                              x + tw + bezel + 6, y0 + th + bezel + 30],
                                             radius=r + bezel + 8, fill=(0, 0, 0, 120))
        canvas.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0),
                     sh.filter(ImageFilter.GaussianBlur(28)).split()[3])

        if framed:
            # A white body with a hairline edge — the phone the screen is sitting in.
            ImageDraw.Draw(canvas).rounded_rectangle(
                [x - bezel, y0 - bezel, x + tw + bezel, y0 + th + bezel],
                radius=r + bezel, fill=(255, 255, 255), outline=(214, 232, 255), width=max(2, int(3 * k)))

        canvas.paste(shot, (x, y0), mask)
        if not framed:
            ImageDraw.Draw(canvas).rounded_rectangle([x, y0, x + tw, y0 + th], radius=r,
                                                     outline=(255, 255, 255, 60), width=3)
        canvas.save(out / f"{i:02d}_{spec['suffix']}.png", "PNG")
        made += 1
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--locales", nargs="*")
    ap.add_argument("--device", default="iphone69", choices=sorted(DEVICES),
                    help="App Store canvas to render for")
    ap.add_argument("--raw-dir", help="override the raw-shot directory name under shots/")
    args = ap.parse_args()
    use_device(args.device)
    capdir = ROOT / "apps" / args.slug / "design" / "captions"
    files = sorted(capdir.glob("*.json"))
    if args.locales:
        files = [f for f in files if f.stem in args.locales]
    if not files:
        sys.exit(f"!! caption json bulunamadi: {capdir}")
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        caps = data.get("captions") or []
        if len(caps) < len(frames_for(args.slug)):
            print(f"  !! {f.stem}: only {len(caps)} captions", file=sys.stderr)
        n = build(args.slug, f.stem, caps, args.device, args.raw_dir)
        print(f"{f.stem}: {n} screenshots")


if __name__ == "__main__":
    main()
