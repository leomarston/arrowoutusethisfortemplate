# Video index — the owner's two gameplay videos

Machine-readable: `research/video-index.json` (every tap, screen and popup with times). Built by `research/video-tools/vindex.py`
(`vindex.py build V1 V2 && vindex.py write`). Frames: `research/video-frames/` (gitignored; `vgrab V1|V2 OUTDIR T` re-grabs any exact frame).

| video | file | length | fps | size |
|---|---|---|---|---|
| V1 | `research/video/owner/V1-levels-01-20.mp4` | 505.1 s | 25.00 | 592x1280 px (393x852 pt; pt = px x 0.6639) |
| V2 | `research/video/owner/V2-levels-11-38.mp4` | 1683.5 s | 59.64 | 592x1280 px (393x852 pt; pt = px x 0.6639) |

Times are video seconds (m:ss.ss). t_board = the clean start frame (`research/video-frames/V?/L0NN-start.png`).
Taps = touch-indicator discs on the board; exit/bump counts are the index's approximation (the replay check in
`vextract.py replay` decides per arrow). "left at clear" = HUD timer (OCR) on the frame the board is cleared.

## V1 — levels

| level | label | tag | first | board | 1st tap | clear | win | result | taps | exit | bump | timer | left at clear | reward | before (popups) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Levels 1-4 (stage 1) |  | 0:00.52 | 0:00.72 | 0:01.64 | 0:05.20 | - | stage_clear | 4 | 2 | 0 | 3:00 | 2:59 |  | loading "MAZЕ / OUT! / Loading.." |
| 2 | Levels 1-4 (stage 2) |  | 0:05.80 | 0:07.92 | 0:08.04 | 0:10.36 | - | stage_clear | 6 | 6 | 0 | 3:00 | 2:58 |  |  |
| 3 | Levels 1-4 (stage 3) |  | 0:11.00 | 0:12.32 | 0:12.44 | 0:17.44 | - | stage_clear | 6 | 6 | 0 | 3:00 | 2:56 |  |  |
| 4 | Levels 1-4 (stage 4) |  | 0:17.88 | 0:19.36 | 0:19.48 | 0:24.12 | 0:24.20 | win | 5 | 5 | 0 | 3:00 | 2:56 | 80 |  |
| 5 | Level 5 |  | 0:28.32 | 0:30.12 | 0:30.24 | 0:41.64 | 0:41.72 | win | 15 | 15 | 0 | 3:00 | 2:50 | 20 |  |
| 6 | Level 6 |  | 0:44.96 | 0:46.60 | 0:46.88 | 1:09.08 | 1:09.84 | win | 27 | 26 | 0 | 3:00 | 2:38 | 20 |  |
| 7 | Level 7 |  | 1:20.12 | 1:21.04 | 1:21.16 | 1:31.32 | 1:31.40 | win | 13 | 13 | 0 | 3:00 | 2:50 | 20 | dark "3:00"; unlock "3:00 / Linked Arrows! / Unlocked! / LINKED ARROWS move" |
| 8 | Level 8 |  | 1:37.12 | 1:39.00 | 1:39.12 | 1:49.52 | 1:50.08 | win | 15 | 14 | 0 | 3:00 | 2:50 | 20 |  |
| 9 | Level 9 |  | 1:58.28 | 2:00.12 | 2:00.24 | 2:15.68 | 2:16.44 | win | 27 | 27 | 0 | 3:00 | 2:44 | 20 |  |
| 10 | Level 10 |  | 2:22.16 | 2:23.44 | 2:23.56 | 2:56.24 | 2:57.00 | win | 35 | 33 | 0 | 3:00 | 2:27 | 20 |  |
| 11 | Level 11 |  | 3:05.88 | 3:07.76 | 3:07.88 | 3:16.96 | 3:17.44 | win | 16 | 15 | 0 | 3:00 | 2:51 | 20 | dark "3:00 / Curtain! / =A1AA"; unlock "3:00 / Curtain! / Unlocked! / Clear required amount of" |
| 12 | Level 12 |  | 3:21.80 | 3:23.08 | 3:23.20 | 3:38.20 | 3:38.96 | win | 23 | 22 | 0 | 3:00 | 2:45 | 20 |  |
| 13 | Level 13 |  | 3:45.28 | 3:48.68 | 3:48.80 | 4:10.04 | 4:10.68 | win | 26 | 24 | 0 | 3:00 | 2:39 | 20 |  |
| 14 | Level 14 |  | 4:20.88 | 4:22.44 | 4:22.56 | 4:32.24 | 4:32.60 | win | 15 | 15 | 0 | 3:00 | 2:51 | 20 |  |
| 15 | Level 15 |  | 4:38.48 | 4:39.72 | 4:39.84 | 5:13.80 | 5:14.40 | win | 44 | 43 | 0 | 3:00 | 2:27 | 20 |  |
| 16 | Level 16 |  | 5:18.64 | 5:20.16 | 5:20.28 | 5:32.88 | 5:33.68 | win | 21 | 21 | 0 | 3:00 | 2:47 | 20 |  |
| 17 | Level 17 |  | 5:39.12 | 5:40.72 | 5:40.84 | 6:20.76 | 6:21.16 | win | 46 | 40 | 0 | 3:00 | 2:08 | 20 |  |
| 18 | Level 18 |  | 6:29.36 | 6:31.00 | 6:31.12 | 6:44.16 | 6:44.76 | win | 21 | 21 | 0 | 3:00 | 2:47 | 20 |  |
| 19 | Level 19 | Hard | 6:51.68 | 6:55.56 | 6:55.68 | 7:43.20 | 7:43.96 | win | 58 | 55 | 0 | 3:00 | 2:13 | 60 |  |
| 20 | Level 20 |  | 7:54.00 | 7:55.32 | 7:55.44 | 8:10.72 | 8:11.16 | win | 19 | 19 | 0 | 3:00 | 2:45 | 20 |  |

Captions on start frames (OCR): L1: Tap to move!

Mistakes (confirmed heart losses): none

## V2 — levels

