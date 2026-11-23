# DS Forever — Linux Streaming Edition

**Stream WoW Forever from your Linux PC to the AYN Thor.**

**[Download the latest release](https://github.com/mummigast/ds-forever-linux/releases/latest)** ·
[What's new](CHANGES.md) · [Report a problem](https://github.com/mummigast/ds-forever-linux/issues)

<!-- screenshot: both screens, the auction house remote -->

## What this edition adds

- **A Linux PC helper.** It starts WoW through Steam and Proton, keeps your add-ons in sync, and closes the game once the
  Thor has been away for a while.
- **A different auction house.** The game's own AH window, driven from buttons and a tappable result list on the Thor.
  Search, filter, buy and sell without D-pad hunting.
- **Real typing.** Letters go straight into the game's search, price and level boxes as you type.
- **Shortcuts instead of clicks.** Quests, vendors, bags, the cast bar and menus answer to keyboard shortcuts, so nothing
  misses, and the game sees far fewer automated inputs.
- **Smoother fights.** Less work per frame inside the game, so fewer hitches when a fight starts.
- **Streaming only.** The game runs on the PC, never on the Thor, so the app is smaller and installs next to the official one.

## Latest: 1.0.38.4

The auction house remote, live typing, buying fixed, and keys never land in Battle.net or another window.
[All changes](CHANGES.md)

## What you need

| | |
|---|---|
| **Handheld** | AYN Thor |
| **PC** | Linux with Steam (tested: Bazzite / KDE Plasma on Wayland) |
| **Game** | WoW Forever through Battle.net, added to Steam as a non-Steam game and run with Proton |
| **Streaming** | [Sunshine](https://github.com/LizardByte/Sunshine) on the PC, set up and running |
| **Network** | Same home network for the first pairing; after that home or a VPN such as WireGuard |

## Quick start

1. **On the PC**, download `dsf-linux-helper-<version>.tar.gz` from the latest release, unpack it and run `./install.sh`
   in a terminal on the desktop. It checks your setup and shows a pairing code.
2. **On the Thor**, install the APK from the same release. The first start offers to install the game files: say yes,
   the maps and icons are built from them.
3. **Pair:** press **Streaming**, type the 6-digit code, then enter the 4-digit PIN in Sunshine's web page
   (`https://localhost:47990` → PIN).
4. **Play:** from now on, open the app and press **Streaming**. WoW starts on the PC by itself.

More detail, commands and troubleshooting: [the helper's guide](linux-helper/README.md).

## Known issues

- Chat commands typed in the app's chat (`/reload`, ...) aren't sent: use the game's own chat for those.
- A few actions still go as clicks: the bags button, moving items between bags, picking a spell from the spellbook.
- *In fights: Top screen* can put the moved buttons in the wrong layout.
- The full list: [CHANGES.md](CHANGES.md).

## FAQ

**Do I need Windows?** No. The PC side is Linux only; for Windows, use the official DS Forever and its Desktop app.

**Can I play the game installed on the Thor?** Not with this edition. It only streams; the official DS Forever plays locally.

**Is it safe for my account?** No one can promise that for a fan-made tool. The app keeps automated input to a minimum: one
keyboard shortcut per action you take, only while WoW is the window in front. It never plays for you.

**Does it replace the official app?** No. It installs next to it, with its own settings.

## Help and feedback

[Open an issue](https://github.com/mummigast/ds-forever-linux/issues): what you did, what you expected and what happened.
The helper's log helps: `journalctl --user -u dsf-bridge`.

Want to try new things first? Betas are published as pre-releases: [how betas work](BETA.md).

## Credits

An unofficial fork of [DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702, who wrote almost all of the app.
Not affiliated with DS Forever's author, Blizzard Entertainment, WoW Forever or GameNative; you need your own game and account.
GPL-3.0, like DS Forever. What changed, file by file, and how to build it yourself: [FORK.md](FORK.md) ([build](FORK.md#build)).
