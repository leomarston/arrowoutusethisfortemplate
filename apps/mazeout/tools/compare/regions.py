#!/usr/bin/env python3
"""VERIFY V2: the comparison regions for every capture of tools/capture/manifest.json -> tools/compare/regions.json.

Adapted from apps/matchfactory/tools/compare/regions.py (e10a076): the helpers and the conventions are kept; the capture
lists are Arrow Out's (V2, build-4, 2026-09-27), from SPEC-ui's measured frames (design/ui-tokens.json + ui-tokens-2.json
`frame_pt`, every one measured on the research shot the manifest names as the capture's ref) plus a few boxes read off
the reference shots for scene/ground areas.

Boxes are (x, y, w, h) in points on the 393 x 852 reference canvas. Each box sits INSIDE its element (a few pt in from
the measured edges), so a ±2 pt layout difference does not move an edge into the box and the mean colour compares the
element itself. Kinds:
  ui     flat UI chrome (pills, buttons, panels, bars): the strict ΔE ≤ 6 target
  text   a region dominated by copy (EN vs TR captures differ by wording; the reference language is English)
  art    a hero illustration or 3D render (our own art; the colour family must match)
  board  board content (arrows, dots, obstacles; compares the overall tone of a board region)
  dim    a dimmed background (dim opacity and what lies under it)
  bg     a scene background
Nothing above y 52 is compared: the simulator screenshot draws the Dynamic Island there.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOK = {}
for f in ("ui-tokens.json", "ui-tokens-2.json"):
    for k, v in json.load(open(os.path.join(ROOT, "design", f)))["components"].items():
        if v.get("frame_pt"):
            TOK[k] = v["frame_pt"]

R = []


def reg(name, x, y, w, h, kind="ui"):
    return {"name": name, "r": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)], "kind": kind}


def inset(name, x0, y0, x1, y1, d=4, kind="ui"):
    """A box from measured edges (x0, y0)-(x1, y1), moved d pt inside on every side."""
    return reg(name, x0 + d, y0 + d, x1 - x0 - 2 * d, y1 - y0 - 2 * d, kind)


def tok(tid, kind="ui", d=4, name=None):
    """The measured frame of a SPEC-ui token, d pt inside."""
    x, y, w, h = TOK[tid]
    return inset(name or tid, x, y, x + w, y + h, d, kind)


def add(cid, regions):
    R.append({"id": cid, "regions": regions})


# ---------- shared groups ----------------------------------------------------------------------------------------------

def home_top(claw=True):
    g = [tok("home.avatarButton", "ui", 5), tok("home.coinPill"), tok("home.gearButton"),
         tok("home.livesPill", "text", 3), tok("home.coinIcon", "art", 6)]
    if claw:
        g += [tok("home.clawHex", "art", 6), reg("claw.track.l", 70, 121, 16, 16, "ui")]
    return g


def home_scene(tier="normal"):
    g = [reg("scene.wallR", 322, 296, 56, 44, "bg"), reg("scene.platform", 10, 726, 62, 30, "bg"),
         reg("scene.scientist", 160, 196, 76, 70, "art"), reg("scene.console", 110, 300, 60, 40, "art"),
         reg("scene.machine.glass", 118, 416, 158, 100, "art"), reg("scene.machine.side", 98, 425, 14, 80, "art"),
         reg("scene.workerL", 38, 522, 70, 70, "art"), reg("scene.workerR", 282, 522, 70, 70, "art"),
         tok("home.levelCaption", "text", 2)]
    if tier == "normal":
        g += [tok("home.levelPlate", "ui", 4), inset("play.left", 91.1, 628.2, 142, 714.9, 5),
              inset("play.right", 252, 628.2, 302.3, 714.9, 5), inset("play.label", 142, 640, 252, 705, 0, "text"),
              inset("playFrame.bottom", 90, 716, 304, 724, 1)]
    else:
        plate = "home.levelPlateHard" if tier == "hard" else "home.levelPlateSuperHard"
        g += [tok(plate, "ui", 4), inset("play.left", 91.7, 652, 142, 715, 5), inset("play.right", 252, 652, 302.2, 715, 5),
              inset("play.label", 142, 655, 252, 710, 0, "text"),
              tok("home.hardRibbon" if tier == "hard" else "home.superHardRibbon", "text", 3, "tier.ribbon")]
    return g


def home_nav():
    return [reg("nav.bar.l", 3, 800, 26, 44, "ui"), reg("nav.bar.r", 364, 800, 26, 44, "ui"),
            tok("home.navShop", "art", 6), tok("home.navTrophy", "art", 6), tok("home.navHomeIcon", "art", 8),
            inset("nav.homeTile.l", 130, 770, 158, 846, 3), inset("nav.homeTile.r", 236, 770, 264, 846, 3),
            inset("nav.homeLabel", 158, 818, 236, 842, 0, "text")]


def hud(tier="normal"):
    sfx = {"normal": "", "hard": "Hard", "super": "SuperHard"}[tier]
    return [tok("hud.backButton" + sfx, "ui", 5, "hud.back"), tok("hud.pauseButton" + sfx, "ui", 5, "hud.pause"),
            tok("hud.levelTab" + sfx, "text", 2, "hud.levelTab"), tok("hud.stopwatch", "art", 5),
            tok("hud.timerPill" + sfx, "text", 3, "hud.timerPill"), inset("hud.panel.bottom", 120, 110, 300, 118, 1),
            inset("hud.panel.right", 300, 64, 314, 116, 1), tok("hud.heart1", "ui", 5), tok("hud.heart2", "ui", 5),
            tok("hud.heart3", "ui", 5)]


def boosters():
    return [tok("booster.buttonLeft", "ui", 4), tok("booster.buttonRight", "ui", 4), tok("booster.iconLeft", "art", 5),
            tok("booster.iconRight", "art", 5), tok("booster.badgeLeft", "ui", 5),
            reg("booster.trayL.edge", 2, 823, 12, 10, "ui"), reg("booster.trayR.edge", 380, 823, 11, 10, "ui")]


def board_band(y0=135, y1=735):
    return [reg("board.top", 15, y0, 363, (y1 - y0) / 2, "board"), reg("board.bottom", 15, (y0 + y1) / 2, 363, (y1 - y0) / 2, "board")]


def dim_level():
    """The dimmed HUD and board under a level popup."""
    return [reg("dim.hud", 20, 64, 36, 36, "dim"), reg("dim.boardLow", 20, 700, 353, 40, "dim"),
            reg("dim.boosterL", 16, 768, 50, 46, "dim")]


# ---------- home -------------------------------------------------------------------------------------------------------
add("home-L32", home_top(False) + home_scene() + home_nav() + [tok("home.streakBadgeL32", "art", 8, "event.streak")])
add("home-L34-hard", home_top() + home_scene("hard") + home_nav() + [tok("home.streakBadge", "art", 8, "event.streak")])
add("home-L39-super", home_top() + home_scene("super") + home_nav() + [tok("home.streakBadge", "art", 8, "event.streak")])
add("home-L62", home_top() + home_scene() + home_nav() + [
    tok("home.streakBadge", "art", 8, "event.streak"), reg("event.rocket", 16, 298, 60, 44, "art"),
    reg("event.sky", 16, 395, 60, 44, "art"), inset("nav.newsBadge", 326, 772, 339, 785, 2, "ui")])

# ---------- level HUD ----------------------------------------------------------------------------------------------------
add("hud-L32", hud() + boosters() + board_band())
add("hud-L34-hard", hud("hard") + boosters() + board_band())
add("hud-L39-super", hud("super") + boosters() + board_band())

# ---------- level popups -------------------------------------------------------------------------------------------------
add("pause", [tok("pause.ribbon", "text", 8), tok("pause.close", "ui", 8), tok("pause.card", "ui", 10),
              tok("pause.toggleSound", "text", 3), tok("pause.toggleKnob", "ui", 6), tok("pause.iconSound", "art", 4),
              tok("pause.iconHaptic", "art", 4), tok("pause.resume", "text", 6), tok("pause.quit", "text", 6),
              tok("pause.bumperTL", "ui", 8), inset("pause.field.l", 22, 330, 44, 470, 0), inset("pause.bar.bottom", 60, 610, 330, 620, 0)]
      + dim_level())
BAND = [reg("band.rail", 70, 238, 250, 14, "ui"), reg("band.field", 20, 268, 40, 32, "ui"), reg("band.cream.l", 12, 318, 36, 140, "ui"),
        reg("band.field.low", 20, 482, 50, 110, "ui"), reg("band.railBottom", 60, 622, 270, 12, "ui")]
add("quitLevel", BAND + [tok("quitLevel.ribbon", "text", 8), tok("quitLevel.close", "ui", 8), tok("quitLevel.heart", "art", 12),
                         tok("quitLevel.quit", "text", 6), inset("quitLevel.msg", 100, 330, 290, 350, 0, "text")] + dim_level()[:1]
      + [reg("dim.boardLow", 20, 660, 353, 60, "dim")])
add("outOfTime", [tok("outOfTime.title", "text", 6), tok("outOfTime.close", "ui", 8), tok("outOfTime.stopwatch", "art", 25),
                  tok("outOfTime.plus30", "text", 8), tok("outOfTime.addTimeFace", "text", 6), tok("outOfTime.coinGroup", "ui", 6),
                  reg("glow.l", 10, 380, 40, 60, "dim"), reg("glow.r", 343, 380, 40, 60, "dim"), reg("dim.low", 20, 745, 353, 40, "dim")])
add("continue-streak", BAND + [tok("continueStreak.ribbon", "text", 8), tok("continueStreak.close", "ui", 8),
                               tok("continueStreak.chips", "text", 4), tok("continueStreak.chipLit", "ui", 10),
                               tok("continueStreak.playOn", "text", 6), tok("continueStreak.message", "text", 6),
                               tok("continueStreak.coinGroup", "ui", 6), reg("dim.boardLow", 20, 660, 353, 60, "dim")])
add("continue-token", BAND + [tok("continueStreak.ribbon", "text", 8), tok("continueStreak.close", "ui", 8),
                              inset("token.hex", 55, 327, 100, 370, 3, "art"), inset("token.chips", 36, 396, 310, 438, 0, "text"),
                              tok("continueStreak.playOn", "text", 6), tok("continueStreak.coinGroup", "ui", 6),
                              reg("dim.boardLow", 20, 660, 353, 60, "dim")])
add("continue-life", BAND + [tok("continueLife.ribbon", "text", 8), tok("continueLife.close", "ui", 8),
                             tok("continueLife.brokenHeart", "art", 14), tok("continueLife.playOn", "text", 6),
                             tok("continueLife.message", "text", 6), tok("continueLife.coinGroup", "ui", 6),
                             reg("dim.boardLow", 20, 660, 353, 60, "dim")])
add("outOfLives", [tok("outOfLives.heart", "art", 20), tok("outOfLives.close", "ui", 8), tok("outOfLives.coinGroup", "ui", 6),
                   tok("outOfLives.addLives", "text", 6), inset("title", 45, 182, 348, 222, 0, "text"),
                   inset("plus3", 90, 510, 305, 565, 0, "text"), reg("glow.l", 10, 380, 40, 60, "dim"),
                   reg("glow.r", 343, 380, 40, 60, "dim"), reg("dim.low", 20, 745, 353, 40, "dim")])
STRIP = [inset("strip.rail", 0, 703, 70, 716, 1), inset("strip.field", 3, 742, 60, 758, 0), tok("streakRace.logo", "art", 6),
         tok("streakRace.timerChip", "text", 3), tok("streakRace.chips", "text", 4)]
add("levelFailed", [tok("failed.ribbon", "text", 8), tok("failed.close", "ui", 8), tok("failed.card", "ui", 10),
                    tok("failed.brokenHeart", "art", 18), tok("failed.caption", "text", 3), tok("failed.tryAgain", "text", 6),
                    inset("panel.field.l", 22, 300, 46, 480, 0), inset("panel.bar.bottom", 60, 645, 330, 655, 0)] + STRIP
      + dim_level()[:1])


def win(tier):
    p = {"normal": "win", "hard": "winHard", "super": "winSuperHard"}[tier]
    g = [tok(p + ".ribbon", "text", 8, "win.ribbon"), tok("win.close", "ui", 8), tok("win.perfect", "text", 4),
         tok("win.rewardsLabel", "text", 3), tok("win.coins", "art", 18), tok("win.continue", "text", 6),
         inset("panel.field.l", 22, 260, 46, 470, 0), inset("panel.field.r", 347, 260, 371, 470, 0),
         inset("panel.bar.bottom", 60, 625, 330, 635, 0)] + STRIP + dim_level()[:1]
    if tier != "normal":
        g += [tok(p + ".tagRibbon", "text", 6, "win.tagRibbon")]
    return g


add("win-normal", win("normal"))
add("win-hard", win("hard"))
add("win-super", win("super"))


# ---------- unlock overlays ----------------------------------------------------------------------------------------------
def unlock(board=True):
    g = [tok("unlock.title", "text", 6), tok("unlock.subtitle", "text", 3), tok("unlock.icon", "art", 14),
         tok("unlock.card", "text", 6), inset("card.edgeL", 44, 540, 52, 596, 0), inset("card.edgeR", 341, 540, 349, 596, 0)]
    if board:
        g += [reg("dim.boardMid", 20, 640, 353, 70, "dim"), reg("dim.hud", 20, 64, 36, 36, "dim")]
    return g


add("unlock-pipe", unlock())
add("unlock-box", unlock())
add("unlock-elevator", unlock())
add("unlock-corner", unlock())
add("unlock-door", unlock(False))

# ---------- claims, More Lives, booster info ----------------------------------------------------------------------------
add("claim-lives", [tok("claim.title", "text", 6), tok("claim.heart", "art", 10), tok("claim.amount", "text", 4),
                    tok("claim.tap", "text", 4), reg("dim.top", 20, 240, 353, 60, "dim"), reg("dim.low", 20, 560, 353, 60, "dim")])
add("claim-coins", [tok("claimCoins.title", "text", 6), tok("claimCoins.coins", "art", 10), tok("claimCoins.amount", "text", 4),
                    tok("claimCoins.tap", "text", 4), reg("dim.top", 20, 240, 353, 60, "dim"), reg("dim.low", 20, 560, 353, 60, "dim")])
MORE = [tok("moreLives.ribbon", "text", 8), tok("moreLives.close", "ui", 8), tok("moreLives.card", "ui", 16),
        inset("panel.field.l", 22, 260, 46, 640, 0), inset("panel.bar.bottom", 60, 690, 330, 700, 0), reg("dim.low", 20, 725, 353, 40, "dim")]
add("noLives", MORE + [tok("moreLives.heart", "art", 12), tok("moreLives.timerChip", "text", 4), tok("moreLives.refill", "text", 6),
                       tok("moreLives.adLive", "text", 6), tok("moreLives.coinGroup", "ui", 6)])
add("boosterBuy", MORE)

# ---------- pages ------------------------------------------------------------------------------------------------------------
HEADER = [reg("header.l", 14, 58, 40, 36, "ui"), inset("header.lip", 20, 105, 373, 110, 0)]
add("shop", HEADER + [tok("shop.coinPill", "ui", 6), inset("shop.title", 150, 60, 245, 95, 0, "text"),
                      reg("shop.bg.offers", 3, 170, 30, 16, "bg"), tok("shop.offerCard", "ui", 14), tok("shop.offerBadge", "text", 6),
                      tok("shop.offerPrice", "text", 5), tok("shop.sectionPurple", "text", 6),
                      reg("shop.bundle.art", 50, 505, 110, 70, "art"), inset("shop.bundle.strip", 12, 592, 180, 640, 0)] + home_nav()[:2])
add("settings", HEADER + [inset("settings.title", 130, 60, 260, 95, 0, "text"), tok("settings.close", "ui", 8),
                          tok("settings.notifCard", "text", 6), tok("settings.notifToggle", "text", 4), tok("settings.audioCard", "ui", 12),
                          tok("settings.soundBtn", "art", 8), tok("settings.musicBtn", "art", 8), tok("settings.hapticBtn", "art", 8),
                          tok("settings.support", "text", 6), tok("settings.terms", "text", 5), tok("settings.privacy", "text", 5),
                          reg("page.bg", 20, 640, 353, 120, "bg")])
add("terms", HEADER + [tok("settings.close", "ui", 8), reg("page.bg.l", 3, 140, 12, 300, "bg")])
add("profile", HEADER + [tok("profile.close", "ui", 8), tok("profile.card", "ui", 12), tok("profile.avatar", "art", 10),
                         tok("profile.pencil", "art", 8), tok("profile.levelPlate", "text", 6), reg("profile.bg", 20, 620, 353, 120, "bg"),
                         tok("profile.statPill1_1", "text", 4), tok("profile.statPill1_2", "text", 4), tok("profile.statIcon1_1", "art", 6),
                         tok("profile.statIcon1_2", "art", 6), tok("profile.statPill3_1", "text", 4), tok("profile.statPill3_2", "text", 4)])
add("editProfile", [tok("editProfile.ribbon", "text", 8), tok("editProfile.close", "ui", 8), tok("editProfile.card1", "ui", 8),
                    tok("editProfile.nameField", "text", 4), tok("editProfile.card2", "ui", 6), tok("editProfile.tileSel", "art", 8),
                    tok("editProfile.tile22", "art", 8), tok("editProfile.tile33", "art", 8), tok("editProfile.save", "text", 6),
                    inset("panel.field.l", 16, 240, 40, 600, 0), reg("dim.header", 14, 40, 40, 36, "dim")])
add("username", [tok("editProfile.close", "ui", 8), reg("dim.header", 14, 40, 40, 36, "dim")])
LBTAB = [tok("lb.tabStrip", "ui", 3, "lb.strip") if "lb.tabStrip" in TOK else reg("lb.strip", 3, 113, 6, 50, "ui"),
         inset("lb.title", 100, 60, 293, 95, 0, "text"), tok("lb.timerChip", "text", 3)]
add("lb-weekly", HEADER + LBTAB + [tok("lb.tabWeeklyOn", "text", 4), tok("lb.tabWorldOff", "text", 4), tok("lb.tabCountryOff", "text", 4),
                                    tok("lb.weeklyLogo", "art", 4), tok("lb.info", "ui", 5), tok("lb.podium1", "art", 20),
                                    tok("lb.podium2", "art", 20), tok("lb.podium3", "art", 20), tok("lb.rowMe", "text", 6),
                                    tok("lb.row", "text", 6), tok("lb.navTab", "text", 6)])
add("lb-world", HEADER + LBTAB + [inset("tab.weekly.off", 14, 128, 128, 170, 0, "text"), inset("tab.world.on", 141, 128, 252, 170, 0, "text"),
                                   inset("tab.country.off", 264, 128, 375, 170, 0, "text"), tok("lb.worldRow", "text", 5),
                                   tok("lb.hexGold", "art", 5), reg("lb.bg", 386, 300, 5, 300, "bg"), tok("lb.navTab", "text", 6)])
add("lb-country", HEADER + LBTAB + [inset("tab.weekly.off", 14, 128, 128, 170, 0, "text"), inset("tab.world.off", 141, 128, 252, 170, 0, "text"),
                                     inset("tab.country.on", 264, 128, 375, 170, 0, "text"), tok("lb.countryRow", "text", 5),
                                     reg("lb.bg", 386, 300, 5, 300, "bg"), tok("lb.navTab", "text", 6)])
add("weeklyInfo", [tok("wkInfo.mazeIcon", "art", 10), tok("wkInfo.podium", "art", 20), tok("wkInfo.coins", "art", 16),
                   tok("wkInfo.trophy", "art", 8), tok("wkInfo.arrow1", "art", 6), tok("wkInfo.arrow2", "art", 6),
                   inset("title", 80, 50, 313, 92, 0, "text"), inset("tap", 110, 776, 283, 800, 0, "text"), reg("dim.r", 360, 150, 25, 100, "dim")])
add("weeklyTutorial", [tok("wkTut.card", "text", 6), tok("wkTut.arrow", "art", 12), tok("wkTut.trophyTab", "ui", 10),
                       reg("dim.scene", 30, 150, 80, 60, "dim"), reg("dim.nav", 20, 790, 100, 40, "dim")])
add("streakRace", [tok("streak.header", "art", 30), tok("streak.close", "ui", 8), tok("streak.info", "ui", 8), tok("streak.logo", "art", 6),
                   inset("streak.band.field", 3, 360, 30, 470, 0), tok("streak.chips", "text", 4), tok("streak.timerChip", "text", 3),
                   inset("streak.subtitle", 20, 356, 373, 380, 0, "text"), tok("streak.row1", "text", 5),
                   tok("streak.row2", "text", 5), tok("streak.row3", "text", 5)])
add("streakRace-fresh", [tok("streak.close", "ui", 8), tok("streak.info", "ui", 8), tok("streak.chips", "text", 4),
                         inset("streak.band.field", 3, 360, 30, 470, 0), tok("streak.row1", "text", 5)])
add("rocketRace", [reg("rocket.header", 20, 40, 300, 120, "art"), tok("rocket.band", "text", 6), tok("rocket.logo", "art", 10),
                   tok("rocket.timerTag", "text", 4), reg("rocket.lanes.l", 5, 345, 70, 80, "bg"), reg("rocket.lanes.r", 318, 345, 70, 80, "bg"),
                   reg("rocket.tiles", 5, 755, 383, 80, "text")])
add("rocketOffer", [tok("rocketOffer.panel", "art", 30), tok("rocketOffer.logo", "art", 12), tok("rocketOffer.close", "ui", 8),
                    tok("rocketOffer.timer", "text", 4), tok("rocketOffer.stages", "text", 6), tok("rocketOffer.start", "text", 6),
                    reg("dim.low", 20, 725, 353, 40, "dim")])
add("skyJump", [tok("skyMap.header", "text", 8), tok("skyMap.close", "ui", 8), tok("skyMap.info", "ui", 6),
                reg("sky.bg", 20, 230, 100, 100, "bg"), reg("sky.bg2", 280, 400, 100, 100, "bg"), tok("skyMap.tap", "text", 4)])
add("skyOffer", [tok("skyJump.panel", "art", 30), tok("skyJump.logo", "art", 10), tok("skyJump.close", "ui", 8),
                 tok("skyJump.timerChip", "text", 3), tok("skyJump.stages", "text", 6), tok("skyJump.start", "text", 6),
                 tok("skyJump.rules", "text", 4), reg("dim.low", 20, 725, 353, 40, "dim")])
add("claw", [tok("claw.header", "art", 40), tok("claw.close", "ui", 8), tok("claw.infoButton", "ui", 6), tok("claw.logo", "art", 6),
             inset("claw.band.field", 3, 300, 16, 430, 0), tok("claw.timerChip", "text", 3), tok("claw.subtitle", "text", 3),
             tok("claw.chevrons", "text", 4), tok("claw.progressBar", "text", 4), tok("claw.ladderRail", "ui", 5),
             reg("claw.bg", 20, 470, 30, 250, "bg")])
add("clawInfo", [tok("clawInfo.title", "text", 6), tok("clawInfo.mazeIcon", "art", 10), tok("clawInfo.chips", "text", 6),
                 tok("clawInfo.coins", "art", 8), tok("clawInfo.caption1", "text", 4), tok("clawInfo.caption2", "text", 4),
                 reg("dim.r", 360, 600, 25, 100, "dim")])

add("loading", [tok("loading.logo", "art", 10), tok("loading.label", "text", 4)])

# ---------- FTUE (the video is the OLDER skin: blue arrows on a light-blue ground, 4 boosters; layout/centring only) --------
for k in (1, 2, 3, 4):
    add(f"ftue-s{k}", [tok("hud.levelTab", "text", 2), tok("hud.timerPill", "text", 3), tok("hud.backButton", "ui", 5),
                       tok("hud.pauseButton", "ui", 5), reg("board.centre", 116, 360, 160, 160, "board")]
        + ([reg("tutorial.caption", 75, 271.5, 241, 35.2, "text")] if k == 1 else []))
add("L5", [reg("board.centre", 96, 330, 200, 200, "board")])
for k in (2, 3, 4):
    add(f"ftue-flow-s{k}", [tok("hud.levelTab", "text", 2), tok("hud.timerPill", "text", 3), tok("hud.backButton", "ui", 5),
                            tok("hud.pauseButton", "ui", 5), reg("board.centre", 116, 360, 160, 160, "board")])

# ---------- key-sequence freezes: only position-free regions (the labs pick their own arrows; the rest is LOOKED at) --------
add("fx-freeze", [reg("frost.left", 0, 440, 6, 40, "ui"), reg("frost.right", 387, 440, 6, 40, "ui"), reg("frost.bottom", 150, 842, 90, 8, "ui"),
                  inset("freeze.tray", 92.7, 118.4, 185.4, 143.4, 3, "ui"), inset("freeze.digit", 100, 122, 115, 138, 0, "text"),
                  tok("hud.stopwatch", "art", 4, "freeze.stopwatch"), tok("hud.heart1", "ui", 5), tok("hud.pauseButton", "ui", 5)])
for tau in ("005", "015"):
    add(f"fx-heart-{tau}", [tok("hud.heart1", "ui", 5), tok("hud.heart2", "ui", 5), tok("hud.heart3", "art", 2, "heart3.breaking")])


if __name__ == "__main__":
    out = os.path.join(HERE, "regions.json")
    with open(out, "w") as f:
        json.dump({"about": __doc__.strip().split("\n")[0], "units": "pt on 393x852", "shots": R}, f, indent=1)
    print(out, len(R), "captures,", sum(len(s["regions"]) for s in R), "regions")
