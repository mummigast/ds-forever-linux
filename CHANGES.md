# Changes in DS Forever Linux Streaming Edition

Newest first. This is the STABLE line (`main`); what the beta has on top: [CHANGES.md on the beta branch](https://github.com/mummigast/ds-forever-linux/blob/beta/CHANGES.md) (see "Stable and beta" in the README). Based on DS Forever 1.0.39 (upstream add-on set 424; this edition's set 458). What differs from DS Forever in general: [FORK.md](FORK.md).


## 2026-11-27: linux-v1.0.41.1, DS Forever 1.0.41, add-on set 464 (tested)

On top of linux-v1.0.39.2. Tested on the Thor 2026-11-27: hold to cast over the stream, our cast bar above the HUD, pinned buffs
cancelled in a fight, Edit Home tabs, the Controller room and its switches, indoor maps, Keyboard link, bank deposit and withdraw,
Smart Y by a campfire. Built and tested off-device only: the Group Finder by keys, the rumble, the bank's ZL / ZR.

### New from DS Forever 1.0.40 and 1.0.41 (upstream)

- **Edit Home tabs:** Out of combat, In combat and Party mode each keep their own Home layout, edited on their own tab.
- **Our own cast bar in fights,** right above the HUD on the top screen (or across the bottom screen if you pick that), with the
  swing timer.
- **Performance mode:** Home's animations ease off while you move or fight (the bottom screen redraws at ~30 Hz), automatically.
- **Lighter add-ons in fights:** fewer flushes and no full 15 s snapshot mid-fight.
- **Smart Y sits you down by a campfire.**
- **The Controller room** shows just Press and Hold per button (Move / Bind hold / Bind).

### New in this edition

- **Hold to cast while streaming:** two spells on one button - tap for one, hold for the other (hold time in Settings: 0.3 / 0.4 /
  0.55 s). Upstream built it for the Thor's own game only; here the presses to the PC go through the same timing, with the
  controller's Guide button as the "this was a hold" signal. A one-time check presses Guide once to see that the game gets it; once
  it works it is not repeated. If the check fails, hold to cast simply stays off.
- **Pin buffs for fights:** in Home's buff list, **Pin for fights** (up to two per character). In a fight the pause wheel (Start,
  page 3) shows **Cancel <buff>** for each: one press cancels it (for an accidental Divine Shield or Ice Block). **Unpin** in the
  same list.
- **Settings > Help > Keyboard link:** whether your presses reach the game as keys (green), which rooms still use clicks (amber),
  or that the link is not up yet (red).
- **Rumble:** the game's controller rumble reaches the Thor, and a short buzz when a queue pops, a ready check or an invite comes.
- **The Group Finder by keys** instead of clicks.
- **Settings tabs are easier to hit** (a full 48 dp touch area; the look is the same).
- **The map says "Your position is hidden by the game in here"** in dungeons and battlegrounds instead of going blank.
- **Problem reports go to this project:** Send opens a pre-filled issue on this repository.
- PC helper: `dsf-bridge doctor` also checks the PC clock, Sunshine's encoder (hardware or software) and other streaming programs;
  the Thor warns when the two clocks differ by more than 3 s.

### Fixed

- A game rumble running when the stream ended kept buzzing; it now stops.
- With a long buff list the pin buttons could end up without a cell; they now get theirs first.
- The Controller room's open by keys and upstream's new fight cast bar used the same internal code; ours moved (they would have
  triggered each other).
- **The Controller room's switches** (DS WoW toolbar, Combat controls, Start attack on cast) went to the game as screen clicks
  that often missed while streaming, so the toolbar seemed not to switch. They now go as keys, set straight to on or off.
- **The In combat diamond** in the Controller room left a button blank when it had no In combat spell, while the right page
  showed what it does in a fight. It now shows that normal action, dimmed.
- **Background art (indoor minimaps, icons) no longer builds while you stream:** it ran for up to 20 minutes during a stream
  (fan noise). It waits for the stream to end, as the indoor maps already did.
- **Smart Y's Sit by the fire** now works at WoW Forever's campfire (its "Violet Flames" buff), not only the classic Cozy Fire.
- **Bank:** ZL / ZR now jump between the bank and your bags (L / R still work too).
- The add-on's own **DSF Soft On / DSF Soft Off** account macros (a "?" picture, nothing to cast) are deleted and no longer made.

### Known issues in this release

- **Hold to cast:** holds belong to a tab: one set on Out of combat does nothing in a fight (set it on In combat too). If the Steam
  overlay opens when the Guide check runs, turn off Steam > Settings > Controller > "Guide button focuses Steam".
- A few actions still go as clicks: picking or casting a spell from the Spellbook room, the spell radials, party frames.
- Cancelling a pinned buff takes the pause wheel (Start, page 3); a quicker way is planned.
- Chat commands typed in the app's chat (`/reload`, ...) aren't sent: use the game's own chat for those.
- No dungeon map inside the Stockades. In a battleground, X on flags / corpses and Leave Battle are not played yet.

