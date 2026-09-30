# Economy display helpers (`economy-ui`)

The coin / duration formats, the catalogue's product titles and the home coin pills' in-flight count, shared by every screen that draws coins or rewards.

ShopFormat (thin-space thousands "1 000", "1h" / "30m" unlimited-lives durations; money is never formatted here, the Shop shows StoreKit's displayPrice), ShopTitles (the product titles as strings keys and their English form) and CoinPillDisplay (what the coin pills show: the banked coins minus what has not landed yet). The Shop, the lives and booster popups, the home top bar and bars, the payout sequence and the event pages all use them. The economy table itself (ShellEconomy: rules.json + social.json decoded once, purchases applied) stays in core: the shell's own event-art and rotation policies read it.

## How the app uses it

```swift
let coins = CoinPillDisplay.shared.shown(ShellScreens.homeState(app))       // the Shop tab's header pill
GameText(verbatim: ShopFormat.amount(g.coins), style: st)                   // a reward amount
```

## Open it in a Debug build

```
-pc.go shop -pc.fakeStore 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show economy-ui
python3 tools/kit.py export economy-ui --out /tmp/economy-ui-kit
```