| level | label | tag | first | board | 1st tap | clear | win | result | taps | exit | bump | timer | left at clear | reward | before (popups) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | Level 11 |  | 1:19.14 | 1:32.01 | 1:32.13 | 1:41.77 | 1:42.44 | win | 20 | 20 | 0 | 3:00 | 2:50 | 20 | other "•al 5G 074 / grand"; loading "MAZE / OUT! / Loading."; loading "Loading..."; loading "MAZE / OUT! / Loading..."; leaderboard "Leaderboard / Weekly World  / in-level: quit@1:20.60; pause@1:23.50 |
| 12 | Level 12 |  | 1:50.04 | 1:52.14 | 1:52.23 | 2:12.67 | 2:13.08 | win | 23 | 22 | 0 | 3:00 | 2:39 | 20 |  |
| 13 | Level 13 |  | 2:21.38 | 2:27.80 | 2:27.90 | 3:04.30 | 3:05.17 | win | 32 | 31 | 0 | 3:00 | 2:24 | 20 |  |
| 14 | Level 14 |  | 3:13.80 | 3:14.94 | 3:15.04 | 3:31.07 | 3:31.44 | win | 15 | 13 | 0 | 3:00 | 2:44 | 20 |  |
| 15 | Level 15 |  | 3:39.37 | 3:41.37 | 3:41.47 | 4:33.60 | 4:33.96 | win | 47 | 47 | 0 | 3:00 | 2:08 | 20 |  |
| 16 | Level 16 |  | 4:42.94 | 4:44.65 | 4:44.76 | 5:00.74 | 5:01.41 | win | 24 | 22 | 0 | 3:00 | 2:44 | 20 |  |
| 17 | Level 17 |  | 5:15.66 | 5:17.81 | 5:17.91 | 6:20.60 | 6:21.27 | win | 46 | 42 | 0 | 3:00 | 1:57 | 20 |  |
| 18 | Level 18 |  | 6:28.83 | 6:29.94 | 6:30.04 | 6:49.27 | 6:49.67 | win | 20 | 20 | 0 | 3:00 | 2:41 | 20 |  |
| 19 | Level 19 | Hard | 6:56.18 | 7:00.91 | 7:01.01 | 8:09.33 | 8:10.00 | win | 61 | 53 | 0 | 3:00 | 1:52 | 60 |  |
| 20 | Level 20 |  | 8:18.74 | 8:20.20 | 8:20.33 | 8:37.90 | 8:38.57 | win | 20 | 19 | 0 | 3:00 | 2:42 | 20 |  |
| 21 | Level 21 |  | 8:48.83 | 8:50.64 | 8:50.75 | 9:07.04 | 9:07.68 | win | 24 | 24 | 0 | 3:00 | 2:44 | 20 | dark "0035 / ailat"; unlock "Pipe! / Unlocked! / 3 / Pass arrows through the" |
| 22 | Level 22 |  | 9:14.10 | 9:15.88 | 9:15.98 | 9:48.00 | 9:48.64 | win | 29 | 28 | 0 | 3:00 | 2:28 | 20 |  |
| 23 | Level 23 |  | 9:55.66 | 9:59.47 | 9:59.57 | 10:42.17 | 10:42.81 | win | 37 | 31 | 0 | 3:00 | 2:17 | 20 |  |
| 24 | Level 24 |  | 10:51.53 | 10:54.01 | 10:54.13 | 11:43.61 | 11:44.28 | win | 28 | 26 | 0 | 3:00 | 2:11 | 20 |  |
| 25 | Level 25 | Hard | 11:50.93 | 11:52.75 | 11:52.86 | 13:12.30 | 13:12.94 | win | 60 | 54 | 0 | 3:00 | 1:40 | 60 |  |
| 26 | Level 26 |  | 13:19.76 | 13:21.21 | 13:21.31 | 13:51.03 | 13:51.67 | win | 26 | 26 | 0 | 3:00 | 2:30 | 20 |  |
| 27 | Level 27 |  | 13:58.45 | 14:00.00 | 14:00.10 | 14:53.98 | 14:54.61 | win | 41 | 39 | 0 | 3:00 | 2:06 | 20 |  |
| 28 | Level 28 |  | 15:01.30 | 15:02.61 | 15:02.71 | 16:11.13 | 16:11.81 | win | 42 | 38 | 0 | 3:00 | 1:51 | 20 |  |
| 29 | Level 29 | Super Hard | 16:18.45 | 16:22.47 | 16:22.60 | 19:03.18 | 19:03.76 | win | 67 | 61 | 0 | 3:00 | 0:20 | 100 |  |
| 30 | Level 30 |  | 19:11.68 | 19:12.93 | 19:13.04 | 19:32.60 | 19:33.27 | win | 25 | 25 | 0 | 3:00 | 2:40 | 20 |  |
| 31 | Level 31 |  | 19:43.23 | 19:44.04 | 19:44.14 | 20:07.51 | 20:08.16 | win | 31 | 30 | 0 | 3:00 | 2:36 | 20 | dark "CACAO"; unlock "Elevator! / Unlocked! / Clear all arrows on the / ELEVATOR to activate"; unlock "010 / Elevator! / Unlocked! / Clear all arrows on the" |
| 32 | Level 32 |  | 20:15.04 | 20:16.38 | 20:16.50 | 20:51.34 | 20:51.67 | win | 41 | 36 | 2 | 3:00 | 2:26 | 20 |  |
| 33 | Level 33 |  | 20:58.46 | 20:59.17 | 21:00.24 | 21:58.57 | 21:59.21 | win | 47 | 43 | 0 | 3:00 | 2:02 | 20 |  |
| 34 | Level 34 |  | 22:06.57 | 22:10.78 | 22:10.88 | 22:43.87 | 22:44.55 | win | 30 | 29 | 0 | 3:00 | 2:27 | 20 |  |
| 35 | Level 35 | Hard | 22:54.27 | 22:59.07 | 22:59.17 | 24:56.46 | 24:57.13 | win | 89 | 86 | 0 | 3:00 | 1:03 | 60 |  |
| 36 | Level 36 |  | 25:03.91 | 25:06.21 | 25:06.31 | 25:39.13 | 25:39.81 | win | 36 | 35 | 0 | 3:00 | 2:28 | 20 |  |
| 37 | Level 37 |  | 25:46.38 | 25:49.24 | 25:49.35 | 26:59.66 | 27:00.30 | win | 54 | 52 | 0 | 3:00 | 1:49 | 20 |  |
| 38 | Level 38 |  | 27:06.81 | 27:11.10 | 27:11.20 | 27:51.34 | 27:51.57 | win | 33 | 33 | 0 | 3:00 | 2:20 | 20 |  |

Mistakes (confirmed heart losses): L32 tap 20:35.11 -> heart 20:35.28, L32 tap 20:49.28 -> heart 20:49.44

## V1 — screens and popups (non-play)

