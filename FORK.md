# DS Forever Linux Edition

**Based on [DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702.** Almost everything here is their work
(and, before them, the WoW Forever for Android, GameNative, Pluvia and Winlator contributors). This fork only adds what
is needed to stream WoW Forever from a **Linux PC** (Steam/Proton + Sunshine) to an AYN Thor, including over a VPN such
as WireGuard.

**A personal project.** It is made to work on one setup: a Linux PC with Steam/Proton and Sunshine, and an AYN Thor,
at home or over WireGuard. Anyone is free to try it, build it and change it under the GPL-3.0, but it comes with no
support, no promises and no warranty (GPL-3.0 sections 15-16). For everything that is not Linux-specific, use and
support the official DS Forever. Please don't report problems with this fork to DS Forever's author.

Unofficial: not affiliated with or endorsed by DS Forever's author, Blizzard Entertainment, WoW Forever or GameNative.
World of Warcraft and Battle.net are trademarks of Blizzard Entertainment; you need your own game and account.

## Licence

- The whole app stays **GPL-3.0** (LICENSE), the same as DS Forever. The Linux helper in `linux-helper/` is GPL-3.0 too.
- All original copyright, licence and credit notices are kept unchanged: LICENSE, THIRD_PARTY_NOTICES,
  RELEASE_NOTICES.md, SOURCE_PROVENANCE.md, licenses/, and every notice inside the source files.
- Each change to an upstream file is marked with a `Linux Edition` comment and its date (GPL-3.0 section 5a); the
  table below lists them, and the git history shows every change against upstream.
- Dependencies keep their own terms (CascLib MIT, Recast zlib, Moonlight GPL-3.0, OpenSSL Apache-2.0, Opus BSD,
  and the rest in RELEASE_NOTICES.md).

## What is different from DS Forever

| Change | Where |
|---|---|
| Own app ID `app.dsforever.companion.linux` and name "DS Forever Linux Edition": installs beside the official app | `app/build.gradle.kts`, `res/values*/strings.xml` |
| Ghost clicks fixed when streaming from Linux: a 1 px relative nudge before each click so WoW hands its controller cursor to the mouse, then position and click | `dsforever/.../stream/StreamKeys.kt` |
| Quiet-pad wait +90 ms while streaming (controller and mouse travel separately) | `companion/.../TapQuiet.kt`, `TapSink.kt` |
| **PC address…** on the pairing screen: pair by IP where mDNS can't reach (VPN) | `dsforever/.../stream/StreamTop.kt`, `StreamScreens.kt` |
| Update check and problem reports point at this fork, not upstream | `app/build.gradle.kts`, `companion/.../ProblemReport.kt` |
| Reload UI works while streaming: F12 (the add-on's ReloadUI key) is let through; other F-keys stay blocked | `dsforever/.../stream/StreamKeys.kt` |
| Unanswered game-switch taps back off to every 30 s after 3 tries (was every 2 s forever: ghost clicks with WoW's settings open) | `companion/.../GameUi.kt` |
| `DSFTAP` log line per tap with its caller (diagnostics) | `TapBridge.kt`, `StreamKeys.kt` |
| The Linux PC helper (replaces DS Forever Desktop) | `linux-helper/` |
| Fork banner at the top of the README (the original text follows unchanged) | `README.md` |
| One-command Linux build | `linux-build.sh` |

Changed upstream files carry a `Linux Edition` comment at each change (GPL-3.0 section 5a).

## Thor setup

- Window focus: **Top screen**. With auto-lock, touching the bottom screen moves focus there and controller presses
  (L/R in the bottom menus, game buttons) stop arriving.
- Pairing over a VPN: Streaming → **PC address…** → the PC's LAN IP.

## Build

```
./linux-build.sh --test
```
Fetches and checksum-verifies the runtime components, builds the two native libraries (CascLib, Recast) and the
Moonlight prebuilts if missing, then the APK. Without the native libraries the app says "this build has no file reader".

## Following upstream

```
git fetch upstream
git merge upstream/main          # conflicts are usually only in the files in the table above
./linux-build.sh --test
```
Upstream's version number is kept (the fork tracks its releases); the app's update check is pointed at this repo.

## Sharing

- **Source:** free to share, fork and change under GPL-3.0. Keep the notices, mark your own changes.
- **APKs:** please build your own with `./linux-build.sh`. This repo does not hand out APKs: besides the GPL code,
  the app contains runtime parts whose redistribution rights DS Forever itself lists as unresolved
  (RELEASE_NOTICES.md: the Proton/Wine build, Turnip drivers, `redirect.tzst`, `libkgslshim.so`, a Samsung SDK, some
  fonts/art). If you do pass a build on, you must also offer its complete corresponding source (GPL-3.0 section 6).
