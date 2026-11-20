# DS Forever Linux Streaming Edition

**Based on [DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702.** Almost everything here is their work
(and, before them, the WoW Forever for Android, GameNative, Pluvia and Winlator contributors).

**For streaming from a Linux PC only.** This edition streams WoW Forever from a **Linux PC** (Steam/Proton + Sunshine)
to an AYN Thor, at home or over a VPN such as WireGuard, with the Linux helper in `linux-helper/` in place of DS Forever
Desktop. It is not meant for playing WoW installed on the Thor itself: **for that, and for streaming from Windows, use
the official [DS Forever](https://github.com/Jreese702/DS-Forever)** - it does those better.

**A personal project.** Made to work on one setup. Anyone is free to try it, build it and change it under the GPL-3.0.
Issues and pull requests about this edition are welcome on [its own repository](https://github.com/mummigast/ds-forever-linux/issues)
and answered when there is time; there are no promises and no warranty (GPL-3.0 sections 15-16). Please don't report problems with
this fork to DS Forever's author; a fix that belongs in DS Forever itself is best offered upstream.

Unofficial: not affiliated with or endorsed by DS Forever's author, Blizzard Entertainment, WoW Forever or GameNative.
World of Warcraft and Battle.net are trademarks of Blizzard Entertainment; you need your own game and account.

## Licence

- The whole app stays **GPL-3.0** (LICENSE), the same as DS Forever. The Linux helper in `linux-helper/` is GPL-3.0 too.
- All original copyright, licence and credit notices are kept unchanged: LICENSE, THIRD_PARTY_NOTICES,
  RELEASE_NOTICES.md, SOURCE_PROVENANCE.md, licenses/, and every notice inside the source files.
- Each changed upstream file carries a `Linux Edition` or `Linux Streaming Edition` comment with its date (GPL-3.0 section 5a); the
  table below lists them, and the git history shows every change against upstream.
- Dependencies keep their own terms (CascLib MIT, Recast zlib, Moonlight GPL-3.0, OpenSSL Apache-2.0, Opus BSD,
  and the rest in RELEASE_NOTICES.md).

## What is different from DS Forever

| Change | Where |
|---|---|
| Own app ID `app.dsforever.companion.linux` and name "DS Forever Linux Streaming": installs beside the official app | `app/build.gradle.kts`, `res/values*/strings.xml` |
| **Streaming only**: the start screen has one Stream card (no Local card, so no Battle.net sign-in and no local game launch); the start list drops the Battle.net and Thor add-on rows | `companion/.../ChooserPanel.kt` (`STREAM_ONLY`), `SetupFlow.kt`, `ModeBridge.kt` |
| **The local game runtime is not packaged** (see *What is left out*): 270 MB -> about 130 MB | `app/build.gradle.kts` (`-PlocalRuntime=true` restores) |
| Indoor maps build while the app is open and not streaming, pause during a stream; the start list shows their progress ("120 / 340 (35%)") | `companion/.../PlayGate.kt` (`streamOnlyBake`), `IndoorSchedulerStep.kt` |
| Texts name the Linux helper instead of DS Forever Desktop; a stuck streaming service says "restart Sunshine" | `dsforever/.../stream/*` |
| The video decoder is not forced to its top clock (heat); low latency and realtime priority stay | `dsforever/.../stream/StreamMedia.kt` |
| Clicks land in the game world when streaming from Linux (not yet while a WoW window is open, see *Known problems*): a 4 px relative nudge (out, pause, back) before each click so WoW sees real mouse motion and hands its controller cursor to the mouse; a +1/-1 nudge sums to zero within one frame and does nothing | `dsforever/.../stream/StreamKeys.kt` |
| Quiet-pad wait +90 ms while streaming (controller and mouse travel separately) | `companion/.../TapQuiet.kt`, `TapSink.kt` |
| Update check and problem reports point at this fork, not upstream | `app/build.gradle.kts`, `companion/.../ProblemReport.kt` |
| Reload UI works while streaming: F12 (the add-on's ReloadUI key) is let through; other F-keys stay blocked | `dsforever/.../stream/StreamKeys.kt` |
| `DSFTAP` log line per tap with its caller (diagnostics) | `TapBridge.kt`, `StreamKeys.kt` |
| Click positions +1 screen px: on Linux the pointer landed ~1 px up-left (measured in WoW), on the edge of the tap pad's ~2 px rows, so the row above took the press | `dsforever/.../stream/StreamKeys.kt` |
| The character is taken from a replayed document until a live one comes (a Thor joining a running game never learned it, so no per-character switch was sent) | `companion/.../CompanionHost.kt`, `GameUi.kt` |
| The Linux PC helper (replaces DS Forever Desktop); it installs the add-ons from this repository, so they match the app built from the same checkout | `linux-helper/` |
| The helper shows DS Forever's **Other network** code (the PC's address) under the pairing code, for a Thor on a VPN | `linux-helper/paircode.py`, `dsf_bridge.py` |
| The helper closes WoW and Battle.net after 10 min with no Thor connected (only a WoW a Thor used; `DSF_IDLE_CLOSE_MIN`, 0 = never) | `linux-helper/dsf_bridge.py`, `wow_linux.py` |
| **Keyboard shortcuts instead of clicks** (the key channel, off upstream, is on): CTRL-SHIFT + row key + column key presses the add-ons' hidden buttons without WoW's cursor, so quests, vendor (Sell junk, Repair), and the top-screen switches work with a WoW window open | `TapBridge.kt` (`KEYS_ON`), `TapKeys.kt`, `WowCompanion/TapPad.lua` |
| Live-game key fixes: CTRL-SHIFT-PAGEDOWN is bound in WoW, so the HUD switch row takes the test row's RIGHT; with no row key left, a row key pressed **twice** picks a second row (RIGHT RIGHT + column = the layout row: minimap, chat, tracker) | `TapPad.lua` (`KEY_HOT`, `KEY_PAGE2`), `TapKeys.kt` |
| **Fewer taps after login**: the Start button's mode and B's pet follow are derived or kept by the add-ons instead of told by the app | `WowCompanionQuests/Quests.lua`, `WowCompanionSpells` |
| **Normal game UI** switch (Settings > Top screen > Game windows): minimap, chat, tracker and cast bar back in one tap; `/wcui reset` typed in the game's chat brings back the whole UI | `GameUi.kt`, `GameUiSection.kt`, `Hub.lua` |
| No top-screen taps under a loading screen (`LoadGate`, from the add-on's loading-screen reports); while streaming the login's one restore tap waits for the key handshake (at most 15 s) | `companion/.../LoadGate.kt`, `GameUi.kt`, `TapBridge.kt` |
| The app never downloads a game client onto the device (no automatic update for the local game) | `StartMode.kt` (`STREAM_ONLY`), `WoWForeverScreen.kt` |
| **Box under the dot** (2026-11-19): the game's tooltip for the unit under the reticle (`mouseover` > `softenemy` > `softfriend`), never over a tooltip someone else shows; a switch in the Tooltips tile's band (`dotbox on/off` cells on `iact`), `/wcbox` | `WowCompanionHub/Hub.lua` (hub72-73), `WowCompanionInteract/Interact.lua` (i167), `HomeSettings.kt` (`DotBoxSwitch`), `GameUiSection.kt`, `GameUiTiles.kt`, `CompanionHost.kt`, `SettingsPad.kt` |
| Loot window "top screen" holds in fights too (upstream's i144 sends fight loot to the bottom screen) | `WowCompanionInteract/Interact.lua` (i166, `LOOT.top`) |
| Friendly plates On = every friendly plate, through fights (upstream: only the target's, alpha 0 for the rest) | `WowCompanion/Trail.lua` (ag15) |
| Soft-target object tooltip on; account macros *DSF Soft On/Off* for the tooltip settings WoW Forever accepts; `/wcsoft` | `WowCompanionHub/Hub.lua` (hub71) |
| While the key handshake is missing (after login, a `/reload` or a stream reconnect), a press asks for it again after 2 s, not 10 s (only the player's own presses ask: no clicks on a timer) | `companion/.../TapBridge.kt` |
| Upstream's Reset knows this edition's saved switches (`dotBoxOff`, `softTgtOff` = settings; `softTgt`, `dotBox` = never) | `companion/.../ResetPlan.kt` |
| Own front page; DS Forever's README follows unchanged in a fold | `README.md` |
| One-command Linux build | `linux-build.sh` |

Changed upstream files carry a `Linux Edition` / `Linux Streaming Edition` comment (GPL-3.0 section 5a). No upstream code is deleted:
the edition's behaviour sits behind switches, and the runtime is left out at packaging time, so upstream merges stay small.

## What is left out

The Streaming Edition's APK does not package what only the local game (WoW running on the Thor) uses. The code that would
use it stays, unused:

- the runtime components: the Proton/Wine build, DXVK, both Turnip drivers (`bundled_components`), box64, PulseAudio,
  `redirect.tzst`, `libredirect-bionic-wx*.so` (proprietary per THIRD_PARTY_NOTICES), the Windows components, LSFG;
- the container's prebuilt libraries: `libkgslshim`, `libpulse*`, `libsndfile`, `libltdl`, `liblsfg-vk-layer`,
  `libgnoverlay`, the DNS shim, `libevshim`, `libhook_impl`, `libmain_hook`, `libpatchelf`, `libvortekrenderer`,
  `libvirglrenderer`, `libpulseaudio`.

The Samsung perfsdk jar RELEASE_NOTICES.md mentions is not in this source snapshot at all.

## Known problems

- **Chat commands typed in the app's chat** (`/reload`, `/wcui ...`) are not sent: that button is a secure click, which keys can't
  press yet. Turn on *Normal game UI* and type them in the game's own chat window. Plain chat works from the app.
- **"Normal game UI" doesn't bring back a hidden player, target or party frame**; `/wcui reset` in the game's chat does.
- Right after connecting, the camera may turn by itself until the right stick is moved (cause not settled; not being worked on).
- **Soft targeting is the controller's only** in WoW Forever (`SoftTargetEnemy`, its range and `SoftTargetInteract` are secure, even
  from a macro): the box under the dot only ever sees enemies (`softenemy`), never friendly units or NPCs.

## Untested

Built and passing the off-device tests, but **not yet tried in the game**. Reports welcome.
- The pet frame and party frame switches; 1.0.34's Damage meter switch.
- The friendly-nameplate and other switches whose column keys are punctuation (`-`, `=`, `[`, `]`): they may not arrive on non-US
  keyboard layouts.
- Layout row by keys (RIGHT RIGHT + column): minimap, chat and tracker toggles (added 2026-11-18).
- B's pet follow kept per character (Hunter / Warlock).
- Bags, spells and other secure rows still go as clicks (no keys yet).

Tested on the Thor (2026-11-19): DS Forever 1.0.36 (relog HUD, keys, power button), loot window on top in fights, every friendly
plate, the box under the dot with quest lines (its Settings switch: not yet).

Tested on the Thor (2026-11-17/18): quests (pick, accept, reward), Sell junk, Repair, buy and sell, player and target frames,
nameplates, Reload UI, 1.0.34's Edit layout (move + Save), Buffs and Cooldown Manager switches, an instant relog with the layout kept, per-character settings, Normal game UI on/off.

## Thor setup

- Window focus: **Top screen**. With auto-lock, touching the bottom screen moves focus there and controller presses
  (L/R in the bottom menus, game buttons) stop arriving.
- Pairing over a VPN: tap **Other network** on the pairing screen and type the second code `dsf-bridge code` shows.

## Build

```
./linux-build.sh --test
```
Builds the two native libraries (CascLib, Recast) and fetches the Moonlight prebuilts if missing, then the APK. Without the
native libraries the app says "this build has no file reader". `DSF_LOCAL_RUNTIME=1` also fetches (checksum-verified) and
packages the local game runtime, as upstream's full app.

## Following upstream

```
git fetch upstream
git merge upstream/main          # conflicts are usually only in the files in the table above
./linux-build.sh --test
```
Upstream's version number is kept (the fork tracks its releases); the app's update check is pointed at this repo.

## Sharing

- **Source:** free to share, fork and change under GPL-3.0. Keep the notices, mark your own changes.
- **APKs:** build your own with `./linux-build.sh`; this repository does not hand out APKs. Leaving out the local runtime
  removes the parts DS Forever's RELEASE_NOTICES.md lists as not cleared for redistribution (Proton/Wine build, Turnip,
  `redirect`, `libkgslshim`, PulseAudio/box64 builds). Still open before anyone hands out a build: the fonts' and some
  artwork's exact provenance (RELEASE_NOTICES.md, "Actual Launcher Inputs"), and the data files the app ships
  (`assets/safepath`, `assets/harvest`), which come from upstream as they are. Anyone passing a build on must also offer
  its complete corresponding source (GPL-3.0 section 6).