| from | to | kind | text (OCR, first lines) |
|---|---|---|---|
| 0:00.04 | 0:00.48 | loading | MAZЕ / OUT! / Loading.. |
| 0:25.00 | 0:25.50 | other | 2:56 / Levels 1-4 / MAZE / oUur / 3 3 3 3 |
| 0:25.52 | 0:27.50 | dark | 56 / MAZE / OUT! |
| 0:27.52 | 0:28.28 | win_panel | 2:56 / Level 1-4 / Perfect! / Rewards: / 80 / Continue |
| 0:42.52 | 0:43.02 | other | 2:50 / Level S / MAZE / OUur / 3 3 3 3 |
| 0:43.00 | 0:44.02 | dark | Level 5 / MAZE / OUT! |
| 0:44.00 | 0:44.92 | win_panel | Level S / Perfect! / Rewards: / 20 / Continue |
| 1:10.72 | 1:11.02 | other | 2:38 / Level 6 / MAZE / 3 3 3 3 |
| 1:11.00 | 1:12.50 | dark | :38 / Levèl 6 / MAZE / OUT! |
| 1:12.52 | 1:14.02 | win_panel | 2:38 / Level 6 / Perfect! / Rewards: / 20 / Continue |
| 1:14.00 | 1:16.50 | home | 1096 Full / LEVEL / 7 / Play / Home |
| 1:16.52 | 1:17.50 | dark | 3:00 |
| 1:17.52 | 1:20.02 | unlock | 3:00 / Linked Arrows! / Unlocked! / LINKED ARROWS move / together! |
| 1:32.20 | 1:32.50 | other | 2:50 / MAZE / oUrr / 3 3 3 3 |
| 1:32.52 | 1:33.50 | dark | MAZE / OUT! |
| 1:33.52 | 1:35.02 | win_panel | 2:5 / Level 7 / Perfect! / Rewards: / 20 / Continue |
| 1:35.00 | 1:37.02 | home | 1128 Full / LEVEL / 8 / Play / Home |
| 1:51.00 | 1:51.50 | other | 2:50 / MAZE / OUT / 3 3 3 3 |
| 1:51.52 | 1:54.02 | dark | MAZE / OUT! |
| 1:54.00 | 1:55.02 | win_panel | 2:50 / Level 8 / Perfect! / Rewards: / 20 / Continue |
| 1:55.00 | 1:58.24 | home | 1160 Full / LEVEL / Play / Home |
| 2:17.52 | 2:19.50 | win_panel | 2:4 / Level 9 / Perfect! / Rewards: / 20 / Continue |
| 2:19.52 | 2:22.12 | home | 1180 Full / LEVEL / 10 / Play / Home |
| 2:58.00 | 2:58.50 | other | 2:27 / MАZE / •UT. / 3 |
| 2:58.52 | 2:59.50 | dark | 2:27 / MAZE / OUT! |
| 2:59.52 | 3:00.50 | win_panel | 2:27 / Level 10 / Perfect! / Rewards: / 20 / Continue |
| 3:00.52 | 3:03.50 | home | 1200 Full / LEVEL / 11 / Play / Home |
| 3:03.52 | 3:04.50 | dark | 3:00 / Curtain! / =A1AA |
| 3:04.52 | 3:05.84 | unlock | 3:00 / Curtain! / Unlocked! / Clear required amount of / arrows to open the / CURTAIN! |
| 3:18.52 | 3:20.02 | win_panel | Level 21 / Perfect! / Rewards: / 20 / Continue |
| 3:20.00 | 3:21.76 | home | 1208 Full / LEVEL / 12 / Play / Home |
| 3:40.00 | 3:40.50 | other | 2:45 / MАЗЕ / OUT! / 3 |
| 3:40.52 | 3:41.50 | dark | MAZE / OUT! |
| 3:41.52 | 3:42.50 | win_panel | Level 22 / Perfect! / Rewards: / 20 / Continue |
| 3:42.52 | 3:45.24 | home | 1240 Full / LEVEL / 13 / Play / Home |
| 4:11.56 | 4:12.02 | other | 2:39 / MAZE / oUrr / 3 3 3 3 |
| 4:12.00 | 4:14.50 | dark | 2:39 / MAZE / OUT! |
| 4:14.52 | 4:18.02 | win_panel | 2:39 / Level 13 / Perfect! / Rewards: / 20 / Continue |
| 4:18.00 | 4:20.84 | home | 1256 Full / LEVEL / 14 / Play / Home |
| 4:33.48 | 4:33.90 | other | 2:51 / MAZE / 3 3 3 3 |
| 4:33.92 | 4:34.90 | dark | 191 / MAZE / OUT! |
| 4:34.92 | 4:35.90 | win_panel | Level 14 / Perfect! / Rewards: / 20 / Continue |
| 4:35.92 | 4:38.42 | home | 1272 Full / LEVEL / 15 / Play / Home |
| 5:15.40 | 5:15.90 | win_panel | 2:27 / Level 2S / Perfect! / Rewards: / 20 / Continue |
| 5:15.92 | 5:16.42 | win_panel | Level 1S / Perfect! / Rewards: / 20 / Continue |
| 5:16.40 | 5:18.60 | home | 1284 S Full / LEVEL / 16 / Play / fa- / Home |
| 5:34.48 | 5:34.90 | other | 2:47 / MАZЕ / oUrr / 3 3 3 3 |
| 5:34.92 | 5:35.42 | dark | 2:47 / MAZE / OUT! |
| 5:35.40 | 5:36.90 | win_panel | 2:47 / Level 16 / Perfect! / Rewards: / 20 / Continue |
| 5:36.92 | 5:39.08 | home | 1316 Full / LEVEL / 17 / Play / Home |
| 6:22.40 | 6:22.90 | other | 2:08 / MAZE / OUrr / 3 3 3 3 |
| 6:22.92 | 6:23.90 | dark | MAZE / OUT! |
| 6:23.92 | 6:25.42 | win_panel | 2:081 / Level 27 / Perfect! / Rewards: / 20 / Continue |
| 6:25.40 | 6:29.32 | home | 1340 S Full / LEVEL / 18 / Play / a- / Home |
| 6:45.64 | 6:45.90 | other | 2:47 / MAZE / oUrr / 3 3 3 3 |
| 6:45.92 | 6:46.90 | dark | 2:47 / MAZE / OUT! |
| 6:46.92 | 6:47.90 | win_panel | 2:47- / Level 18 / Perfect! / Rewards: / 20 / Continue |
| 6:47.92 | 6:51.64 | home | 1360 Full / LEVEL / 19 / Hard Level / Play / Home |
| 7:44.92 | 7:45.42 | other | Hard Level / 2:13 / MAZE / OUT / 3 |
| 7:45.40 | 7:47.90 | dark | rd Le / MAZE / OUT! |
| 7:47.92 | 7:50.90 | win_panel | Hard Leve / Hard Level / Level 19 / Perfect! / Rewards: / 60 |
| 7:50.92 | 7:53.96 | home | 1420 Full / LEVEL / 20 / Play / Home |
| 8:12.00 | 8:12.42 | other | 2:45 / MAZE / 3 3 3 3 |
| 8:12.40 | 8:14.90 | dark | 2:45 / MAZE / OUT!) |
| 8:14.92 | 8:15.42 | win_panel | 2:45 / Level 20 / Perfect! / Rewards: / 20 / Continue |
| 8:15.40 | 8:18.42 | home | 1432 Full / LEVEL / 21 / Play / Home |
| 8:18.40 | 8:19.42 | other |  |
| 8:19.40 | 8:19.90 | dark | SHARE |
| 8:19.92 | 8:25.08 | other | SUBSCRIBE |