## 2026-11-24 (afternoon): linux-v1.0.39.2, add-on set 458 (bugfix)

On top of linux-v1.0.39.1. Tested on the Thor 2026-11-24: Professions from the first viewing, entering Bags. The bank changes are built and tested off-device, not played yet.

- **Professions show on the bottom screen the first time** you open one: the room's buttons go as keys instead of clicks that
  could get lost on the stream, and the recipe list is read again while the game is still loading it.
- **Entering Bags no longer fires your D-pad spell shortcuts:** the room takes the controller at once (by keys), before the game's
  own bag window opens behind it.
- **Bank:** the pointed item's name and kind show in the footer (for example "Recipe · Tailoring"); L / R jump the cursor between
  the bank and your bags; the Bank / Account Bank tabs are a row the D-pad reaches (A picks).

### Known issues in this release
- Chat commands typed in the app's chat (`/reload`, ...) aren't sent: use the game's own chat for those.
- A few actions still go as clicks: opening your bags' game window, moving items between bags, picking a spell from the spellbook.
- *In fights: Top screen* can put the moved buttons in the wrong layout.
- Live typing works in the auction house only (letters, digits and spaces; no å, ä or ö yet).
- No dungeon map inside the Stockades (being looked at). In a battleground, X on flags / corpses and Leave Battle are not played yet.

## 2026-11-24: linux-v1.0.39.1, DS Forever 1.0.39, add-on set 456 (tested)

On top of linux-v1.0.38.4. Tested on the Thor 2026-11-24: party invites with roles, the battleground entry pop-up, no "blocked" pop-up in a battleground, the Map room from the Start wheel, general play with no Lua errors. Not tested yet in a battleground: X on flags and corpses in a fight, Leave Battle.

- **DS Forever 1.0.39** (upstream): fewer freezes, sign-in fixes, Start opens the pause wheel with the toolbar off too, the auction
  house Sell list scrolls and shows the items the game won't take (greyed, with why), crate picks list trade goods.
- **Party and group pop-ups on the bottom screen:** an invite from a group with roles (it showed only on the top screen, with Accept
  greyed), battleground "Enter Battle", PvP and dungeon role checks, dungeon finder "Enter", ready checks, premade group invites,
  wargames and pet battles. Tap the buttons or use A / B. With no role ticked, your spec's role is ticked for you.
- **Leaving a battleground:** the end-of-match results show Leave Battle / Requeue on the bottom screen, and the pause wheel (Start)
  has Leave Battle on its third page while you are in a battleground (pick it twice).
- **X takes flags and loots corpses in a fight:** with something to interact with in front of you, X interacts instead of casting
  your In-combat X spell.
- **No "WowCompanion has been blocked" on every button press in battlegrounds:** a range check the game forbids in combat is no
  longer made in a fight.
- **No "large number of errors" warning in the middle of a fight:** that warning (its first button disables all add-ons) no longer
  pops up; Lua errors are kept in the add-on's save file for bug reports instead. Several errors in dungeons and battlegrounds fixed.
- **The Map room takes the controller again** (Start wheel → Map): it asks by keys instead of a click that often got lost on the
  stream, so the map scrolls with the stick and by touch.
- Smoother play: no 45 ms hitch every 5 seconds (the settings save runs every 30 s and never in a fight).

### Known issues in this release
- Chat commands typed in the app's chat (`/reload`, ...) aren't sent: use the game's own chat for those.
- A few actions still go as clicks: opening your bags, moving items between bags, picking a spell from the spellbook.
- *In fights: Top screen* can put the moved buttons in the wrong layout.
- Live typing works in the auction house only (letters, digits and spaces; no å, ä or ö yet).
- No dungeon map inside the Stockades (being looked at).

## 2026-11-23 (late): linux-v1.0.38.4, add-on set 439 (beta 4, tested)

On top of linux-v1.0.38.3. Tested on the Thor 2026-11-23: the remote's buttons, selecting a result row, a buy and a sale through it, the keyboard.

- **The auction house remote on the bottom screen:** the game's own buttons that are shown now (Buy / Sell / Auctions, Search,
  Filter, Favorites, Back, Buy now, Buyout, Bid, OK, Cancel, Post, Cancel auction, scroll) and the visible result rows, a finger each.
  Each is one keyboard shortcut that clicks the game's own button (no D-pad hunting, no guessing what the game aims at). Quantity,
  Price, Min / Max level and the search line put the game's cursor in that box, and the keyboard comes up only then.
- **No keys or clicks into the wrong window:** the PC helper tells the Thor which window is in front; while it is not WoW (e.g.
  Battle.net, whose Play button once got our Enter and started a second WoW), the app holds its keys and clicks back and asks for
  WoW to be brought to the front.
