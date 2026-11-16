# dsf-linux-helper: DS Forever on Linux

**Unofficial.** Stream WoW Forever from a Linux PC to your AYN Thor with [DS Forever](https://github.com/Jreese702/DS-Forever).

> **Status: early.** Works end to end against a simulated Thor; real-device testing is ongoing. Please
> [open an issue](https://github.com/mummigast/dsf-linux-helper/issues) with the output of `dsf-bridge doctor` if
> something doesn't work.

Play **World of Warcraft: Forever** on your **Linux PC** and stream it to an **AYN Thor**: the game on the top screen,
DS Forever's touch companion (map, bags, quests, chat, party) on the bottom screen.

**What you run:** the official **DS Forever app** on the Thor, plus this small **helper** on the PC. The helper replaces
DS Forever Desktop, which only exists for Windows.

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
- PC and Thor on the **same home network**.
- **DS Forever** installed on the Thor: the APK from [its releases](https://github.com/Jreese702/DS-Forever/releases/latest).

## Install (about a minute)

```sh
git clone https://github.com/mummigast/dsf-linux-helper.git
cd dsf-linux-helper
./install.sh
```

Run it in a terminal on the PC's desktop (not over SSH). The installer sets everything up as your user (no root), starts the helper as a background service, checks your setup
and shows a **pairing code**. Anything marked **FIX** comes with the exact command to run.

## Connect the Thor (once)

1. On the Thor open **DS Forever → Streaming**. It finds your PC by itself.
2. Type the **6-digit code**. To see it again: `dsf-bridge code`.
3. The Thor then pairs its Moonlight with Sunshine using a **4-digit PIN**:
   open Sunshine's web page on the PC (`https://localhost:47990`), go to **PIN**, and type the PIN that
   `dsf-bridge code` shows (or the one on the Thor's screen).
   *Skip this step every time:* put your Sunshine login in `~/.config/dsf-bridge/env` (`SUNSHINE_USER=` / `SUNSHINE_PASS=`).
4. Done. From now on: open DS Forever on the Thor and pick Streaming.

## What happens when you play

- If WoW isn't running, the helper starts Battle.net and launches WoW Forever for you. If Battle.net wants you to sign in,
  do that once on the PC (your login is never seen or stored by the helper).
- The first time the Thor connects, the helper installs DS Forever's add-ons into the game and keeps them up to date. They
  only go in `Interface/AddOns/WowCompanion*`; nothing else in the game is changed. Type `/reload` in the game after an install.
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
| "The PC isn't answering" / "Desktop isn't running" | `dsf-bridge doctor`: helper running? firewall open for 48210/tcp and mDNS? same network? |
| "The stream works, but Desktop's bridge isn't answering" | the helper is down or blocked: `systemctl --user restart dsf-bridge`, check the firewall |
| "Pair again" | `dsf-bridge code`, enter it on the Thor; Sunshine's PIN step again if asked |
| Stuck on "Starting WoW on your PC" | Battle.net may want a sign-in or an update on the PC; or start WoW yourself once |
| Bottom screen empty | add-ons missing: `dsf-bridge addons`, then `/reload` in the game |
| Taps land in the wrong place | stream the monitor WoW is on, with WoW full screen |

## Other launchers (Lutris, Heroic, Bottles, plain Wine)

The helper finds WoW Forever in those prefixes too. It can only *start* WoW by itself under Steam/Proton; otherwise put a
start command in `~/.config/dsf-bridge/env`, for example `DSF_START_CMD=lutris lutris:rungame/battlenet`, or start WoW
yourself before you connect.

## Settings (`~/.config/dsf-bridge/env`)

See `env.example`: Sunshine login (automatic PIN), the PC's name on the Thor, an unusual WoW folder, a custom start command.

## Not done yet (compared with DS Forever Desktop)

- Spotting Battle.net's sign-in window (the Thor just waits on "Starting WoW" until you sign in on the PC).
- Closing WoW when the stream ends.

## Privacy and rules (details: [SAFETY.md](SAFETY.md))

The helper reads only WoW's own log file (where DS Forever's add-ons write their data) and the game's process and
connections, to tell the Thor where the game is. It never reads, stores or types your Battle.net login, never sends
key presses, and never writes anything in the game except DS Forever's own add-on folders. It follows the same rules as
DS Forever: one button press is one game action, nothing is automated.

## Licence

GPL-3.0-or-later (`LICENSE`), as DS Forever. Dependency: [websockets](https://github.com/python-websockets/websockets)
(BSD-3-Clause), installed by `install.sh`. Unofficial: not affiliated with Blizzard Entertainment or the DS Forever
project. World of Warcraft and Battle.net are trademarks of Blizzard Entertainment.

## For developers

Protocol: `docs/STREAM_BRIDGE_PROTOCOL.md` (copied from DS Forever, GPL-3.0). Files: `dsf_bridge.py` (server, pairing, CLI), `wow_linux.py`
(finding/starting WoW, screen detection), `addons.py` (add-on installs). Tests: `.venv/bin/python -m unittest discover -s tests`.

## Credits

[DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702 and contributors (GPL-3.0): the Thor app, its add-ons
and the bridge protocol this helper implements. This project is a Linux stand-in for its Windows-only DS Forever Desktop
and is not affiliated with it.
