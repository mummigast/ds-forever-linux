# Changes in DS Forever Linux Streaming Edition

Newest first. This is the BETA line (branch `beta`, published as pre-releases): its "Beta:" sections are what it has on top of the stable line ([CHANGES.md on main](https://github.com/mummigast/ds-forever-linux/blob/main/CHANGES.md); see "Stable and beta" in the README). Based on DS Forever 1.0.37 (upstream add-on set 413; this edition's set 419). What differs from DS Forever in general: [FORK.md](FORK.md).

## Beta: DS Forever 1.0.38 merged, add-on set 424 (beta.2 + upstream; release candidate for linux-v1.0.38.1)

Upstream DS Forever 1.0.38 (code 1520) on top of beta.2. Built and passing the tests; being played.

- **Everything new in DS Forever 1.0.38** ([its notes](https://github.com/Jreese702/DS-Forever/releases/tag/v1.0.38)): edit Home like a
  phone's home screen, *In fights: Top screen*, the rebuilt Controller room with your own macros and tap-to-cast slots for fights and
  Party mode, Spell rank badges, voice typing language, lighter memory use and its fixes.
- The edition's own behaviour stays: keyboard presses instead of clicks where the game allows, the top screen's restore waits for
  your first press, indoor maps build while the app is open and pause while you stream. The loading-screen wait this edition sent
  upstream (PR #567) comes back in upstream's improved form.

## Beta: linux-v1.0.37.5-beta.2, add-on set 419 (pre-release)

On top of beta.1. Built and passing the tests; the auction house is new and not yet played.

- **The auction house is the game's own window** on the top screen, worked with WoW Forever's own controller navigation; the app's
  auction-house screen is gone. The bottom screen is its keyboard: type the search there and press Done (the words go into the
  game's search box; press the game's Search with the controller), and see your auctions and what you bought lately (read only).
- **Fewer automated inputs:** typing (the auction-house search, the app's chat) is the row's keys once, then one key per letter
  (was four keys per letter, or a click per letter before); the Auras pick and the Talents rows go as keys too.
- **"Box under the dot" is now called "Ranged tooltips"** (*Settings > Top screen > Tooltips*; `/wcbox` still switches it). It takes
  over the game's leftover tooltip of another unit (it used to step aside for it), and notes what else stood in its way.

## Beta: linux-v1.0.37.5-beta.1, add-on set 418 (pre-release; the stable line is main / the latest release)

On top of the stable linux-v1.0.37.4. Built and passing the tests; **not yet played in the game** (that is what the beta is for).

- **Fewer automated clicks: switching rooms in the app closes the game's window by keyboard shortcut** (it was a mouse click, up to
  three per switch). The dialogs' and windows' buttons are pressed through the shortcut's own secure button, which clicks the same
  button a touch on the screen does. Opening the game's bags on entering Bags stays a click for now (the backpack button reads
  the shortcut's Ctrl+Shift as a modifier).
- **Less work per update inside the game** (from the stable release's measured hitches: a full update ~45 ms):
  - the add-ons' log lines carry up to 3600 characters instead of 900 (the game takes ~4000, measured): a push to the PC is
    ~17 log writes instead of ~118, and a full update ~28 instead of ~112;
  - what you wear is collected again only when it changes (gear, durability, item info, level, or every 30 s), not in every full
    update (~6.5 ms each);
  - the bags' part of a full update is encoded once per bag change, not once per update (~5.7 ms each);
  - health, power and aura events are asked for only for the units the add-ons use (player, pet, target), not every nameplate.

## Known issues (main = the stable branch; bigger changes are tested on the `beta` branch first)

- A few window actions still go as mouse clicks: opening the game's bags when you enter Bags, closing a game window when you switch
  rooms, moving items between bags and Clean Up. Clicks can miss after controller play, and the aim is as few automated inputs as
  possible (the beta moves the room switch to keyboard shortcuts; the bags door stays a click: the backpack button reads the shortcut's
  Ctrl+Shift as a modifier).
- The quest turn-in "?" can be missing on Home's small map while the big map shows it (seen once, not looked into yet).
- Rarely "nothing received from the game" for a moment; it recovers by itself.
- The tooltip for an enemy under the dot cannot be forced on (WoW Forever owns those settings).

## 2026-11-21: linux-v1.0.37.4, add-on set 417 (the beta.1 line, tested)

- **Bag items by keyboard shortcuts in fights too** (potions from the bags): every shortcut now goes through a secure button set up
  out of combat, which picks the bag slot itself at the press, so nothing needs to be rebound while the fight's lockdown holds.
- **A bag slot picked by touch is one keyboard shortcut** (was three mouse clicks about 0.4 s apart, which also showed as clicks
  in the game): fewer automated inputs, and the cursor is there at once.
- **Less stutter.** A fight's start measured ~32 + ~20 ms (was ~70 + 65), its end ~59 ms (was 104):
  - the full document is built from its parts (the layout was encoded three times per update), and reuses the bags' own last
    document instead of reading every bag slot again (~14-24 ms per update);
  - at a fight's start PadMap's document (sent twice) and the Hub's (built twice) go once each, on later frames;
  - eleven documents are encoded once instead of twice; the group finder's catalogue is re-sent, not re-read, on the heartbeat;
  - the Hub's target frame no longer redraws for every cast of every unit; the box under the dot looks at the existing nameplates
    once per step; the resource bar's aura icons are only touched when they change; PadMap's binding check runs every 0.5 s.
- **Chat item links no longer stick on "Retrieving item information"**: a link whose item the game had not loaded yet is asked
  again (up to 8 times, a second apart) instead of keeping the placeholder.
- **Quicker answers:** the PC helper reads the game's log every 25 ms (was up to 200 ms after a quiet moment), and the keyboard
  shortcuts have shorter gaps between keys.
- **The Thor never downloads or updates WoW itself any more** (a game patch made it start updating its own folder).
- Fixed before release (beta.1 only): every keyboard shortcut raised a Lua error and the UI froze (WoW Forever's secure code has no
  `GetTime`).

## 2026-11-20 (evening): linux-v1.0.37.3, add-on set 415

- **Selling, buying and using bag items work again while streaming.** They went as mouse clicks, which land on the spot WoW parks
  its cursor at after controller play; they are keyboard shortcuts now (Sell = UP UP, Buy and the bags = DOWN DOWN + a selector;
  a bag cell is pressed through its own secure binding, out of combat only, as before). Needs this app and the add-on set 415.
- **Buttons came back slowly after a `/reload`:** the keyboard-shortcut handshake is now asked by keys when the app has a fresh
  document from the game, not by a click that was often lost.
- **Less stutter:** the add-ons' big updates no longer land in one frame. The 15 s heartbeat (the full document plus 18 add-ons
  re-sending their lists) cost a 140-200 ms frame; a fight's start one ~110 ms frame. That work is now spread over the following
  frames, one heavy job per frame. Measured in game: the heartbeat frame ~45 ms, a fight's start 2 x ~65 ms.
- **Typing in chat after a reload or reconnect:** the letters could land in another row of the tap pad (an old row map was used).
- Diagnostics: "hitch" documents for frames over 40 ms (events, documents, per-add-on times), "perf" documents at a fight's start.

## 2026-11-20 (afternoon): linux-v1.0.37.2

- **Fix: the HUD stayed WoW's own when you went straight into a fight after connecting.** Since 1.0.37.1 the keyboard-shortcut
  handshake is asked for only when you press a button, but a fight's buttons go straight to the game, not through the app, so
  nothing asked. Now any controller button you press asks (still never on a timer, at most every 2 s).

## 2026-11-20: DS Forever 1.0.37, add-on set 414

- **Releases with an APK:** each release now carries the signed APK, the Linux helper packed with its matching add-ons
  (`dsf-linux-helper-<version>.tar.gz`: unpack, `./install.sh`) and `SHA256SUMS`, beside the source. First one: `linux-v1.0.37.1`.

- **Merged DS Forever 1.0.37**: *Settings > General > Reset* (settings, layouts, skills or everything, each asks first), a
  *Support the Project* button (DS Forever's Ko-fi), auction house favourites and a sell grid with Post on Start, mailbox Open All,
  Abandon Pet and pet trainer fixes, confirm pop-ups that hold the controller, filter and Send glyphs that follow the controller
  layout, the Home info block (ammo at 0, bags used/total), and the cast bar's display text.
- This edition's own settings (box under the dot, soft target) go back to their defaults with *Reset settings*.
- **Add-ons you install on the Thor now reach the PC:** Settings > Add-ons' Polestar, Spoken, Manners (and QuestTrail) are installed
  into the PC's WoW by the Linux helper, from their own pinned downloads (checked), before WoW starts. A folder you installed yourself
  is left alone. Imported add-ons and QuestieDB updates still need DS Forever Desktop.
- **The power button in the pause menu closes WoW on the PC** (it saves first), as with DS Forever Desktop; it used to stay open until
  the 10-minute idle close.
- **Settings only show what works when streaming:** Frame limit / Frame generation and the Account group (they set up the Thor's own
  game) are hidden.
- **Buttons dead for up to a minute after login, a `/reload` or a stream reconnect:** the keyboard-shortcut handshake was asked for only
  when a button was pressed, at most every 10 s, by a click that is often lost; the presses meanwhile went as clicks and did nothing.
  A press now asks again after 2 s. Only your own presses ask: nothing is clicked on a timer any more, and after login the HUD
  restore waits for your first button press (then goes as a keyboard shortcut) instead of clicking after 15 s.
- **Box under the dot** reaches further: past the soft-target range it takes the nameplate right above the dot (friendly units too,
  while Friendly plates are on).
- Not in this edition: Desktop 0.2.45-0.2.46 (DS Forever Desktop is Windows-only; the Linux helper already never closes a WoW you
  started yourself).

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