## V2 — screens and popups (non-play)

| from | to | kind | text (OCR, first lines) |
|---|---|---|---|
| 0:00.02 | 0:02.51 | other | •al 5G 074 / grand |
| 0:02.50 | 0:05.50 | notification_prompt | Chế độ trò chơi / Mros / OUT! / "Maze Out!" muốn gửi / thông báo cho bạn / Thông báo có thể bao gồm |
| 0:05.50 | 0:08.01 | loading | MAZE / OUT! / Loading. |
| 0:08.00 | 0:08.50 | phone_ui | Loading... / [phone system UI / notification: personal text omitted] |
| 0:08.50 | 0:10.01 | phone_ui | [phone system UI / notification: personal text omitted] |
| 0:10.01 | 0:10.51 | loading | Loading... |
| 0:10.51 | 0:11.50 | loading | MAZE / OUT! / Loading... |
| 0:11.50 | 0:18.51 | home | 1200 5 Full / LEVEL / 11 / Play / Home |
| 0:18.51 | 0:19.01 | shop | Shop / Weekl / Special Offers / 1 000 1h / ial Offer 0.99 $ / Bundles |
| 0:19.00 | 0:22.01 | shop | 1200 Shop / Special Offers / 90% / OFF / 1000 1h / Special Offer 0.99 $ |
| 0:22.00 | 0:22.50 | shop | 1200 Shop / Special Otters / 90% / OFF / 1000 xI 1h / Special Offer 0.99 $ |
| 0:22.50 | 0:23.00 | shop | 1200 Shop / 90% / OFF / 1000 1h / Special Offer 0.99 $ / Bundles |
| 0:23.00 | 0:23.50 | shop | 1200 Shop / Bundles / 2000 3h / Mini Bundle 4.99 $ / 4000 x3 6h / Epic Bundle 9.99 $ |
| 0:23.51 | 0:24.51 | shop | 1200 Shop / Bundles / 2000 3h / Mini Bundle 4.99 $ / 4000 x3 6h / Epic Bundle 9.99 $ |
| 0:24.51 | 0:25.01 | shop | 1200 Shop / 2000 3h / Mini Bundle 4.99 $ / $4000 x3 6h / Epic Bundle 9.99 $ / Popular |
| 0:25.00 | 0:25.50 | shop | 1200 Shop / $4000 x3 6h / Epic Bundle 9.99 $ / Popular / 8-000 x8 12h / Elite Bundle 19.99 $ |
| 0:25.50 | 0:26.50 | shop | 1200 Shop / Popular / 8-000 x8 12h / Elite Bundle 19.99 $ / 20.000 x28 36h / Mega Bundle 49.99 $ |
| 0:26.51 | 0:27.01 | shop | 1200 Shop / 20:000 x18 36h / Mega Bundle 49.99 $ / Best Value / 60:.000 x36 72h / Legendary Bundle 99.99 $ |
| 0:27.01 | 0:27.51 | shop | 1200 Shop / 20.000 x18 36h / Mega Bundle 49.99 $ / Best Value / 60.000 x36 72h / Legendary Bundle 99.99 $ |
| 0:27.50 | 0:28.50 | shop | 1200 Shop / 60 000 x36 72h / Legendary Bundle 99.99 $ / Coins / 1000 5 000 20 000 / 1.99 $ 7.99 $ 14.99 $ |
| 0:28.50 | 0:29.00 | shop | Shop / Week / 30 000 x36 72h / dary Bundle 99.99 $ / Coins / 5 000 10 000 W |
| 0:29.01 | 0:31.00 | leaderboard | Leaderboard / Weekly World Country / Reach level 50 / to compete in / Weekly Contest! / Leaderboard |
| 0:31.00 | 0:33.50 | leaderboard | Leaderboard / Weekly World Country / Level / 229 player_b5s19jr 13 / Level / 130 player_d637jt8 22 |
| 0:33.50 | 0:34.50 | leaderboard | Leaderboard / Weekly World Country / Level / 228 player Top59yk 14 / Level / 229 player_b5s19jr 13 |
| 0:34.51 | 0:36.01 | other | Adventure / Coming Soon / D / Adventure |
| 0:36.00 | 0:48.50 | settings | Settings / Notifications ON / Sound Music Haptic / Support / Terms Privacy / Settings |
| 0:48.51 | 0:50.01 | home | 1200 5 Full / 000 / LEVEL / 11 / Play / Home |
| 0:50.00 | 0:52.51 | profile | Profile / Enter Username / Create your username: / Continue / Q W E T Y00o P / S D F G J K L |
| 0:52.50 | 0:55.01 | leaderboard | Profile / Level / 11 / Hihi / General Stats / Weekly Contest |
| 0:55.01 | 0:55.51 | home | 1200 5 Full / + / LEVEL / 11 / Play / Home |
| 0:55.50 | 0:56.50 | leaderboard | Profile / Level / 11 / Hihi / General Stats / Weekly Contest |
| 0:56.50 | 1:09.01 | profile | Edit Profile / Hihi / Save |
| 1:09.01 | 1:10.50 | leaderboard | Profile / Level / 11 / Hihi / General Stats / Weekly Contest |
| 1:10.50 | 1:11.51 | home | 1200 5 Full / LEVEL / 11 / Play / Home |
| 1:11.51 | 1:12.51 | shop | Shop / 90% / OFF / 1 000 XI 1h / Special Offer 0.99 $ / 2000 3h |
| 1:12.50 | 1:16.00 | home | 1200 5 Full / LEVEL / 11 / Play / Home |
| 1:16.00 | 1:17.01 | dark | 0082 / S |
| 1:17.01 | 1:19.00 | unlock | 3:00 / Box! / Unlocked! / 5 / Clear required amount of / arrows to break the BOX! |
| 1:19.00 | 1:19.11 | other | 3:00 / 13 |
| 1:20.60 | 1:22.50 | quit | 3:00 / Quit Level? / You will lose a life! / Quit / 13 |
| 1:23.50 | 1:26.70 | pause | 3:00 / Paused / Sound Haptic / &03 / Resume Quit |
| 1:28.24 | 1:28.51 | other | 3:00 / 8 / 13 |
| 1:28.51 | 1:29.01 | pause | 3:00 / Paused / Sound Haptic / &03 / Resume Quit / 13 |
| 1:46.00 | 1:46.50 | win_splash | 2:50 / Well Done! |
| 1:46.50 | 1:47.50 | win_panel | 2:50 / Level 11 / Perfect! / Rewards: / 20 / Continue |
| 1:47.51 | 1:50.00 | home | 1220 5 Full / LEVEL / 12 / Play / Home |
| 2:16.70 | 2:17.00 | other | 2:39 |
| 2:17.00 | 2:18.00 | win_panel | Level 12 / Perfect! / Rewards: / 20 / Continue |
| 2:18.00 | 2:21.34 | home | 1240 5 Full / LEVEL / 13 / Play / Home |
| 3:08.74 | 3:09.01 | other | 2:24 / 3 |
| 3:09.01 | 3:11.50 | win_panel | 2:24 / Level 13 / Perfect! / Rewards: / 20 / Continue |
| 3:11.51 | 3:13.77 | home | 1256 5 Full / LEVEL / 14 / Play / Home |
| 3:35.00 | 3:35.50 | other | 2:44 / Wall Donc! |
| 3:35.50 | 3:36.50 | win_panel | 2:44 / Level 14 / Perfect! / Rewards: / 20 / Continue |
| 3:36.51 | 3:39.34 | home | 1280 5 Full / LEVEL / 15 / Play / Home |
| 4:37.57 | 4:38.00 | win_splash | 2:08 / Well Done! |
| 4:38.01 | 4:39.01 | win_panel | 2:08 / Level 15 / Perfect! / Rewards: / 20 / Continue |
| 4:39.01 | 4:42.90 | home | 1300 5 Full / 4 / LEVEL / 16 / Play / Home |
| 5:05.00 | 5:05.50 | win_splash | 2:44 / Well Done! |
| 5:05.50 | 5:08.00 | win_panel | 2:44 / Level 16 / Perfect! / Rewards: / 20 / Continue |
| 5:08.00 | 5:15.63 | home | 1320 5 Full / LEVEL / 17 / Play / Home |
| 6:25.01 | 6:26.00 | win_panel | 1:57 / Level 17 / Perfect! / Rewards: / 20 / Continue |
| 6:26.00 | 6:28.80 | home | 1340 5 Full / LEVEL / 18 / Play / Home |
| 6:53.50 | 6:54.00 | win_panel | Level 18 / Perfect! / Rewards: / 20 / Continue |
| 6:54.00 | 6:56.15 | home | 1344 5 Full / + / LEVEL / 19 / Hard Level / Play |
| 8:13.57 | 8:14.01 | win_panel | Hard Level / 1:52 / Level 19 / Perfect! / Rewards: / 60 |
| 8:14.01 | 8:15.01 | win_panel | Hard Level / 1:52 / Level 19 / Perfect! / Rewards: / 60 |
| 8:15.00 | 8:18.70 | home | 5 Full / + 1420 / LEVEL / 20 / Play / Home |
| 8:42.14 | 8:42.51 | other | 2:42 00 / 3 |
| 8:42.51 | 8:43.01 | win_panel | 2:42 / Level 20 / Perfect! / Rewards: / 20 / Continue |
| 8:43.00 | 8:45.51 | home | 1424 5 Full / LEVEL / 21 / Play / Home |
| 8:45.50 | 8:46.00 | dark | 0035 / ailat |
| 8:46.00 | 8:48.80 | unlock | Pipe! / Unlocked! / 3 / Pass arrows through the / PIPE to break it! |
| 9:11.50 | 9:12.50 | win_panel | 2:44 / Level 21 / Perfect! / Rewards: / 20 / Continue |
| 9:12.51 | 9:14.07 | home | 1456 5 Full / LEVEL / 22 / Play / Home |
| 9:52.25 | 9:52.51 | win_panel | 2:28 / Level 22 / Perfect! / Rewards: / 20 / Continue |
| 9:52.50 | 9:53.50 | win_panel | 2:28 / Level 22 / Perfect! / Rewards: / 20 / Continue |
| 9:53.50 | 9:55.51 | home | 5 Full / + 1460 / +20 / 23 / Play / Home |
| 10:46.50 | 10:48.01 | win_panel | 2:177 / Level 23 / Perfect! / Rewards: / 20 / Continue |
| 10:48.01 | 10:51.50 | home | 1500 5 Full / LEVEL / 24 / Play / Home |
| 11:48.00 | 11:49.00 | win_panel | Level 24 / Perfect! / Rewards: / 20 / Continue |
| 11:49.01 | 11:50.90 | home | 1500 5 Full / 520 / LEVEL / 25 / Hard Level / Play |
| 11:51.00 | 11:50.90 | home | 1520 5 Full / + / LEVEL / 25 / Hard Level / Play |
| 13:16.54 | 13:17.01 | win_panel | Hard Level / 1:40 / Level 25 / Perfect! / Rewards: / 60 |
| 13:17.00 | 13:18.00 | win_panel | Mard Level / Level 25 / Perfect! / Rewards: / 60 / Continue |
| 13:18.00 | 13:19.73 | home | 1532 5 Full / + / LEVEL / 26 / Play / Home |
| 13:55.51 | 13:56.50 | win_panel | Level 26 / Perfect! / Rewards: / 20 / Continue |
| 13:56.50 | 13:58.41 | home | 1596 5 Full / LEVEL / 27 / Play / Home |
| 13:58.51 | 13:58.41 | home | 1600 5 Full / LEVEL / 27 / Play / Home |
| 14:58.20 | 14:58.50 | other | 2:06 |
| 14:58.50 | 14:59.50 | win_panel | 2:06 / Level 27 / Perfect! / Rewards: / 20 / Continue |
| 14:59.51 | 15:01.27 | home | 1608 5 Full / LEVEL / 28 / Play / Home |
| 16:15.51 | 16:16.50 | win_panel | 1:51 / Level 28 / Perfect! / Rewards: / 20 / Continue |
| 16:16.50 | 16:18.41 | home | 1628 5 Full / + / LEVEL / 29 / Super Hard / Play |
| 16:18.51 | 16:18.41 | home | 1640 5 Full / LEVEL / 29 / Super Hard / Play / Home |
| 19:07.50 | 19:08.51 | win_panel | uper Hars / 20 / Level 29 / Perfect! / Rewards: / 100 |
| 19:08.51 | 19:11.64 | home | 1740 5 Full / LEVEL / 30 / Play / Home |
| 19:37.01 | 19:38.00 | win_panel | 2:410 / Level 30 / Perfect! / Rewards: / 20 / Continue |
| 19:38.00 | 19:41.00 | home | 1760 5 Full / LEVEL / 31 / Play / Home |
| 19:41.00 | 19:41.50 | dark | CACAO |
| 19:41.51 | 19:43.01 | unlock | Elevator! / Unlocked! / Clear all arrows on the / ELEVATOR to activate it! |
| 19:43.00 | 19:43.20 | unlock | 010 / Elevator! / Unlocked! / Clear all arrows on the / ELEVATOR to activate it! |
| 20:12.00 | 20:13.01 | win_panel | 2:56 / Level 31 / Perfect! / Rewards: / 20 / Continue |
| 20:13.01 | 20:15.00 | home | 1780 5 Full / LEVEL / 32 / Play / Home |
| 20:55.24 | 20:55.51 | other | 2:26 / Well Donc! |
| 20:55.51 | 20:56.01 | win_panel | Level 32 / Perfect! / Rewards: / 20 / Continue |
| 20:56.00 | 20:58.43 | home | 1784 5 Full / LEVEL / 33 / Play / Home |
| 22:03.00 | 22:04.00 | win_panel | 2:02 / Level 33 / Perfect! / Rewards: / 20 / Continue |
| 22:04.00 | 22:06.54 | home | 1820 5 Full / LEVEL / 34 / Play / Home |
| 22:48.10 | 22:48.50 | other | 2:27 |
| 22:48.50 | 22:49.51 | win_panel | 2:27 / Level 34 / Perfect! / Rewards: / 20 / Continue |
| 22:49.51 | 22:53.01 | home | 1840 5 Full / LEVEL / 35 / Hard Level / Play / Home |
| 22:53.01 | 22:53.51 | home | 1840 5 Full / Bạn có thích Maze / Out! không? / Chạm vào một ngôi sao để / xếp hạng trên App Store. / Để sau |
| 22:53.50 | 22:54.24 | home | 1840 5 Full / LEVEL / 35 / Hard Level / Play / Home |
| 25:00.71 | 25:01.01 | other | Hard Level / 1:03 |
| 25:01.01 | 25:02.01 | win_panel | Hard Level / 1:03 / Level 35 / Perfect! / Rewards: / 60 |
| 25:02.00 | 25:03.88 | home | 1864 5 Full / + / LEVEL / 36 / Play / Home |
| 25:43.51 | 25:44.50 | win_panel | 2:28 / Level 36 / Perfect! / Rewards: / 20 / Continue |
| 25:44.50 | 25:46.35 | home | 1904 5 Full / LEVEL / 37 / Play / Home |
| 27:04.01 | 27:05.01 | win_panel | 1:49 / Level 37 / Perfect! / Rewards: / 20 / Continue |
| 27:05.00 | 27:06.77 | home | 1920 5 Full / +20 / 38 / Play / Home |
| 27:55.14 | 27:55.51 | other | 2:20 |
| 27:55.50 | 27:56.00 | win_panel | Level 38 / Perfect! / Rewards: / 20 / Continue |
| 27:56.00 | 28:03.01 | home | 1960 5 Full / + / LEVEL / 39 / Super Hard / Play |
| 28:03.01 | 28:03.48 | phone_ui | Maze Out! Chế độ trò chơi > / [phone system UI / notification: personal text omitted] |

