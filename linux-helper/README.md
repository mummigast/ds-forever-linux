# The Linux helper (DS Forever Linux Streaming Edition)

**Unofficial.** The PC half of the [DS Forever Linux Streaming Edition](../FORK.md): stream WoW Forever from a Linux PC
to your AYN Thor, with DS Forever's companion on the bottom screen. Based on [DS Forever](https://github.com/Jreese702/DS-Forever).

> **Status: a personal project.** Used and tested on one setup (KDE Plasma on Wayland, Steam/Proton, Sunshine Flatpak, an
> AYN Thor at home and over WireGuard). Others are welcome to try it; issues and pull requests are welcome on
> [GitHub](https://github.com/mummigast/ds-forever-linux/issues), answered when there is time. `dsf-bridge doctor` checks a setup.

Play **World of Warcraft: Forever** on your **Linux PC** and stream it to an **AYN Thor**: the game on the top screen,
DS Forever's touch companion (map, bags, quests, chat, party) on the bottom screen.

**What you run:** the **DS Forever Linux Streaming** app on the Thor (the APK from a [release](https://github.com/mummigast/ds-forever-linux/releases), or built from this repository), plus this small
**helper** on the PC. The helper replaces DS Forever Desktop, which only exists for Windows. Streaming from Windows, or
WoW installed on the Thor itself: use the official DS Forever instead.

```
 Linux PC                                          AYN Thor
 ┌──────────────────────────┐   video, sound,     ┌───────────────────────────┐
 │ WoW Forever (Steam/Proton)│◄─ controller ─────►│ top: the game (Moonlight) │
 │ Sunshine                  │   (Moonlight)      │                           │
 │ dsf-bridge (this helper)  │◄── game data ─────►│ bottom: DS Forever        │
 └──────────────────────────┘   (port 48210)      └───────────────────────────┘
```

## You need

- **WoW Forever via Battle.net, added to Steam as a non-Steam game, running with Proton.** Start it once and log in
  (other launchers work too, see *Other launchers*).
- **Sunshine** ([Flatpak](https://flathub.org/apps/dev.lizardbyte.app.Sunshine) or your distro's package), set up and running.
- **Python 3.10+** with venv, and **avahi** with its tools. Most desktops have them; otherwise install
  `python3-venv avahi-utils` (Debian/Ubuntu) or `avahi-tools` (Fedora).
- PC and Thor on the **same home network** for the first pairing (later also over a VPN such as WireGuard; or pair over the
  VPN with **Other network** and the second code `dsf-bridge code` shows).
- The **DS Forever Linux Streaming** app on the Thor: the APK from the same [release](https://github.com/mummigast/ds-forever-linux/releases)
  as this helper, or build it with `./linux-build.sh` in the repository's root (see [FORK.md](../FORK.md)).
- On the Thor: window focus on **Top screen** (AYN's settings). With auto-lock, controller presses can go to the bottom
  screen and stop reaching the game.

## Install (about a minute)

From the latest [release](https://github.com/mummigast/ds-forever-linux/releases): download `dsf-linux-helper-<version>.tar.gz`
(it carries the DS Forever add-ons that match that release's APK) and `SHA256SUMS`, then:

```sh
sha256sum -c --ignore-missing SHA256SUMS
tar xzf dsf-linux-helper-<version>.tar.gz
cd dsf-linux-helper-<version>
./install.sh
```

Or from the repository (what you build the app from): `git clone https://github.com/mummigast/ds-forever-linux.git`, then
`cd ds-forever-linux/linux-helper && ./install.sh`. Keep the folder where it is: the service runs from it.

Run it in a terminal on the PC's desktop (not over SSH). The installer sets everything up as your user (no root), starts the helper as a background service, checks your setup
and shows a **pairing code**. Anything marked **FIX** comes with the exact command to run.

## Connect the Thor (once)

0. **First start asks to install the game on the Thor: say yes (Install directly).** The app builds the bottom screen's maps
   and icons from the game's own files, so it needs a WoW Forever folder on the Thor even for streaming (about 250 MB to
   start; it fetches more pieces as it builds). The indoor maps build while the app is open and you are not streaming.
1. On the Thor open the app and press **Streaming**. It finds your PC by itself on the same network; over a VPN, tap
   **Other network** and type the second code `dsf-bridge code` shows under the 6-digit one.
2. Type the **6-digit code**. To see it again: `dsf-bridge code`.
3. The Thor then pairs its Moonlight with Sunshine using a **4-digit PIN**:
   open Sunshine's web page on the PC (`https://localhost:47990`), go to **PIN**, and type the PIN that
   `dsf-bridge code` shows (or the one on the Thor's screen).
   *Skip this step every time:* put your Sunshine login in `~/.config/dsf-bridge/env` (`SUNSHINE_USER=` / `SUNSHINE_PASS=`).
4. Done. From now on: open the app on the Thor and press Streaming.

## What happens when you play

- If WoW isn't running, the helper starts Battle.net and launches WoW Forever for you. If Battle.net wants you to sign in,
  do that once on the PC (your login is never seen or stored by the helper).
- The first time the Thor connects, the helper installs DS Forever's add-ons into the game and keeps them up to date. They
  only go in `Interface/AddOns/WowCompanion*`; nothing else in the game is changed. Type `/reload` in the game after an install.
- The add-ons you install in the Thor app (Settings > Add-ons: Polestar, Spoken, Manners) are installed into the PC's game too,
  from their authors' own downloads (checked), before the helper starts WoW (never while it runs). A folder you put there
  yourself is left alone; one you remove on the Thor is moved to `Interface/AddOns-backup-dsforever`.
- The power button in the Thor app's pause menu closes WoW on the PC (it saves first). With no Thor connected for 10 minutes
  the helper closes WoW and Battle.net (`DSF_IDLE_CLOSE_MIN`, 0 = never); a WoW you started on the PC yourself is never closed.
- On KDE Plasma the helper brings the WoW window to the front for the stream. Other desktops: keep WoW in front yourself.

## Commands

| | |
|---|---|
| `dsf-bridge doctor` | check the setup, with fixes |
| `dsf-bridge code` | show the pairing code |
| `dsf-bridge addons [--force]` | install/update DS Forever's add-ons now |
| `dsf-bridge forget` | forget all paired Thors |
| `journalctl --user -u dsf-bridge -f` | watch the helper's log |
| `systemctl --user restart dsf-bridge` | restart it |
| `./uninstall.sh [--purge]` | remove it (`--purge` also forgets pairings) |

## Troubleshooting

| The Thor says | Try |
|---|---|
| "The PC isn't answering" / "The Linux helper isn't running" | `dsf-bridge doctor`: helper running? firewall open for 48210/tcp and mDNS? same network? |
| "The stream works, but the helper's bridge isn't answering" | the helper is down or blocked: `systemctl --user restart dsf-bridge`, check the firewall |
| "Pair again" | `dsf-bridge code`, enter it on the Thor; Sunshine's PIN step again if asked |
| Stuck on "Starting WoW on your PC" | Battle.net may want a sign-in or an update on the PC; or start WoW yourself once |
| Bottom screen empty | add-ons missing: `dsf-bridge addons`, then `/reload` in the game |
| Taps land in the wrong place | stream the monitor WoW is on, with WoW full screen |
| Bottom-screen buttons react but do nothing in the game | stream the monitor WoW is on, full screen, at the PC's native resolution; `/reload` in the game |
| No PC found over a VPN | **Other network** on the pairing screen, then the second code `dsf-bridge code` shows |
| Controller does nothing after reinstalling the app | restart Sunshine (it keeps the old controller slot): `systemctl --user restart app-dev.lizardbyte.app.Sunshine.service` for the Flatpak's user unit |
| A/B and X/Y swapped in the game | the Thor sends its Nintendo-printed buttons by label: switch the Thor's own controller layout (Xbox / swap A-B) in AYN's settings, and set DS Forever's ABXY to Xbox |

## Other launchers (Lutris, Heroic, Bottles, plain Wine)

The helper finds WoW Forever in those prefixes too. It can only *start* WoW by itself under Steam/Proton; otherwise put a
start command in `~/.config/dsf-bridge/env`, for example `DSF_START_CMD=lutris lutris:rungame/battlenet`, or start WoW
yourself before you connect.

## Settings (`~/.config/dsf-bridge/env`)

See `env.example`: Sunshine login (automatic PIN), the PC's name on the Thor, an unusual WoW folder, a custom start command.

## Not done yet (compared with DS Forever Desktop)

- Spotting Battle.net's sign-in window (the Thor just waits on "Starting WoW" until you sign in on the PC).
- The Thor's *imported* add-ons and automatic QuestieDB updates (they need DS Forever Desktop's file transfer).
- Desktop's quiet clicks and settings / Polestar sync.

## Privacy and rules (details: [SAFETY.md](SAFETY.md))

The helper reads only WoW's own log file (where DS Forever's add-ons write their data) and the game's process and
connections, to tell the Thor where the game is. It never reads, stores or types your Battle.net login, never sends
key presses, and never writes anything in the game except the add-on folders it put there (DS Forever's own and the ones you
picked on the Thor) and their on/off lines in AddOns.txt. It follows the same rules as
DS Forever: one button press is one game action, nothing is automated.

## Licence

GPL-3.0-or-later (`LICENSE`), as DS Forever. Dependency: [websockets](https://github.com/python-websockets/websockets)
(BSD-3-Clause), installed by `install.sh`. Unofficial: not affiliated with Blizzard Entertainment or the DS Forever
project. World of Warcraft and Battle.net are trademarks of Blizzard Entertainment.

## For developers

Protocol: `docs/STREAM_BRIDGE_PROTOCOL.md` (copied from DS Forever, GPL-3.0). Files: `dsf_bridge.py` (server, pairing, CLI), `wow_linux.py`
(finding/starting WoW, screen detection), `addons.py` (DS Forever's add-on set), `pc_addons.py` (the add-ons picked on the Thor).
Tests: `.venv/bin/python -m unittest discover -s tests`. A release's tarball comes from `./linux-build.sh --release` (see ../FORK.md).

## Credits

[DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702 and contributors (GPL-3.0): the Thor app, its add-ons
and the bridge protocol this helper implements. This helper is a Linux stand-in for its Windows-only DS Forever Desktop
and is not affiliated with it. The DS Forever add-ons it installs are from this repository or the release tarball's `addon-set/`
(the same version as the app beside them).