- "Bought lately" lists a stackable buy once, with its count.

## 2026-11-23 (evening): linux-v1.0.38.3, add-on set 433 (bugfix)

- **Buying in the auction house works again:** the confirm (OK) did nothing. The add-ons no longer listen in on the game's own buy
  calls (that is what stopped them on WoW Forever); what you bought is read when the game says the purchase went through.
- Known: a listing you post shows under "Your auctions" on the bottom screen the next time you open the auction house.

## 2026-11-23 (afternoon): linux-v1.0.38.2, add-on set 431 (beta 3, tested)

On top of linux-v1.0.38.1. Tested on the Thor 2026-11-23.

- **Live typing in the auction house:** put the game's search box in focus with the controller, and the bottom screen's keyboard
  types straight into it, letter by letter, as real keys (letters, digits and spaces). **Done** is the game's own Enter, so the
  search runs by itself. The game's controller cannot reach the Filter's level range boxes, so the bottom screen shows **Min level** /
  **Max level** while the Filter is open: a finger puts the game's cursor in that box (one key), and the game's own Tab switches
  between them. Without a game text box in focus the keyboard sends nothing (the old typed rows pressed many keys per word).
- **Fewer clicks after a /reload:** the keyboard link with the add-ons is checked again by keys, not by up to four clicks, and the
  stream's tap calibration tries once (2 clicks) instead of three times.

## 2026-11-23: linux-v1.0.38.1, DS Forever 1.0.38, add-on set 426 (the beta.2 line + upstream, tested)

Tested on the Thor 2026-11-23: login and the key handshake, the top screen's restore, quests, a fight, the auction house, Edit Home,
the Controller room and the tap-to-cast bar.

- **Everything new in DS Forever 1.0.38** ([its notes](https://github.com/Jreese702/DS-Forever/releases/tag/v1.0.38)): edit Home like a
  phone's home screen, *In fights: Top screen*, the rebuilt Controller room with your own macros and tap-to-cast slots for fights and
  Party mode, Spell rank badges, voice typing language, lighter memory use and its fixes. The loading-screen wait this edition sent
  upstream (PR #567) comes back in upstream's improved form.
- **The auction house is the game's own window** on the top screen, worked with WoW Forever's own controller navigation; the app's
  auction-house screen is gone. The bottom screen is its keyboard: type the search there and press Done (the words go into the
  game's search box; press the game's Search with the controller), and see your auctions and what you bought lately (read only).
- **Far fewer automated clicks** (keyboard shortcuts instead):
  - the Controller room opens by keys (was 8 clicks); picking an item, mount, command or macro for the tap-to-cast bar is keys;
  - **pressing a tap-to-cast slot is a key** that casts the slot's spell / item / macro itself (its clicks missed now and then);
  - switching rooms closes the game's window by keys (was up to three clicks per switch);
  - typing (the auction-house search, the app's chat) is the row's keys once, then one key per letter; the Auras pick and the
    Talents rows go as keys too.
- **"Box under the dot" is now called "Ranged tooltips"** (*Settings > Top screen > Tooltips*; `/wcbox` still switches it). It takes
  over the game's leftover tooltip of another unit.
- **Less work per update inside the game:** log lines up to 3600 characters (~17 log writes per push instead of ~118), worn gear and
  the bags' part of an update collected / encoded only when they change, unit events only for the units the add-ons use.

## Known issues (main = the stable branch; bigger changes are tested on the `beta` branch first)

- A few actions still go as mouse clicks: opening the game's bags when you enter Bags (the backpack button reads the shortcut's
  Ctrl+Shift as a modifier), moving items between bags and Clean Up, picking a spell from the spellbook for a button, and two
  calibration taps at login. The aim is as few automated inputs as possible.
- *In fights: Top screen* (new in 1.0.38): the buttons that move to the top screen can get the wrong layout.
- The tap-to-cast bar by keys is tested out of combat; in a fight it is built to work the same way (as bag items do), not yet played.
- In the first seconds of a session, before the app's keyboard link with the add-ons is up, a few setting taps still go as clicks.
- Live typing types letters, digits and spaces (not yet å, ä, ö or symbols), in the auction house only; the chat types as before.
- A listing you post shows under "Your auctions" on the bottom screen the next time you open the auction house.
- The quest turn-in "?" can be missing on Home's small map while the big map shows it (seen once, not looked into yet).
- Rarely "nothing received from the game" for a moment; it recovers by itself.
- The tooltip for an enemy under the dot cannot be forced on (WoW Forever owns those settings).
- No dungeon map inside the Stockades (seen 2026-11-24, being looked at; upstream 1.0.39's indoor-map work may cover it).
- In a battleground, X on flags / corpses in a fight and the pause wheel's Leave Battle are built and tested off-device, not played yet.

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