## Board extraction check (vextract level + replay, every level)

Start frame -> level JSON (`research/video-frames/work/extract/V?-L0NN.json`, overlay `...-overlay.png`). IoU = ink IoU of our re-render vs the frame's stroke mask (raw / with 1-px tolerance). Replay: every exit and bump of the video checked against the model (consistent = exit on a FREE arrow or bump on a BLOCKED one, incl. exits whose touch was not detected); inconsistent = the model contradicts the video. hidden = elevator second-layer arrows read later in the level.

| video | level | arrows | hidden | grid | pitch pt | IoU | IoU tol1 | anomalies | obstacles | taps | consistent | inconsistent | miss | left |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 1 | 3 | 0 | 3x4 | 28.55 | 0.735 | 0.868 | 0 |  | 4 | 3 | 0 | 0 | 0 |
| V1 | 2 | 6 | 0 | 6x6 | 27.98 | 0.813 | 0.966 | 0 |  | 6 | 6 | 0 | 0 | 0 |
| V1 | 3 | 8 | 0 | 10x9 | 28.02 | 0.857 | 0.980 | 0 |  | 6 | 8 | 0 | 0 | 0 |
| V1 | 4 | 8 | 0 | 9x14 | 28.05 | 0.854 | 0.982 | 0 |  | 5 | 8 | 0 | 1 | 0 |
| V1 | 5 | 17 | 0 | 12x14 | 28.04 | 0.852 | 0.976 | 0 |  | 15 | 17 | 0 | 0 | 0 |
| V1 | 6 | 29 | 0 | 27x22 | 13.56 | 0.731 | 0.987 | 0 |  | 27 | 29 | 0 | 4 | 0 |
| V1 | 7 | 18 | 0 | 10x15 | 28.01 | 0.839 | 0.969 | 0 | tape_pink | 13 | 15 | 0 | 1 | 0 |
| V1 | 8 | 19 | 0 | 12x17 | 28.07 | 0.840 | 0.971 | 0 | tape_pink | 15 | 17 | 0 | 0 | 0 |
| V1 | 9 | 27 | 0 | 14x19 | 24.55 | 0.803 | 0.975 | 0 |  | 27 | 27 | 0 | 1 | 0 |
| V1 | 10 | 47 | 0 | 20x22 | 17.86 | 0.802 | 0.982 | 0 | tape_pink | 35 | 38 | 0 | 4 | 0 |
| V1 | 11 | 14 | 0 | 10x20 | 28.01 | 0.853 | 0.976 | 0 | curtain | 16 | 14 | 0 | 1 | 0 |
| V1 | 12 | 24 | 0 | 15x21 | 23.11 | 0.818 | 0.973 | 0 | curtain | 23 | 24 | 0 | 2 | 0 |
| V1 | 13 | 33 | 0 | 14x18 | 24.52 | 0.836 | 0.977 | 0 | curtain, tape_pink | 26 | 31 | 0 | 2 | 0 |
| V1 | 14 | 15 | 0 | 13x16 | 26.17 | 0.849 | 0.979 | 0 |  | 15 | 15 | 0 | 0 | 0 |
| V1 | 15 | 48 | 0 | 20x25 | 17.85 | 0.791 | 0.981 | 0 | curtain | 44 | 48 | 0 | 1 | 0 |
| V1 | 16 | 24 | 0 | 13x15 | 26.19 | 0.837 | 0.966 | 0 |  | 21 | 24 | 0 | 0 | 0 |
| V1 | 17 | 54 | 0 | 19x24 | 18.70 | 0.805 | 0.967 | 0 | tape_pink | 46 | 50 | 0 | 4 | 0 |
| V1 | 18 | 22 | 0 | 14x17 | 24.57 | 0.878 | 0.987 | 0 |  | 21 | 22 | 0 | 1 | 0 |
| V1 | 19 | 62 | 0 | 20x31 | 17.85 | 0.820 | 0.981 | 0 | curtain | 58 | 62 | 0 | 5 | 0 |
| V1 | 20 | 20 | 0 | 14x20 | 24.55 | 0.822 | 0.978 | 0 |  | 19 | 20 | 0 | 1 | 0 |
| V2 | 11 | 14 | 0 | 10x20 | 27.95 | 0.786 | 0.946 | 0 | box | 20 | 14 | 0 | 5 | 0 |
| V2 | 12 | 24 | 0 | 15x21 | 23.10 | 0.819 | 0.980 | 0 | box | 23 | 24 | 0 | 1 | 0 |
| V2 | 13 | 33 | 0 | 14x18 | 24.50 | 0.802 | 0.972 | 0 | box, tape_pink | 32 | 29 | 0 | 3 | 0 |
| V2 | 14 | 15 | 0 | 13x16 | 26.17 | 0.791 | 0.968 | 0 |  | 15 | 15 | 0 | 0 | 0 |
| V2 | 15 | 48 | 0 | 20x25 | 17.85 | 0.791 | 0.981 | 0 | box | 47 | 48 | 0 | 2 | 0 |
| V2 | 16 | 24 | 0 | 13x15 | 26.19 | 0.807 | 0.960 | 0 |  | 24 | 24 | 0 | 0 | 0 |
| V2 | 17 | 54 | 0 | 19x24 | 18.69 | 0.812 | 0.977 | 0 | tape_pink | 46 | 50 | 0 | 3 | 0 |
| V2 | 18 | 22 | 0 | 14x17 | 24.57 | 0.814 | 0.983 | 0 |  | 20 | 22 | 0 | 1 | 0 |
| V2 | 19 | 62 | 0 | 20x31 | 17.84 | 0.828 | 0.984 | 0 | box | 61 | 62 | 0 | 2 | 0 |
| V2 | 20 | 20 | 0 | 14x20 | 24.52 | 0.786 | 0.973 | 0 |  | 20 | 20 | 0 | 0 | 0 |
| V2 | 21 | 20 | 0 | 12x18 | 28.03 | 0.791 | 0.968 | 0 | pipe | 24 | 20 | 0 | 4 | 0 |
| V2 | 22 | 29 | 0 | 14x23 | 24.56 | 0.845 | 0.972 | 0 | pipe | 29 | 29 | 0 | 0 | 0 |
| V2 | 23 | 41 | 0 | 16x22 | 21.79 | 0.817 | 0.966 | 0 | pipe, tape_pink | 37 | 37 | 0 | 1 | 0 |
| V2 | 24 | 37 | 0 | 17x27 | 20.67 | 0.813 | 0.972 | 0 | tape_pink | 28 | 31 | 0 | 0 | 0 |
| V2 | 25 | 61 | 0 | 19x30 | 18.69 | 0.814 | 0.975 | 0 | box, pipe | 60 | 61 | 0 | 5 | 0 |
| V2 | 26 | 26 | 0 | 15x19 | 23.07 | 0.848 | 0.982 | 0 |  | 26 | 26 | 0 | 0 | 0 |
| V2 | 27 | 40 | 0 | 16x26 | 21.82 | 0.804 | 0.964 | 0 | box | 41 | 40 | 0 | 1 | 0 |
| V2 | 28 | 51 | 0 | 19x24 | 18.70 | 0.820 | 0.984 | 0 | box, tape_pink | 42 | 43 | 0 | 3 | 0 |
| V2 | 29 | 67 | 0 | 20x32 | 17.84 | 0.810 | 0.981 | 1 | pipe | 67 | 67 | 0 | 1 | 0 |
| V2 | 30 | 25 | 0 | 16x16 | 21.83 | 0.819 | 0.969 | 0 |  | 25 | 25 | 0 | 0 | 0 |
| V2 | 31 | 35 | 7 | 16x17 | 21.80 | 0.811 | 0.978 | 0 | elevator | 31 | 35 | 0 | 3 | 0 |
| V2 | 32 | 40 | 11 | 17x21 | 20.66 | 0.808 | 0.975 | 0 | elevator | 41 | 42 | 0 | 2 | 0 |
| V2 | 33 | 53 | 17 | 17x23 | 20.65 | 0.799 | 0.970 | 0 | box, elevator | 47 | 53 | 0 | 1 | 0 |
| V2 | 34 | 40 | 0 | 18x23 | 19.63 | 0.842 | 0.984 | 0 | tape_pink | 30 | 36 | 0 | 0 | 0 |
| V2 | 35 | 96 | 39 | 20x32 | 17.84 | 0.800 | 0.980 | 0 | elevator, pipe | 89 | 96 | 0 | 4 | 0 |
| V2 | 36 | 36 | 0 | 20x23 | 17.85 | 0.789 | 0.980 | 0 |  | 36 | 36 | 0 | 3 | 0 |
| V2 | 37 | 55 | 0 | 20x33 | 17.85 | 0.803 | 0.980 | 0 | box | 54 | 55 | 0 | 1 | 0 |
| V2 | 38 | 34 | 0 | 16x20 | 21.82 | 0.804 | 0.970 | 0 | pipe | 33 | 34 | 0 | 1 | 0 |

