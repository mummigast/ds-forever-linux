# Changes in DS Forever Linux Streaming Edition

Newest first. Based on DS Forever 1.0.36 (upstream add-on set 407; this edition's set 413). What differs from DS Forever in general: [FORK.md](FORK.md).

## 2026-11-19 (late): add-on set 413

- **Box under the dot:** the game's tooltip for the enemy under the controller's aim dot, at any range the game draws it, with
  Questie's quest lines. A switch: *Settings > Top screen > Tooltips > Box under the dot* (on by default; `/wcbox` in the game's
  chat does the same). WoW Forever only reports enemies under the dot, so friendly units and NPCs get no box.
- **Loot window on the top screen** now stays WoW's own window in fights too (DS Forever moved fight loot to the bottom screen).
- **Friendly plates On** shows every friendly unit's plate, also in fights (it showed only the selected target's).
- The game's own tooltip for objects and corpses under the dot is on. WoW Forever refuses the other soft-target settings
  (`SoftTargetEnemy`, its range, `SoftTargetInteract`: "read only or secure", even from a macro), so they are left alone. The
  add-on writes two account macros, *DSF Soft On* / *DSF Soft Off*, with the tooltip settings the game does accept.

## 2026-11-19: DS Forever 1.0.36, add-on set 412

- **Merged DS Forever 1.0.36**: the power button in the pause menu, stream tap calibration (taps aimed at each row's measured centre),
  switches sent in one batch, no click loops, Polestar following the stream, the PC's WoW window matching the Thor.
- Not in this edition: Desktop's quiet clicks and its add-on and window management need DS Forever Desktop (the Linux helper does not
  offer them, so the app keeps keyboard shortcuts first and clicks on the stream otherwise). The browser-login helper
  (`wow-session-bridge.exe`) is left out with the local game's runtime.

## 2026-11-18: DS Forever 1.0.35, add-on set 411

- **Merged DS Forever 1.0.35.** It carries this edition's HUD memory and switch backoff (PRs #532 and #533) in upstream's own
  form, so the edition's copies are gone: the add-on keeps the HUD switches, layout and cast bar per character, and the app sends
  one "restore" tap at connect (a WoW started on the PC alone keeps its normal UI); each switch counts its own answers and a
  stuck one gets one retry every 30 s.
- **Pairing over a VPN:** the PC address button is replaced by upstream's **Other network** code. `dsf-bridge code` (and the
  helper's log) now show it under the 6-digit code; type both on the Thor.
- The helper closes WoW and Battle.net after 10 minutes with no Thor connected (swiping the app away left the game running).
  A WoW started on the PC alone is never closed. Setting: `DSF_IDLE_CLOSE_MIN` (0 = never).
- The **XP bar switch** works now (Thor, 2026-11-19).
- **Relog restores the HUD in one go while streaming:** no top-screen taps under a loading screen (they were lost), and the one
  restore tap waits for the keyboard shortcuts to be ready (Thor-tested 2026-11-19).
- Also from 1.0.35: crash fixes, stream settings on the bottom screen, settings sync safety, low-memory work; indoor maps build
  while the local game is closed (streaming: while the app is open and not streaming, as before).

## 2026-11-18: DS Forever 1.0.34, add-on set 410

- **Merged DS Forever 1.0.34**: Edit layout (move and save the top-screen pieces), the Buffs / XP bar / Damage meter / Cooldown
  Manager switches, Smart pet (replaces this edition's pet-follow memory), map and stream fixes from upstream.
- Edit layout and those switches work while streaming: their hidden row is pressed by keyboard shortcuts too.
- Shortcut columns no longer use punctuation keys, which never arrived on non-US keyboard layouts (friendly nameplates and the
  layout editor were affected).
- The pairing screen fits the Thor's top screen (Stream quality, PC address and Back beside the keypad).
- No "Save your Battle.net login" button: the PC signs in.
- **Stream settings** in the start screen's Menu too, before a stream (it opens the quality page and connects when it closes).
- A switch the game never answers retries every 30 s straight away once it is set aside (it got three quick taps first).
- Three of this edition's fixes were offered to DS Forever as pull requests (#532 HUD memory, #533 switch backoff, #534 PC address).
- Known: the XP bar switch does nothing yet; the Damage meter is untested.

## 2026-11-18: add-on set 407

**Fixed**
- **Buttons with a WoW window open** (vendor, quest giver): quests (pick, accept, reward), *Sell junk*, *Repair*, buy and sell now
  work every time. The app presses the add-ons' hidden buttons with keyboard shortcuts (Ctrl+Shift + two keys) instead of clicks,
  so WoW's controller cursor no longer sends them to the middle of the screen.
- **Top-screen switches** (player frame, target frame, nameplates, minimap, chat, tracker...) go as shortcuts too: no more stray
  clicks in the middle of the screen. Ctrl+Shift+PageDown is bound in the game, so those rows use other keys.
- The start screen keeps its Stream button, and the app never downloads a game client onto the device.

**New**
- **Instant relog:** the add-ons remember the HUD switches, the layout (minimap, chat, tracker) and the cast bar per character and
  put them back at login, instead of the app re-sending about 20 taps. The Start button's mode and B's pet follow are no longer
  re-told after every login either.
- **Normal game UI** (Settings > Top screen > Game windows): minimap, chat, tracker and cast bar back in one tap, for
  `/` commands or playing on the PC. Typing `/wcui reset` in the game's chat brings back the whole UI, including the frames.

**Known problems and untested parts:** see [FORK.md](FORK.md) (*Known problems*, *Untested*). In short: chat commands typed in
the app's chat aren't sent (use the game's chat with *Normal game UI* on), and the pet and party frame switches are untested.

Updating: rebuild the app (`./linux-build.sh`) and pull the repository on the PC; the helper installs the add-ons (set 407) when the
Thor connects, then `/reload` in game.
