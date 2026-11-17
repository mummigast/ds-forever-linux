# Safety, rules and licences

What the Linux helper (and the Streaming Edition app with it) does and doesn't do, so you can decide whether to use it.
Reviewed 2026-11-17.
This is a plain-language summary, not legal advice.

## Blizzard: EULA, Terms of Use and the UI Add-On Development Policy

| Rule | How the helper keeps it |
|---|---|
| No bots or automation ("software that allows the automated control of a Game") | The helper never sends key presses, mouse input or game commands. All play input goes Thor → Moonlight → Sunshine as one press = one action, like any controller. |
| No hacks, no reading or changing game memory, no intercepting game traffic | The helper reads only **WoW's own log file** (`Logs/General.log`), where DS Forever's add-ons write their data. It checks the game *process* and counts its *network connections* (not their contents) to tell the Thor whether WoW is at login, character select or in the world. Nothing is injected, hooked or decrypted. |
| No input broadcasting / multiboxing | One Thor drives one game on one PC. |
| Add-ons: free, readable code, no ads, no donation requests | The add-ons it installs are DS Forever's own, unchanged and readable (GPL-3.0). The helper is free and its source is right here. |
| Account security | The helper never asks for, reads, stores or types your Battle.net login. You sign in on the PC yourself. Use Blizzard's Authenticator. |
| Starting the game | Uses Battle.net's own launch option (`--exec="launch WoWF"`), as DS Forever Desktop does. |
| The app's clicks | As in DS Forever, the Thor app's bottom-screen buttons are mouse clicks (through Moonlight) on the add-ons' own hidden buttons: one press, one click. When it connects, the app also clicks the add-ons' layout switches a few times to set up its HUD (frames shown or hidden); that is interface setup, never a game action. |

**Risk, honestly:** this is an unofficial tool that Blizzard has neither approved nor forbidden. It follows the lines
Blizzard enforces (no automation, no memory access, no injection, one action per press), but Blizzard can change its
rules at any time, and using third-party software is at your own risk. The helper changes nothing in the game except
DS Forever's own add-on folders.

## What it changes on your PC

- `~/.config/dsf-bridge/`: settings (`env`), paired Thors, the pairing code, its TLS certificate (private files, mode 600).
- `~/.cache/dsf-bridge/`: a temporary backup during add-on updates (and the upstream download, only if the helper runs
  outside this repository).
- `~/.local/bin/dsf-bridge`, `~/.config/systemd/user/dsf-bridge.service`.
- In the game: only `Interface/AddOns/WowCompanion*` (DS Forever's add-ons). Never `WTF/`, Config.wtf, macros, key
  bindings or settings.
- No root, no system files, no firewall changes (it tells you the command when one is needed).
- Remove it all: `./uninstall.sh --purge`, then delete `Interface/AddOns/WowCompanion*` if you want the add-ons gone too.

## Network

- Listens on **TCP 48210** on your home network and announces itself by mDNS. **Do not forward this port** from your router.
- Pairing: a 6-digit code shown on the PC; the code never crosses the network (HMAC proof). Five wrong codes pause pairing
  for 5 minutes.
- After pairing the Thor uses an encrypted connection (wss, self-signed certificate pinned at pairing). Web pages
  from other sites (an `Origin` header other than localhost) are refused.
- If you give it your Sunshine login (optional), it is used only for Sunshine's local API on 127.0.0.1 to enter the
  Moonlight PIN, and is kept in `~/.config/dsf-bridge/env` (mode 600).
- Outgoing: none in normal use (the add-ons come from this repository). Only a helper run outside the repository fetches
  them from upstream DS Forever's latest release on GitHub (at most every 3 hours, verified with its SHA256SUMS).

## Licences

| Part | Licence | Notes |
|---|---|---|
| This helper | GPL-3.0-or-later | `LICENSE` |
| DS Forever's bridge protocol (`docs/STREAM_BRIDGE_PROTOCOL.md`) | GPL-3.0 | copied unchanged, credited |
| DS Forever's add-ons (installed into the game) | GPL-3.0 | DS Forever's own, from this repository, installed unchanged, notices kept |
| [websockets](https://github.com/python-websockets/websockets) | BSD-3-Clause | installed by pip, not bundled |
| The Streaming Edition app on the Thor | GPL-3.0 (DS Forever's), dependencies their own | you build it from this repository; **this project hands out no APKs** (see ../FORK.md, *Sharing*) |

Trademarks: World of Warcraft and Battle.net are trademarks of Blizzard Entertainment. Unofficial; not affiliated with
or endorsed by Blizzard Entertainment, DS Forever, WoW Forever, GameNative, Valve or LizardByte (Sunshine).