## Same boards (vmatch: identical arrows / max count, best integer shift)

| a | b | score | identical | arrows |
|---|---|---|---|---|
| V1-L011 | V2-L011 | 1.000 | 14 | [14, 14] |
| V1-L012 | V2-L012 | 1.000 | 24 | [24, 24] |
| V1-L012 | phone-L051 | 1.000 | 24 | [24, 24] |
| V1-L013 | V2-L013 | 1.000 | 33 | [33, 33] |
| V1-L014 | V2-L014 | 1.000 | 15 | [15, 15] |
| V1-L014 | phone-L052 | 1.000 | 15 | [15, 15] |
| V1-L015 | V2-L015 | 1.000 | 48 | [48, 48] |
| V1-L016 | V2-L016 | 1.000 | 24 | [24, 24] |
| V1-L017 | V2-L017 | 1.000 | 54 | [54, 54] |
| V1-L018 | V2-L018 | 1.000 | 22 | [22, 22] |
| V1-L019 | V2-L019 | 1.000 | 62 | [62, 62] |
| V1-L020 | V2-L020 | 1.000 | 20 | [20, 20] |
| V2-L012 | phone-L051 | 1.000 | 24 | [24, 24] |
| V2-L014 | phone-L052 | 1.000 | 15 | [15, 15] |
| V2-L021 | phone-L035 | 1.000 | 20 | [20, 20] |
| V2-L026 | phone-L045 | 1.000 | 26 | [26, 26] |

