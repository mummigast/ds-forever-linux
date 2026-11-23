# DS Forever Linux Streaming Edition

Play **WoW Forever** on an **AYN Thor**, streamed from a **Linux PC** (Steam/Proton + Sunshine), with DS Forever's two-screen
companion on the bottom screen. At home or over a VPN such as WireGuard.

**Streaming only, and getting leaner.** This edition is made for one way of playing: WoW Forever on your PC, streamed to the Thor.
Parts of the app that don't fit streaming are being taken out, and features that don't work reliably over a stream yet are being
reworked, such as a new auction house screen, with fewer automated clicks sent to the game (fewer missed clicks, less input that
isn't yours).

> **An unofficial, personal fork of [DS Forever](https://github.com/Jreese702/DS-Forever) by Jreese702.** Almost all of the app
> is their work (and, before them, the WoW Forever for Android, GameNative, Pluvia and Winlator contributors). This edition adds
> a Linux PC helper and a few streaming fixes on top, and follows upstream's releases.
>
> - **Not the official app.** To play WoW installed on the Thor, or to stream from Windows, use the official
>   [DS Forever](https://github.com/Jreese702/DS-Forever): it does those better.
> - **Issues and pull requests are welcome here**, about this edition: [open an issue](https://github.com/mummigast/ds-forever-linux/issues).
>   It is a hobby project tested on one setup, so answers come when there is time, and there is no warranty. Please don't report
>   this edition's problems to DS Forever's author; changes that belong in DS Forever itself are best sent upstream.
> - **APK + source in every [release](https://github.com/mummigast/ds-forever-linux/releases)**, signed with this edition's own key;
>   or build it yourself (see *Build*).
> - Not affiliated with or endorsed by DS Forever's author, Blizzard Entertainment, WoW Forever or GameNative. World of Warcraft
>   and Battle.net are trademarks of Blizzard Entertainment; you need your own game and account.

## What is different from DS Forever

**Added**
- **A Linux helper instead of DS Forever Desktop** ([linux-helper/](linux-helper/README.md)): pairs with the Thor, starts WoW
  through Steam/Proton, installs the matching add-ons (also the Thor's Polestar / Spoken / Manners), closes the game after
  10 minutes without a Thor, and closes it from the pause menu's power button.
- **Pairing over a VPN** with DS Forever's *Other network* code (`dsf-bridge code`).
- Small extras on the top screen, each with its own switch in *Settings*:
  - **Ranged tooltips**: the game's tooltip for the unit under the controller's aim dot (as far as the nameplates reach), with
    Questie's quest lines.
  - **Loot window on the top screen** stays the game's own, in fights too.
  - **Friendly plates** show for every friendly unit, not only the target.

**Improved**
- **Keyboard shortcuts instead of screen clicks** wherever possible: quests, vendors (buy, sell, repair), bags (in fights too),
  a bag slot picked by touch, the top-screen switches, the room switch, the Controller room and the tap-to-cast bar, typing
  (one key per letter). Streaming, a click lands where WoW
  parks its cursor after controller play, so clicks often missed; shortcuts don't, and fewer automated inputs are sent.
- **Less stutter while streaming:** the add-ons' big updates are built once and spread over frames (a fight's start ~32 + 20 ms
  instead of one ~110 ms frame).
- **Chat item links** no longer stick on "Retrieving item information".
- **The auction house is the game's own window** on the top screen, worked with WoW Forever's own controller navigation; the
  bottom screen is its keyboard (type the search, Done) and shows your auctions and what you bought lately.
- **Settings show only what works when streaming.**

**Removed / left out**
- **No local game:** this edition only streams. No Local card, no Battle.net sign-in on the Thor, and the local runtime (Proton,
  DXVK, drivers, ...) is not packaged: the app is about 130 MB and installs beside the official one
  (`app.dsforever.companion.linux`). The Thor never downloads or updates WoW itself.

The full list, file by file: [FORK.md](FORK.md). What changed lately: [CHANGES.md](CHANGES.md).
Each version is a [release](https://github.com/mummigast/ds-forever-linux/releases) (`linux-v<DS Forever version>.<n>`) with the APK, the
helper with its matching add-ons, `SHA256SUMS`, the source and its notes: watch the repo's releases to hear about new ones.

### Stable and beta

- **Stable** (branch `main`): the release marked **Latest**. The app's update check only ever offers these. Known issues are at
  the top of [CHANGES.md](CHANGES.md).
- **Beta** (branch [`beta`](https://github.com/mummigast/ds-forever-linux/tree/beta)): bigger changes are tried here first and published
  as **pre-releases** (`linux-v<version>-beta.<n>`), each with the same APK, helper and notes. What is new in the beta:
  [CHANGES.md on the beta branch](https://github.com/mummigast/ds-forever-linux/blob/beta/CHANGES.md), and every pre-release's own notes
  on the [releases page](https://github.com/mummigast/ds-forever-linux/releases). When a beta has proven itself it becomes the next
  stable release.
- **Current beta:** none right now; the next one starts from stable 1.0.38.1.
- **Installing a beta:** download its APK and its `dsf-linux-helper-<version>.tar.gz` from the pre-release (both, the add-ons must
  match the app), install the APK over the stable one (same signing key, your settings stay) and run the helper's `./install.sh`.
  To go back, install the latest stable release's APK and helper the same way. The app's update check never offers a beta.

## Quick start

1. On the PC: install the helper from the latest release's `dsf-linux-helper-<version>.tar.gz` (or the repository), see
   [linux-helper/README.md](linux-helper/README.md).
2. Download the APK from the latest [release](https://github.com/mummigast/ds-forever-linux/releases) (or build it, below) and install it
   on the Thor.
3. On the Thor: *Stream*, then type the pairing code the helper shows (on a VPN, tap **Other network** and type the second code).

## Build

```
./linux-build.sh --test
```

Builds the native libraries, runs the tests and makes `app/build/outputs/apk/modern/debug/app-modern-debug.apk`. Details and
options: [FORK.md](FORK.md#build).

## Known problems

- Chat commands typed in the app's chat (`/reload`, ...) aren't sent: turn on *Normal game UI* and use the game's own chat.
- WoW Forever keeps soft targeting for the controller only, and add-ons can't change that: ranged tooltips find friendly
  units and NPCs only by their nameplates (turn on *Friendly plates*).
- Right after connecting, the camera may turn by itself until the right stick is moved.
- More, and what is still untested: [FORK.md](FORK.md#known-problems).

Found another one? [Open an issue](https://github.com/mummigast/ds-forever-linux/issues) with what you did, what you expected and
what happened (the helper's log, `journalctl --user -u dsf-bridge`, helps).

## Licence and credits

GPL-3.0, the same as DS Forever ([LICENSE](LICENSE)). Every original copyright, licence and credit notice is kept
(THIRD_PARTY_NOTICES, RELEASE_NOTICES.md, SOURCE_PROVENANCE.md, licenses/), and every changed upstream file says so in a dated
`Linux Edition` comment. See [FORK.md](FORK.md#licence).

## DS Forever's own README

Kept unchanged below, as upstream wrote it. Parts of it (playing on the Thor, DS Forever Desktop, the updater) are about the
official app, not this edition.

<details>
<summary>DS Forever README (upstream, unchanged)</summary>

# DS Forever

Android launcher and companion for the World of Warcraft: Forever beta. Forked
from [WoW Forever](https://github.com/jaredgei/wow-forever-android) and
[GameNative](https://github.com/utkarshdalal/GameNative); their contributors'
copyright/licence notices are retained.

Unofficial community project, not affiliated with or endorsed by Blizzard,
WoW Forever's maintainers or GameNative. World of Warcraft and Battle.net are
their owners' marks. Supply your own authorised game installation/account.
No Blizzard client files, extracted art, QuestieDB or Polestar are bundled.

## Tested Scope

**AYN Thor only**; other devices are unverified. Android10/API29+, arm64-v8a.
Package `app.dsforever.companion`. Same-package, same-key
DS builds update in place. Do not uninstall or clear data for signing conflicts;
developer builds with another key cannot update an official installation.

The user accepted the predecessor's T3 walk-through. Full-catalogue storage and
map-reader checks are PC evidence, not a completed full-device bake. The native
peak includes the game; large-dungeon device memory/backoff was not captured.
Some layouts remain deferred. Whole-city/floorless/liquid coverage is incomplete.

## Setup And Play

On first start choose **Install directly** (about 250 MB now; the game streams the
rest from Blizzard as you play, up to about 50 GB; needs Wi-Fi and 60 GB free), or
choose an existing folder containing `.build.info` and `Data/`, including hidden files.
Thor testing used `/storage/emulated/0/Documents/WoW Forever`; every game path
comes from the chosen root, not a hard-coded old `/sdcard` folder.

Two-screen setup checks environment readiness and automatically prepares art
from your installed game. Seven required steps gate Play; required failures
offer **Try again**. QuestieDB downloads after the art check. Polestar
(fitzforge/polestar, GPL-3.0-only; Polestar_Nav GPL-3.0-or-later) downloads from
its project's own pinned release, never bundled; its licence and notice files go
in with its folders. Before Play the bottom screen asks once whether to use the
Polestar quest guide; Settings > Add-ons switches it On/Off. Optional interiors
and all-icons background work never gate Play. No extracted PC/server pictures
are used as a fallback.

Configure Login/Update Login manages sign-in; updating login restarts the game
to read it. Refused sign-in has recovery controls. Credentials are excluded from
diagnostic logs. Keyboard opens Android's keyboard on the Thor's top screen.
Authenticator challenges are manual; avoid repeated wrong-password tests.

The companion shows observed NPCs, not database-only ghosts. No suggested spells.
Old DS-created macros are removed silently, preserving user-created macros.
Herbs/ore: use the game's minimap tracking (live minimap dots are gone). Sparkles OFF by default. Indoor legend:
**red main exit, green up, blue down**. Outdoors remains visible while a plan loads.

## Streaming From Your PC

DS Forever can play WoW Forever from your Windows PC instead of on the Thor,
with the companion on the bottom screen. It needs DS Forever Desktop on the PC:

1. Download `DsForeverDesktop-<version>-win-x64.zip` from the same release as
   the APK, unzip it to a folder you keep, and run `DsForeverDesktop.exe`.
2. Pick Streaming on the Thor and enter the code Desktop shows.
3. Connect on your home Wi-Fi. Desktop starts WoW and signs in with the login
   saved on your Thor.

Your saved login stays sealed on the Thor. When a stream starts it goes to the
PC over the paired, encrypted link and is written to WoW's own `login.txt`,
readable by your Windows account only and deleted about 20 seconds after
sign-in starts (5 minutes at most, or as soon as the Thor disconnects). No keys
are typed. Authenticator challenges stay manual.

Desktop updates itself from these releases once no Thor is connected, checked
against `SHA256SUMS`. It is not code-signed, so Windows may warn on first run.
WoW closes itself 5 minutes after the stream ends, unless the PC is in use.

## Updates

The **app updater** uses
[`Jreese702/DS-Forever`](https://github.com/Jreese702/DS-Forever/releases/latest)
and `DS-Forever-<version>.apk`. Offline checks do not block Play. Downloads check
size/any supplied SHA-256; installation checks package, DS certificate and a newer
numeric versionCode. Android owns installer permission/confirmation. Updates are
held while the game runs. Release1.0.0 asset: `DS-Forever-1.0.0.apk` + SHA256SUMS.
The updater is not a working public channel until the public release exists.

The **game updater** separately checks Blizzard's build and updates client/CASC
metadata in the chosen folder. App updates do not replace game data. Game updates
can invalidate generated art/interiors. Neither updater grants beta entitlement.

## Self-Contained Windows Build

Companion and set115 add-on source live in `companion/`. Never reuse/publish the
old private `ds-forever` history; this source snapshot has no inherited Git history.
Install JDK17, Python3.8+, Git for Windows (Bash/curl), CMake>=3.16, Ninja,
Android platform36/build-tools36.1.0/NDK27.2.12479018. Put tools on PATH; set
JAVA_HOME and ANDROID_HOME. Gradle8.12.1 and bootstrap fetch public dependencies.

```powershell
./tools/bootstrap.ps1
./gradlew.bat :app:assembleModernDebug
```

Debug signing is for development, not updating official installs. Signed release:
securely supply all four environment values WC_KEYSTORE, WC_KEYSTORE_PASS,
WC_KEY_ALIAS, WC_KEY_PASS (never put secrets in source), then:

```powershell
python tools/build_release.py --out C:/build-output/DS-Forever-1.0.0
```

The original `tools/fetch_components.sh` is unchanged: all FOUR pinned files,
three from upstream components-v1 and TurnipV32 from its original upstream URL.
`./tools/bootstrap.ps1 -Components C:/verified-files` supports a local folder.
The Windows SHA-256 check-mode shim in tools/bin supplies shasum without editing
the fetch script. Runtime archives stay ignored. Bootstrap fetches pinned
CascLib/Recast, patches a CascLib copy and builds both JNI libraries. Gradle uses
repo-relative `companion/app/src/main`; -PdsAppDir is a developer override.
Release tooling checks frozen inputs, runtime hashes, signing/version, zero-art
including resources, and post-R8 callbacks. Linux/bit-for-bit reproducibility
has not been verified.

## Credits And Licences

WoW Forever and GameNative: launcher, container and X-server foundation. DS:
companion, chosen-root setup/sign-in, controller workflow, local art/interiors
and app updater. Thanks to the RP6 runtime contributors, Wine/Proton, DXVK,
Mesa, CascLib (Ladislav Zezula), Recast (Mikko Mononen), box64, PulseAudio and
the projects in THIRD_PARTY_NOTICES. Application fork: GPL-3.0 (LICENSE).
Dependencies have separate terms: RELEASE_NOTICES.md, licenses/ and APK inventory.
Source/patch/redistribution gaps are explicit, not presumed cleared for publication.

</details>
