# Safety, rules and licences

What the Linux helper (and the Streaming Edition app with it) does and doesn't do, so you can decide whether to use it.
Reviewed 2026-11-17, updated 2026-11-20 (add-ons you pick on the Thor, closing WoW, keyboard shortcuts, release APKs).
This is a plain-language summary, not legal advice.

## Blizzard: EULA, Terms of Use and the UI Add-On Development Policy

| Rule | How the helper keeps it |
|---|---|
| No bots or automation ("software that allows the automated control of a Game") | The helper never sends key presses, mouse input or game commands. All play input goes Thor → Moonlight → Sunshine as one press = one action, like any controller. |
| No hacks, no reading or changing game memory, no intercepting game traffic | The helper reads only **WoW's own log file** (`Logs/General.log`), where DS Forever's add-ons write their data. It checks the game *process* and counts its *network connections* (not their contents) to tell the Thor whether WoW is at login, character select or in the world. Nothing is injected, hooked or decrypted. |
| No input broadcasting / multiboxing | One Thor drives one game on one PC. |
| Add-ons: free, readable code, no ads, no donation requests | The add-ons it installs are DS Forever's own, unchanged and readable (GPL-3.0), plus the ones **you** pick in the Thor app's Settings > Add-ons (Polestar, Spoken, Manners), each unchanged from its own author's pinned release. The helper is free and its source is right here. |
| Account security | The helper never asks for, reads, stores or types your Battle.net login. You sign in on the PC yourself. Use Blizzard's Authenticator. |
| Starting and closing the game | Starts it with Battle.net's own launch option (`--exec="launch WoWF"`), as DS Forever Desktop does. Closes it when you press the power button in the Thor app's pause menu (asks its window to close, as its X does, so it saves first), or after 10 minutes with no Thor connected. |
| The app's presses | The Thor app's bottom-screen buttons press the add-ons' own hidden buttons through Moonlight: as keyboard shortcuts (CTRL-SHIFT chords bound only to those buttons) once a handshake with the add-on is in, as mouse clicks before that. One press, one action. The handshake is asked for only when you press a button, never on a timer; after login the HUD restore waits for your first press. A few interface syncs (HUD layout, the Start menu mode, opening a room) press the add-ons' own buttons too; never a game action (no movement, casting or targeting). |

**Risk, honestly:** this is an unofficial tool that Blizzard has neither approved nor forbidden. It follows the lines
Blizzard enforces (no automation, no memory access, no injection, one action per press), but Blizzard can change its
rules at any time, and using third-party software is at your own risk. The helper changes nothing in the game except
the add-on folders it put there itself (and their on/off lines in AddOns.txt).

## What it changes on your PC

- `~/.config/dsf-bridge/`: settings (`env`), paired Thors, the pairing code, its TLS certificate (private files, mode 600).
- `~/.cache/dsf-bridge/`: a temporary backup during add-on updates, the pinned downloads of the add-ons you picked
  (`pc-addons/`), and the upstream download (only if the helper runs without its own add-on set).
- `~/.local/bin/dsf-bridge`, `~/.config/systemd/user/dsf-bridge.service`.
- In the game: `Interface/AddOns/WowCompanion*` (DS Forever's add-ons), the add-ons you picked on the Thor (only folders it put
  in itself; a folder of yours with the same name is never touched; replaced or removed copies go to
  `Interface/AddOns-backup-dsforever`, nothing is deleted), and those folders' on/off lines in `WTF/Account/*/AddOns.txt`.
  Never Config.wtf, macros, key bindings or other settings.
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
- Outgoing: DS Forever's add-ons come with the helper (this repository, or the release tarball's `addon-set/`). The add-ons
  you pick on the Thor are downloaded from their own source only (Polestar and Spoken: their GitHub releases; Manners:
  CurseForge's file server), each checked against its pinned size and SHA-256. A helper with no add-on set of its own fetches
  DS Forever's from upstream's latest release (at most every 3 hours, verified with its SHA256SUMS).

## Licences

| Part | Licence | Notes |
|---|---|---|
| This helper | GPL-3.0-or-later | `LICENSE` |
| DS Forever's bridge protocol (`docs/STREAM_BRIDGE_PROTOCOL.md`) | GPL-3.0 | copied unchanged, credited |
| DS Forever's add-ons (installed into the game) | GPL-3.0 | DS Forever's own, from this repository, installed unchanged, notices kept |
| Add-ons you pick on the Thor | their own (Polestar GPL-3.0, Spoken MIT, Manners MIT) | downloaded from their authors' pinned releases, installed unchanged, licence files kept |
| [websockets](https://github.com/python-websockets/websockets) | BSD-3-Clause | installed by pip, not bundled |
| The Streaming Edition app on the Thor | GPL-3.0 (DS Forever's), dependencies their own | a signed APK + its source in every release, or build it yourself (see ../FORK.md, *Releases* and *Sharing*) |

Trademarks: World of Warcraft and Battle.net are trademarks of Blizzard Entertainment. Unofficial; not affiliated with
or endorsed by Blizzard Entertainment, DS Forever, WoW Forever, GameNative, Valve or LizardByte (Sunshine).