## Findings the tools established (evidence in the tables above and in `video-frames/work/extract/*-replay.json`)

- **Scale.** Both videos are a 393-pt-wide phone: V2 L21 reads pitch 28.03 pt, the phone's identical L35 28.09 pt (-0.2 %). The video
  board sits 1.7 pt higher (origin y 198.8 vs 200.6 pt): a small layout difference between the builds.
- **Timer.** Every level of both videos shows 3:00 on its clean start frame, Hard and Super Hard included (the phone's v552 L34 Hard
  used 3:30); the clock starts at the first tap (the timer track shows the first tick ~1 s after it). Each "Levels 1-4" stage restarts
  at 3:00 (stages cleared at 2:59, 2:58, 2:56, 2:56). Time left at clear per level: column "left at clear".
- **Rewards on the win panel:** 20 normal, 60 Hard (V1 L19; V2 L19, L25, L35), 100 Super Hard (V2 L29), 80 for "Levels 1-4".
  Tags: V1 L19 Hard; V2 L19 Hard, L25 Hard, L29 Super Hard (cleared with 0:20 left), L35 Hard; V2's last home screen offers L39
  Super Hard.
- **Unlock popups (the only obstacle tutorials; no hand):** V1 "Linked Arrows! Unlocked! LINKED ARROWS move together!" before L7,
  "Curtain! Unlocked! Clear required amount of arrows to open the CURTAIN!" before L11. V2 (other build) "Box! Unlocked! Clear required
  amount of arrows to break the BOX!" before L11, "Pipe! Unlocked! Pass arrows through the PIPE to break it!" before L21, "Elevator!
  Unlocked! Clear all arrows on the ELEVATOR to activate it!" before L31. The board is already built (dimmed) under the popup.
