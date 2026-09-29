---
name: disk-fills-fast-clean-archives
description: "The factory fills the disk every few apps; Xcode Archives + simulator devices are the two big consumers, and ENOSPC surfaces as a linker error"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 67834757-7bc9-4e4f-a907-36f39cf8e3e8
  modified: 2026-09-28T22:20:48.470Z
---

The machine ran out of disk mid-build on 2026-09-02 and the failure read as:

    Write() failed, errno=28
    Linker command failed with exit code 1
    ** TEST FAILED **

`errno=28` is ENOSPC. **Nothing in the message says "disk".** Check `df -h /` FIRST whenever a
link, codesign or archive step fails for no obvious reason — see [[disk-full-lies]].

**Where the space actually goes** (measured, worst first):
1. `~/Library/Developer/CoreSimulator/Devices` — 29 GB across 13 devices. `xcrun simctl erase`
   each device you are not using; it keeps the device and drops its data.
2. `~/Library/Developer/Xcode/Archives` — 7.3 GB. One folder per DAY. Archives of apps already
   uploaded are dead weight: the IPA and its dSYMs went to App Store Connect with the build.
   Keep today's, delete the rest.
3. `apps/<slug>/build` — ~750 MB per app that has been archived. Delete for any submitted app.
4. `~/Library/Developer/Xcode/DerivedData` — regenerable, always safe to clear.
5. `~/Library/Logs/CoreSimulator/CoreSimulator.log` — ONE log file that reached 1.0 GB after two days
   of heavy simulator use (2026-09-27, mazeout). Truncate it in place (`: > file`, keep a tail first);
   safe while the service has it open. Check it first in any disk crunch: nobody thinks of it.
   Swap in `/System/Volumes/VM` also eats the boot disk (up to 16 GB with 2 sims + builds) and only
   shrinks when pressure drops, so free space swings by several GB on its own.

6. `$TMPDIR/instruments*.ktrace` (`/private/var/folders/<..>/T`) — xctrace/Instruments leaves a 50-270 MB
   temp trace behind per perf recording; 10 of them = 1.6 GB after three days of FrameProbe runs (2026-09-28,
   mazeout). Delete the ones `lsof` shows closed and older than an hour.
7. Each simulator's `data/Library/Caches/com.apple.containermanagerd/Dead/` keeps the old app bundle of every
   reinstall (~65-300 MB each) until containermanagerd gets round to it; clear entries older than 10 min.

8. **A runaway process hides from `ps` RSS.** 2026-09-28 22:44 a Python render (fur strands, draft) reached an
   8.6 GB memory FOOTPRINT with 5.9 GB of it compressed, so its RSS looked small, my RSS-based memguard never
   fired, swap hit 16.6 GB and the disk fell to 191 MB. Find hogs with `top -l 1 -o mem -stats pid,command,mem,cmprs`,
   never `ps rss`; kill it and swap drops at once (disk back to 6.7 GB in a minute). A memory guard must read top's MEM.
   Key the guard's rule on the EXECUTABLE (`ps -o comm=`), never on words in the command line: 09-29 13:48 an xctest whose
   arguments contained 'python' was killed under the python limit mid-verification.

9. **Other apps' caches — only with the owner's OK, and only the harmless part.** 2026-09-29 the owner said
   "if its not gonna harm the other apps, you can clear them, make sure nothing important from them are lost".
   Safe (re-downloaded on demand, no user data): `~/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation`
   (staged app update), `kimi-desktop-updater/*.zip`, Playwright browser builds NO project references (check each
   project's `node_modules/playwright-core/browsers.json` revisions against `ms-playwright/`). NOT safe: the Playwright
   builds a project still pins, and `com.microsoft.VSCode.ShipIt` while a `ShipIt` process is running (it is waiting to
   install that update when VS Code quits). Check `lsof` and running processes before deleting any of it.

That sequence recovered 23 GB. Do it BEFORE a submit run rather than after a mysterious failure:
seven archive+upload cycles need roughly 6 GB of headroom.