- **Hand tutorial:** only V1 L1 stage 1: "Tap to move!" and a pointing hand over the middle (up) arrow of three vertical arrows; the
  hand appears ~0.1 s after the board is built (clean start frame at 0.72 s is hand-free). Grey discs next to the hand from 1.64 s are
  flagged `near_hand` (the hand's drop shadow looks like a touch); the arrow leaves on the touch at 3.52 s.
- **Counters (replay-verified, every level):** a curtain (V1) or box (V2) breaks on the exit that makes the number of arrows removed
  since the level start equal to its counter; every member of a Linked bundle counts. A pipe breaks after `counter` passes (V2 L23 both
  pipes 3, L38 3). A curtain/box blocks rays until it breaks.
- **Elevator (V2 L31+):** the platform's arrows are normal arrows; when the last one leaves, a hidden second layer is live AT ONCE (V2 L32:
  a tap 0.6 s after that exit bumped into it, 0.3 s before the platform visibly dropped) and is drawn ~0.4-0.9 s later where the platform
  was. Hidden layers read: L31 7, L32 11, L33 9 + 8, L35 39 arrows.
- **Mistakes:** only V2 L32 has any: two taps on blocked arrows, each costing a heart (3 -> 2 -> 1), both BLOCKED in our model. In V2 a
  bumped arrow is redrawn BLACK until it leaves. V1 has no heart loss at all.
- **Edits in the footage:** V1 L17 is CUT at 6:00.7 (timer 2:41 -> 2:28 across one frame) and the board is re-fitted smaller after the
  cut (pitch 28.2 -> 26.7 px); the replay re-registers the grid there. V2 shows iOS notification banners (Vietnamese) over the HUD and
  an AssistiveTouch-like grey circle top right; V2 opens with a meta tour (shop, leaderboard "Reach level 50 to compete in Weekly
  Contest!", settings, profile/username) before L11 and shows the iOS rating prompt on the home screen after L34.
- **V1 vs V2 (L11-L20, the overlap):** all 10 boards are IDENTICAL (every arrow, same grid); only the obstacle skin differs: V1's purple
  "Curtain" crates are V2's cyan "Box" blocks, same cells, same counters (L11 8/13, L12 8/16/23, L13 4/28, L15 26/41, L19 13/20/25).
- **Video build vs the phone (v552, research/levels L32-L61):** V1/V2 L12 = phone L51, V1/V2 L14 = phone L52, V2 L21 = phone L35,
  V2 L26 = phone L45 (identical arrows; the phone also shows boxes on L51 and the pipe on L35; phone L45 runs 2:30, the video's L26
  3:00). Nothing else matches (best other score 0.09): V2 L32-L38 are NOT the phone's L32-L38 (V2 L32 vs phone L32: 1 identical arrow
  of 53/40, 20x20 tapes vs 17x21 elevator). So v552 REORDERED levels (video L21 -> 35, L26 -> 45, L12 -> 51, L14 -> 52) and inserted
  others; L1-L31 content from the videos is real game content, but its v552 position is not the video's number.

