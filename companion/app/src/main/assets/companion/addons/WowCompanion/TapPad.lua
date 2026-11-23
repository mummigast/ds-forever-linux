-- WowCompanion / TapPad.lua
-- THE ONE SHARED INPUT CHANNEL (user ruling 2026-09-27): every room's app -> addon action is ONE
-- TAP on the top screen. Owned by the quests session; ask in AGENT_LOG.md for changes.
--
-- An addon cannot receive anything from outside the game at runtime: no sockets, no file reads,
-- no clipboard read (checked against the client's string table). The only way in is input. Typed
-- chat was the first route and it is broken on this device: Android's keyboard system swallows the
-- characters once the game's edit box has focus, leaving the box open (measured 2026-09-27).
--
-- So the addon owns a grid of INVISIBLE buttons at a spot it publishes, and the app taps a cell.
-- GameNative runs the container in touchscreen mode, so a tap on display 0 arrives as a mouse
-- click, and the button's OnClick runs. PROVEN ON THE THOR (probe, 2026-09-27): the click
-- landed in 69 ms, at exactly the intended pixel, with no chat box and the controller left in play
-- mode. One touch = one click = one action.
--
-- GRID: one ROW per operation, one COLUMN per slot.
--   * pad.op(name, ns, handler): a plain row. A slot is a stable key (a questID) within a
--     namespace. A key keeps its column for as long as it lives, and a freed column is quarantined
--     for QUARANTINE seconds before reuse, so a tap made from a slightly stale document can never
--     land on a different key. The handler receives the KEY; replies echo it so the app can check.
--   * pad.secureRow(name, ncols, init, onClick[, opts]): a row of SecureActionButtonTemplate cells, for
--     actions the game only allows from a hardware event (use an item, cast). A mouse click on a
--     secure button IS a hardware event. The cells' attributes are set by init(button, col) and are
--     STATIC: secure frames cannot be created, changed or moved in combat, so all of that happens
--     out of combat (queued until PLAYER_REGEN_ENABLED), while clicking them works in combat.
--
-- A PLAIN ROW'S HANDLER RUNS AS ADDON (TAINTED) CODE. It must NEVER call Blizzard's own UI Lua that
-- opens, closes or rearranges a game window (CloseAllBags / OpenAllBags / ToggleSpellBook / ShowUIPanel
-- / ...), and must never write a field on a Blizzard frame or table. Blizzard's code then runs tainted,
-- and on this controller client the gamepad action bar's UpdateInteractIcons hits the protected
-- SetPreferredGamepadInteractTarget() and is refused on every target change until a reload. It
-- happened twice on 2026-09-28: 4,012 refusals after a `/wcpad show` typed into chat (11:06), and 2,050
-- in 90 s after a plain op called CloseAllBags / OpenAllBags (22:57). Game-engine calls (C_QuestLog.*,
-- C_SuperTrack.*, SetAlpha, ...) are fine; to press one of the GAME's controls, use a secureRow cell
-- whose click presses that control.
--
-- A PLAIN CELL FIRES ON THE PRESS (pad5, 2026-09-30). The professions session measured on the Thor that in controller
-- freelook the game puts its hidden cursor back in the middle of the screen (640,287 read just after a tap), and when that
-- lands between `input tap`'s press and release, the release is off the button: a cell registered for the release
-- ("AnyUp", pad4) never fired. 2 of 10 taps right after a controller press were lost that way, while the press itself
-- landed inside the intended cell 10 of 10 times. So plain cells register for the PRESS only: they fire where the pointer
-- is known to be right.
-- BUT ONE TAP ARRIVES AS TWO PRESSES on this device (pad5 on the Thor, 2026-09-30 14:04: every Quests action answered twice,
-- 2 ms apart; bags had seen a "stray second press" 3 ms after a drop). pad4 hid that, because both presses share one release.
-- So a cell ignores a repeat press within REPEAT seconds of its last one (pad5b): once per tap, on the first press.
-- SECURE CELLS CANNOT DO THE SAME: for a real mouse click, the game's secure template acts on the RELEASE whatever the
-- ActionButtonUseKeyDown setting (securetemplates.lua SecureActionButton_OnClick: `useOnKeyDown = not isSecureMousePress
-- and ...`), and so does their onClick hook. A secure cell tapped right after a controller press can still be lost; the
-- owning room's answer (or its absence) is what shows it.
-- UNLESS THE CELL HAS NO SECURE ACTION (pad6b, the spells session's ask 2026-10-01): a secure row may mix cells that press a
-- game control with cells that only run the row's onClick (spells turned its whole row secure for 3 such cells, the pad
-- being full). With opts.onPress, a cell whose "type" is nil runs onClick on the PRESS, like a plain cell and with the same
-- REPEAT guard, and nothing on the release; a cell with a secure action keeps the release. Older pads ignore the argument.
--
-- A STRAY PRESS LANDS ON THE FREELOOK PARK POINT, SO A SINK SITS THERE (pad6, 2026-09-30). In controller freelook the game
-- parks its hidden cursor at one fixed point, game px (480, 214.5) on this 960x540 screen: measured by the mouse diagnostic on
-- 2026-09-28, and again on 2026-09-30 15:44:37 by the professions session, when the game snapped the cursor there just
-- BEFORE an injected press. That press landed on the 3D world (GetMouseFoci empty) and could have targeted or interacted
-- with whatever stood there: a game action from no touch of its own. A tap is never meant to land there, so a small frame
-- covers that point: BACKGROUND strata, so every game window above it still takes its own clicks and only the WORLD is
-- below it; CLICK ONLY (SetMouseMotionEnabled false), so the parked cursor's hover over the world still works. A press
-- that lands on it does nothing in the game and is reported (a "padstray" document, at most one a second), so the room's
-- missing answer has a reason. What it cannot catch: a press snapped anywhere else (none measured).
-- WHILE ANYONE HOLDS THE CONTROLLER IT GOES ON TOP (pad6c, Home's ask 2026-10-01, raised by calendar). The user's ruling "every
-- room opens the game's own window behind it" means a holding room's game window is OPEN, hidden by alpha, and an invisible
-- window still takes clicks: on BACKGROUND the sink sat under it, so a stray press would land on a spell, an item or a calendar
-- control nobody can see. So while the shared capture has a holder (a room, or interact's "npc"), the sink is TOOLTIP strata,
-- above every window; with no holder it is BACKGROUND again (today's behaviour: visible windows take their own clicks). The
-- capture has no change hook, so a ticker reads its state() every SINK_POLL seconds. The sink is a plain frame: changing its
-- strata is allowed in combat, so the rule holds through a fight. Still click only: hover is unchanged either way.
--
-- GEOMETRY IS MEASURED, NEVER ASSUMED. The game renders at 960x540 on this device and GameNative
-- scales it 2x; the UI scale is 0.94. describe() publishes the grid in the game's own pixels,
-- top-left origin, together with that pixel size, and the app converts to display pixels itself.
-- A secure row is only published while its cells really sit at the published geometry: if the
-- screen is re-laid out in combat, secure rows drop out of describe() until combat ends.

local ADDON = ...
local WC = _G.WowCompanion
if type(WC) ~= "table" or type(WC.emit) ~= "function" then return end
local S, SN, CALL = WC.S, WC.SN, WC.CALL

local PADV = "pad35"     -- pad35 THE 1.0.38 MERGE (Linux Streaming Edition, 2026-11-23): the fork's line and upstream's both kept. Fork: pad34 sticky typing rows: one key per letter after the row's keys. pad33 the chat rows chq / chr / chs as far rows (typing into the AH search by keys). pad32 aurapick / talents / talentn as far rows. pad31 secure far "click" cells by keys (bag0 doors, idlg), columns 36-39 too. pad30 key-only rows (pad.keyRow; Bags' bcur0..5: a slot pick in one step). pad29 Bags' pick rows (bmvq, bagsort, bmv) are far rows: a slot pick by keys. pad28 THE SECURE KEY ROUTER: every key through a secure proxy; a bag far pick works in fights. pad27 FAR ROWS: DOWN DOWN <selector> (ibuy, iqty, keytest, the bag rows by a secure swap). pad26 UP UP = isell (vendor Sell as keys). pad25 NO CURSOR FROM OUR OWN PRESSES (the user, 2026-11-19, streaming 1.0.36: "the cursor keeps randomly showing on the game"; the Thor's taps.log: every press Desktop posts moves the game's own cursor to the cell, and pad13's rule showed it again on that move - ResetCursor - until it had rested a second at the park): a press of ours (a cell, the calibration strip, the layout catcher) ARMS the blank cursor at once; the moves a press explains (to the cell and the game's park, within PRESS_WIN of it, or back to the park spot it learned) keep it blank wherever it rests, over the world or a window; the first move nothing of ours explains (a real mouse, the trackpad, a touch on the top screen) disarms it and is kept as pad.humanAt (Dialogs d35 reads it); an item on the cursor or a spell aiming shows it, and it is still only under the game's own cursor drawing (pad14's soft()); nothing saved, no setting changed; pad24 THE STREAM'S TAPS MEASURED (the user, 2026-11-18, test 1494 streamed: "testing stream, ui still didnt hide"; pad23's ring proved every "ui" tap (row 51, aimed y 115.5) pressed "uisw" (row 50) and every "pnav" tap (row 1, y 15.5) pressed "chq" (row 2) while the rows between were right: on the PC the game sees a press about 2 % closer to y ~65 than the app aims it): THE CALIBRATION STRIP, one plain press-only Button of ours, CAL_W game px wide, CAL_GAP left of the grid, over the band's full placed height, that does nothing but keep where the game saw each press (GetCursorPosition, read only; describe()'s `calib`: its box, the count and the last 4 "x,y" in game px), so the app taps it twice (top and bottom) and aims every tap through what it measured; the ring of presses also keeps where each was seen (rxDoc `at`, beside `last`); the catcher's band zone takes the strip in; nothing else changed; pad23 WHERE A TAP LANDED (the user, 2026-11-18, test 1492 streamed: "it looked like it was doing a lot of clicks again and also the UI didnt hide"; the "ui" row's restore and layout taps were never answered on the PC while the "uisw" row 2 px above them was): every cell press is kept in a ring of the last 8 ("row:col", pad.rxDoc: the count and the ring, read by Hub's document), and describe() says `off` = the rows whose first cell does NOT stand where the grid says (its real top in game px, read off the frame; normally absent) - read only, nothing else changed; pad22 THE LAYOUT EDITOR'S CATCHER AND STORE (the user, 2026-11-16: "we need to make a way to basically edit the UI locations on the top screen from our UI menu"; the design's picks, all the recommended ones: our own pieces first, taps that set an exact spot): WC.lay at the end of this file - the per-character saved layout of our own top-screen pieces (WowCompanionDB.lay[name-realm]), the editor's view of its draft, and THE CATCHER, one full-screen plain button at TOOLTIP strata under every cell and the sink, press only, that reads where a tap landed (its own 60 ms same-spot guard, the pad band and the sink left out, the reach switch); nothing else changed; pad21 THE SHARED ROW (the 1.0.32 test build, code 1472: the Macros room's lazy row "mac" had no row at the fullest layout - six bags, the cast bar, both radials - so the room said "No pad row"): a secure row registered with opts.share is a GUEST on another secure row (its own cells; one of the two on the row at a time, the host by default; the other hidden and left out of describe()), pad.lease(name) puts one on the row out of combat (in a fight it waits), pad.holds(name); the Macros room is the Calendar room's guest (Spells s12, Book b65: padtab 39 then 34 / 35); pad20: pad15's switch-back-on now finds an add-on the game has off by the game's own reason too (issue #278, the user relaying a player, 2026-11-13: "says waitin on wow controller. i press start and the wheel only pops up on top screen": the login probe said WowCompanionSpells:DISABLED and pad15 never switched it on - GetAddOnEnableState(name, character) did not say 0 on that client); pad19: pad.op(..., { last = true }) pins a row to the LAST row (ROWS_MAX - 1; Bags' shared drag row "bmv", the user 2026-11-13: "Bags share one row"); pad18: pad16's health probe and pad17's health strips REMOVED (the user, 2026-11-05: reading hidden health off the screen would break Blizzard's terms); pad17: five hair-thin health strips in the top-left corner, filled by the game (probe strips); pad16: a read-only health probe (every reader's kind on a health change, probe hpprobe); pad15: our add-ons the game has switched off are switched on again at login (the app reloads once); pad14: the software cursor (gxCursor 0, set once) and the hiding only under it (the hardware cursor drew the blank as a black box); pad13: the cursor hidden once still for a second anywhere over the world (the game parks it at y 41 %, not the centre); pad12: the PARKED CURSOR hidden (a blank cursor while it rests at the screen centre over the world); pad11 (Party mode, the lead's contract PARTY_BUILD.md 2.1): ROWS_MAX 56 for the party row; nothing else changed || Upstream 1.0.38: pad27 NO PARTIAL CHARACTER KEY (the 11-20 hunter, test build 1513): L.who() (the layouts' key) is Safety k6's WC.charKey(), nil until the realm is known (it was "Name-" with an empty realm); pad26 THE ROW ORDER (GitHub #550, with #564 / #570 / #249 / #260: "top screen ui doesnt update when editing in settings"; the reporter: the switches only failed with the game at about 960x540, at 1280x720 everything toggled): a row is no longer given the next free row in the order the add-ons happen to register, but ITS OWN ROW from ORDER (below), ranked by impact - the top screen's switches "uisw" and its one-tap restore / layout row "ui" FIRST (rows 0-1, placed at any resolution and UI scale), the least used rows last, so a smaller layout drops those; describe() says `drop` = the registered rows this layout cannot place (name -> row; normally absent), so the app can say so once instead of waiting on a row that is not there; same cells, same geometry, same fits(); a name not in ORDER takes the lowest free row, as before; pad25 NO CURSOR FROM OUR OWN PRESSES (the user, 2026-11-19, streaming 1.0.36: "the cursor keeps randomly showing on the game"; the Thor's taps.log: every press Desktop posts moves the game's own cursor to the cell, and pad13's rule showed it again on that move - ResetCursor - until it had rested a second at the park): a press of ours (a cell, the calibration strip, the layout catcher) ARMS the blank cursor at once; the moves a press explains (to the cell and the game's park, within PRESS_WIN of it, or back to the park spot it learned) keep it blank wherever it rests, over the world or a window; the first move nothing of ours explains (a real mouse, the trackpad, a touch on the top screen) disarms it and is kept as pad.humanAt (Dialogs d35 reads it); an item on the cursor or a spell aiming shows it, and it is still only under the game's own cursor drawing (pad14's soft()); nothing saved, no setting changed; pad24 THE STREAM'S TAPS MEASURED (the user, 2026-11-18, test 1494 streamed: "testing stream, ui still didnt hide"; pad23's ring proved every "ui" tap (row 51, aimed y 115.5) pressed "uisw" (row 50) and every "pnav" tap (row 1, y 15.5) pressed "chq" (row 2) while the rows between were right: on the PC the game sees a press about 2 % closer to y ~65 than the app aims it): THE CALIBRATION STRIP, one plain press-only Button of ours, CAL_W game px wide, CAL_GAP left of the grid, over the band's full placed height, that does nothing but keep where the game saw each press (GetCursorPosition, read only; describe()'s `calib`: its box, the count and the last 4 "x,y" in game px), so the app taps it twice (top and bottom) and aims every tap through what it measured; the ring of presses also keeps where each was seen (rxDoc `at`, beside `last`); the catcher's band zone takes the strip in; nothing else changed; pad23 WHERE A TAP LANDED (the user, 2026-11-18, test 1492 streamed: "it looked like it was doing a lot of clicks again and also the UI didnt hide"; the "ui" row's restore and layout taps were never answered on the PC while the "uisw" row 2 px above them was): every cell press is kept in a ring of the last 8 ("row:col", pad.rxDoc: the count and the ring, read by Hub's document), and describe() says `off` = the rows whose first cell does NOT stand where the grid says (its real top in game px, read off the frame; normally absent) - read only, nothing else changed; pad22 THE LAYOUT EDITOR'S CATCHER AND STORE (the user, 2026-11-16: "we need to make a way to basically edit the UI locations on the top screen from our UI menu"; the design's picks, all the recommended ones: our own pieces first, taps that set an exact spot): WC.lay at the end of this file - the per-character saved layout of our own top-screen pieces (WowCompanionDB.lay[name-realm]), the editor's view of its draft, and THE CATCHER, one full-screen plain button at TOOLTIP strata under every cell and the sink, press only, that reads where a tap landed (its own 60 ms same-spot guard, the pad band and the sink left out, the reach switch); nothing else changed; pad21 THE SHARED ROW (the 1.0.32 test build, code 1472: the Macros room's lazy row "mac" had no row at the fullest layout - six bags, the cast bar, both radials - so the room said "No pad row"): a secure row registered with opts.share is a GUEST on another secure row (its own cells; one of the two on the row at a time, the host by default; the other hidden and left out of describe()), pad.lease(name) puts one on the row out of combat (in a fight it waits), pad.holds(name); the Macros room is the Calendar room's guest (Spells s12, Book b65: padtab 39 then 34 / 35); pad20: pad15's switch-back-on now finds an add-on the game has off by the game's own reason too (issue #278, the user relaying a player, 2026-11-13: "says waitin on wow controller. i press start and the wheel only pops up on top screen": the login probe said WowCompanionSpells:DISABLED and pad15 never switched it on - GetAddOnEnableState(name, character) did not say 0 on that client); pad19: pad.op(..., { last = true }) pins a row to the LAST row (ROWS_MAX - 1; Bags' shared drag row "bmv", the user 2026-11-13: "Bags share one row"); pad18: pad16's health probe and pad17's health strips REMOVED (the user, 2026-11-05: reading hidden health off the screen would break Blizzard's terms); pad17: five hair-thin health strips in the top-left corner, filled by the game (probe strips); pad16: a read-only health probe (every reader's kind on a health change, probe hpprobe); pad15: our add-ons the game has switched off are switched on again at login (the app reloads once); pad14: the software cursor (gxCursor 0, set once) and the hiding only under it (the hardware cursor drew the blank as a black box); pad13: the cursor hidden once still for a second anywhere over the world (the game parks it at y 41 %, not the centre); pad12: the PARKED CURSOR hidden (a blank cursor while it rests at the screen centre over the world); pad11 (Party mode, the lead's contract PARTY_BUILD.md 2.1): ROWS_MAX 56 for the party row; nothing else changed
local COLS = 40          -- columns per row; the quest log holds at most 40, a bag at most 36
local ROWS_MAX = 56      -- rows that may register; only those that end ABOVE the pop-up dialogs are placed (pad8 / pad9 / pad11, see below)
local POPUP_MARGIN = 1   -- game px a row keeps clear of popupTop
local CELL_W = 6         -- game pixels per cell, across (12 display px on the Thor)
local CELL_H = 2         -- game pixels per cell, down (4 display px) -- see below
local QUARANTINE = 30    -- seconds a freed column stays unused
local REPEAT = 0.25       -- seconds: a second press on the same plain cell within this is the same tap (see above)
local PARK_X, PARK_Y = 0.5, 214.5 / 540   -- the freelook park point, as fractions of the game's screen (see above)
local SINK = 10          -- game pixels across the stray-press sink, centred on the park point
local SINK_POLL = 0.1    -- seconds between reads of the capture's holder (the sink's strata follows it)
local TOP_GAP = 12       -- game pixels between the screen's top edge and the first row
local CAL_W = 6          -- pad24: game pixels across the calibration strip (see THE STREAM'S TAPS MEASURED)
local CAL_GAP = 6        -- pad24: game pixels between the strip and the grid's first column
-- ROW HEIGHT (user rulings 2026-09-28: ~18:55 "thinner rows, 3 px"; ~21:10 "2 px rows now", before the first push, because the
-- rooms' requests reached 27 rows, 31 with more bags). 16 rows of 6 px filled up, and rows 13+ reached down into the game's
-- pop-up dialogs, which Blizzard anchors TOP at -135 UI units, centred right under this grid (89 game px at this device's 0.94
-- UI scale; `popupTop` in describe()). The cells are TOOLTIP strata, so a row inside a dialog turns a finger tap on its
-- buttons into a pad action. 2 px rows fit 38 rows above the dialogs. A tap lands at a row's centre, +/-1 game px from its
-- edges; the mouse diagnostic measured the vertical landing EXACT (y 15.0 / 81.0). An earlier try at 2 px ("pad3") looked
-- dead, but that was the TapBridge 1240-width bug misaiming x, not the rows. The app never assumes a size: it reads cw / ch
-- from describe(). Any change here gets ONE real tap test on the Thor before rooms rely on it; if it misses, 6 px goes back.
-- ROWS PAST 37 (pad8, 2026-10-06, the consumables radial's row; the pad was full). 38 was the count that fits above the dialogs
-- on GameNative's 960x540 (popupTop 89.2 game px). WoW Forever renders 1920x1080, where the dialogs start at 135 UI units = 121.5
-- px or lower at any UI scale the game allows (0.64-1.15), so 48 rows (ending at 108 px) fit there. So up to ROWS_MAX rows
-- register, and a row is PLACED (shown, published in describe()) only while its bottom is above popupTop, measured at every
-- layout: on 960x540 that is still exactly rows 0-37; a row that does not fit is hidden, never left inside a dialog. Rows keep
-- their places, so rows 0-37 never move.
-- pad9 (2026-10-07, the pad owner's: the rooms' rows reached 45 of 48, 47 with a reagent bag): ROWS_MAX 54. At 1920x1080 the
-- dialogs' top is 135 UI units = 121.5 px at the SMALLEST UI scale the game allows (UIParent 1200 units tall); a row is placed only
-- while it ends at least POPUP_MARGIN above it, so row 53 (ending at 12 + 54 x 2 = 120) is the last that fits at EVERY UI scale --
-- all 54 are placed whatever scale the player picks (the Thor's own scale fits 56). Nothing else changed: same cells, same rules.
-- pad10 / pad10c (2026-10-09, L1 THE KEY CHANNEL: the user's pick "L1 key channel" via Home): see THE KEY CHANNEL below.
-- pad11 (2026-10-28, Party mode's ONE secure row "party"; the pad was full at 54 with every bag and the reagent bag): ROWS_MAX 56.
-- On the Thor's own UI scale (popupTop 126.6 game px) rows 0-55 fit (row 55 ends at 12 + 56 x 2 = 124); at the SMALLEST scale (121.5)
-- rows 54-55 are neither placed nor described, exactly as pad8 / pad9 drop rows, and the app finds those cells missing. Same cells,
-- same geometry, same fits() and describe(). One real tap test on the device is owed before release (probe P11).
-- pad26 THE ROW ORDER (GitHub #550 and its duplicates #564, #570, #249, #260). Rows were handed out in the order the add-ons registered
-- them, and Hub's top-screen switch rows "uisw" / "ui" register late (rows 49-50 of 56). fits() places only the rows that end above
-- popupTop, and that is fewer rows than 56 on a smaller layout: at the game's 960x540 (popupTop 94.9) rows 0-39, at 1280x720 with a
-- lowered UI scale (#249: 107.6) rows 0-46, at 1920x1080's smallest scale (121.5) rows 0-53, at 960x540's smallest (0.64: 60.75) rows
-- 0-22. So the switches were never placed there and their tiles waited forever. Now every known row has ITS OWN ROW, its place in
-- ORDER, ranked by impact: the rows the top screen's switches and the one-tap restore need first (they fit at any layout the game
-- allows), then the rooms' everyday rows, the least used last. A row keeps its row whatever order the add-ons load in or whichever
-- add-on is off (a lazy row's row waits for it), so taps from a stale document still never land on a different row. Which rows a
-- smaller layout drops (the bands are the measured layouts above; a room's rows are kept together across each band's edge):
--   every layout:  uisw ui padtab spells sradial qpick qact ipick iact idlg pause gamemenu party pfocus bag0-5 binv pnav uwp (rows 0-22)
--   below 1920x1080's smallest scale (rows 54-55):  keytest, bmv
--   and below 1280x720 lowered (#249, rows 47-53):  prof profsel profopen, gf gfl gfw gfclose
--   and below 960x540 (rows 40-46):                 talents talentn, aurapick auracancel, spick sact, cal (+ its guests mac, lay)
--   and below 960x540's smallest (rows 23-39):      chq chr chs chcmd, ibuy isell iqty itrain, castbar radial classr tcast, mapw,
--                                                   bagsort bmvq, extra radialpin
-- A name not in ORDER (a new row nobody ranked yet: add it here; tools/test_pad_order.py fails on one) takes the lowest free row, as
-- every row did before; opts.last (pad19) is kept for such a name. A ranked row whose own row is taken does the same. describe()'s `drop` lists the registered rows this layout does not place, so the
-- app can say so (once) and never waits on them.
local ORDER = {
    "uisw", "ui",                                                    -- 0-1   the top screen's switches; the one-tap restore / layout
    "padtab",                                                        -- 2     Book's one-shot pick (leases, the chooser)
    "spells", "sradial",                                             -- 3-4   the Spellbook's cells; the spell radials (fights)
    "qpick", "qact",                                                 -- 5-6   Quests
    "ipick", "iact", "idlg",                                         -- 7-9   the NPC dialogs
    "pause", "gamemenu",                                             -- 10-11 the pause wheel; the Game Menu
    "party", "pfocus",                                               -- 12-13 Party mode; the unit menu
    "bag0", "bag1", "bag2", "bag3", "bag4", "bag5", "binv",          -- 14-20 Bags: the items, the worn gear
    "pnav", "uwp",                                                   -- 21-22 the routes
    "chq", "chr", "chs", "chcmd",                                    -- 23-26 Chat's keyboard
    "ibuy", "isell", "iqty", "itrain",                               -- 27-30 vendors, trainers
    "castbar", "radial", "classr", "tcast",                          -- 31-34 the cast bar, the radials, touch cast
    "mapw",                                                          -- 35    the Map room
    "bagsort", "bmvq",                                               -- 36-37 Bags' sort / move queue
    "extra", "radialpin",                                            -- 38-39 the Controller room's Extra tab; the radials' pins
    "talents", "talentn",                                            -- 40-41 Talents
    "aurapick", "auracancel",                                        -- 42-43 the Character room's auras
    "spick", "sact",                                                 -- 44-45 Social
    "cal",                                                           -- 46    Calendar (Macros and the layout editor are its guests)
    "prof", "profsel", "profopen",                                   -- 47-49 Professions
    "gf", "gfl", "gfw", "gfclose",                                   -- 50-53 the Group Finder
    "keytest",                                                       -- 54    the key channel's sweep / handshake (no keys: clicks)
    "bmv",                                                           -- 55    Bags' drag row (pad19: the first to go)
}
local SLOT = {}
for i, n in ipairs(ORDER) do SLOT[n] = i - 1 end
local POPUP_TOP_UNITS = 135

local pad = { ORDER = ORDER, SLOT = SLOT, rows = {}, byRow = {}, nrows = 0, ns = {}, geom = nil, info = nil, visible = false,
              listeners = {}, secureAt = nil, securePending = false }
WC.pad = pad

local function scaleInfo()
    local okP, pw, ph = CALL(function() return GetPhysicalScreenSize() end)
    local uw = SN(function() return UIParent:GetWidth() end)
    local uh = SN(function() return UIParent:GetHeight() end)
    if not okP or type(pw) ~= "number" or type(ph) ~= "number" or not uw or not uh
       or uw <= 0 or uh <= 0 then
        return nil
    end
    return { sx = pw / uw, sy = ph / uh, pw = pw, ph = ph }
end

-- identity of the current geometry, to tell whether secure cells still sit where describe() says
local function geomKey()
    local g, i = pad.geom, pad.info
    if not g or not i then return nil end
    return string.format("%d|%d|%d|%d|%.6f|%.6f", g.x, g.y, g.pw, g.ph, i.sx, i.sy)
end

-- ---------------------------------------------------------------- slots

function pad.slotFor(ns, key)
    if key == nil then return nil end
    local t = pad.ns[ns]
    if not t then t = { byKey = {}, byCol = {}, freedAt = {} }; pad.ns[ns] = t end
    local c = t.byKey[key]
    if c then return c end
    local now = GetTime()
    for col = 0, COLS - 1 do
        if t.byCol[col] == nil and (not t.freedAt[col] or now - t.freedAt[col] > QUARANTINE) then
            t.byKey[key] = col
            t.byCol[col] = key
            t.freedAt[col] = nil
            return col
        end
    end
    return nil          -- every column busy or quarantined; the app shows the actions as unavailable
end

-- Free the columns of keys that are no longer present. present = { [key] = true, ... }
function pad.retain(ns, present)
    local t = pad.ns[ns]
    if not t then return end
    local now = GetTime()
    for key, col in pairs(t.byKey) do
        if not present[key] then
            t.byKey[key] = nil
            t.byCol[col] = nil
            t.freedAt[col] = now
        end
    end
end

-- ---------------------------------------------------------------- cells

local function paint(btn)
    if not btn.tex then
        btn.tex = btn:CreateTexture(nil, "OVERLAY")
        btn.tex:SetAllPoints()
    end
    if pad.visible then btn.tex:SetColorTexture(1, 0.82, 0, 0.35) else btn.tex:SetColorTexture(0, 0, 0, 0) end
end

-- a brief flash is the only thing a player ever sees of the pad: proof a tap landed
local function flash(btn)
    if not btn.tex then return end
    btn.tex:SetColorTexture(0.3, 1, 0.3, 0.7)
    C_Timer.After(0.35, function() paint(btn) end)
end

local function place(btn, row, col)
    local g, i = pad.geom, pad.info
    if not g or not i then return end
    btn:SetSize(CELL_W / i.sx, CELL_H / i.sy)
    btn:ClearAllPoints()
    btn:SetPoint("TOPLEFT", UIParent, "TOPLEFT", (g.x + col * CELL_W) / i.sx, -(g.y + row * CELL_H) / i.sy)
    paint(btn)
end

local function fire(row, col)
    local r = pad.byRow[row]
    if not r or type(r.handler) ~= "function" then return end
    local key = nil
    if r.ns then
        local t = pad.ns[r.ns]
        key = t and t.byCol[col] or nil
    end
    -- the handler owns the reply; an unknown column arrives as key == nil and is refused there
    pcall(r.handler, key, col)
end

-- a clock that moves within a frame (the two presses of one tap arrive in the same frame, so GetTime() alone would do too)
local clock = type(GetTimePreciseSec) == "function" and GetTimePreciseSec or GetTime

-- pad8: whether row `row` ends above the game's pop-up dialogs at the current layout (see ROWS PAST 37)
local function fits(row)
    local i = pad.info
    if not i then return false end
    return TOP_GAP + (row + 1) * CELL_H <= POPUP_TOP_UNITS * i.sy - POPUP_MARGIN
end
pad.fits = fits

-- a press of a plain cell, by a click or by the key channel: once per tap (REPEAT), a flash, the row's handler
-- pad23: the last presses, "row:col" (the row's name), newest last; read by Hub's document (rx) so the app can log where its taps landed
-- pad24: where the game sees the cursor now, in the pad's own game px (top-left, 0.1 px), or nil (read only; GetCursorPosition is in
-- screen units, UIParent's effective scale turns it into UI units, the layout's sx / sy into game px)
local function cursorPx()
    local i = pad.info
    if not i then return nil end
    local ok, x, y = pcall(GetCursorPosition)
    local okS, es = pcall(function() return UIParent:GetEffectiveScale() end)
    local function n(v) return type(v) == "number" and (type(WC.isPlain) ~= "function" or WC.isPlain(v)) and v == v and v or nil end
    x, y, es = ok and n(x) or nil, ok and n(y) or nil, okS and n(es) or nil
    if not x or not y or not es or es <= 0 then return nil end
    return math.floor(x / es * i.sx * 10 + 0.5) / 10, math.floor((i.ph - y / es * i.sy) * 10 + 0.5) / 10
end
pad.cursorPx = cursorPx

pad.rx = { n = 0, last = {}, at = {} }
local function landed(row, col)
    local r = pad.byRow[row]
    local L = pad.rx
    L.n = L.n + 1
    L.last[#L.last + 1] = tostring(r and r.name or row) .. ":" .. tostring(col)
    local x, y = cursorPx()                                       -- pad24: where the game saw this press ("-" = not readable)
    L.at[#L.at + 1] = x and (x .. "," .. y) or "-"
    if #L.last > 8 then table.remove(L.last, 1) end
    if #L.at > 8 then table.remove(L.at, 1) end
end
pad.landed = landed
function pad.rxDoc()
    local L = pad.rx
    if L.n == 0 then return nil end
    return { n = L.n, last = table.concat(L.last, " "), at = table.concat(L.at, " ") }
end

-- pad24 THE CALIBRATION STRIP (see THE STREAM'S TAPS MEASURED in the version note): a press on it only keeps where the game saw it
pad.cal = { n = 0, p = {}, btn = nil }
local function calPress()
    local c = pad.cal
    pad.pressT = clock()                                             -- pad25: our press: the cursor stays blank
    local x, y = cursorPx()
    if not x then return end
    local t = clock()
    -- the Thor's one tap arrives as two presses ms apart: the same spot within 0.1 s is the same press
    if c.lastAt and t - c.lastAt < 0.1 and c.lastY and math.abs(y - c.lastY) < 0.5 then return end
    c.lastAt, c.lastY = t, y
    c.n = c.n + 1
    c.p[#c.p + 1] = x .. "," .. y
    if #c.p > 4 then table.remove(c.p, 1) end
    -- the answer goes out at once: the feeds re-publish the grid (describe()'s `calib` changed), as on a new layout
    for _, fn in ipairs(pad.listeners) do pcall(fn) end
end
pad.calPress = calPress
-- the strip's box in game px: CAL_GAP left of the grid, from the first row's top to the bottom of the last row that fits this layout
local function calBox()
    local g = pad.geom
    if not g then return nil end
    local n = 0
    while n < ROWS_MAX and fits(n) do n = n + 1 end
    if n == 0 then return nil end
    return { x = g.x - CAL_GAP - CAL_W, y = g.y, w = CAL_W, h = n * CELL_H }
end
pad.calBox = calBox
local function placeCal()
    local i, b = pad.info, calBox()
    local c = pad.cal
    if not c.btn then
        if not b then return end
        c.btn = CreateFrame("Button", nil, UIParent)
        c.btn:SetFrameStrata("TOOLTIP")
        c.btn:EnableMouse(true)
        c.btn:RegisterForClicks("AnyDown")                 -- the press, as the plain cells
        c.btn:SetScript("OnClick", function() pcall(calPress) end)
    end
    if not b or not i then c.btn:Hide() return end
    c.btn:SetSize(b.w / i.sx, b.h / i.sy)
    c.btn:ClearAllPoints()
    c.btn:SetPoint("TOPLEFT", UIParent, "TOPLEFT", b.x / i.sx, -b.y / i.sy)
    c.btn:Show()
end

local function pressCell(btn, row, col, byKey)
    local t = clock()
    pad.pressT = t                                                   -- pad25: our press (also its second): the cursor stays blank
    -- the tap's second press (a click lands as a press AND its release); pad34: a key is ONE press (the dispatcher drops the
    -- release; keys can share a frame, so no time guard at all) - "ll" typed by keys is two letters
    if not byKey and btn.pressedAt and t - btn.pressedAt < REPEAT then return false end
    btn.pressedAt = t
    flash(btn)
    pcall(landed, row, col)
    fire(row, col)
    return true
end

local function makeRow(r)
    r.cells = r.cells or {}
    local ok = fits(r.row)
    for col = 0, r.n - 1 do
        local btn = r.cells[col]
        if not btn then
            btn = CreateFrame("Button", nil, UIParent)
            btn:SetFrameStrata("TOOLTIP")
            btn:EnableMouse(true)
            btn:RegisterForClicks("AnyDown")     -- the press, not the release: see "A PLAIN CELL FIRES ON THE PRESS"
            local row, c = r.row, col
            btn:SetScript("OnClick", function(self) pressCell(self, row, c) end)
            r.cells[col] = btn
        end
        place(btn, r.row, col)
        if ok then btn:Show() else btn:Hide() end      -- pad8: never inside a dialog
    end
end

-- pad19 (the user, 2026-11-13: "Bags share one row"): a row may be PINNED to the last row (ROWS_MAX - 1) instead of the next one, so
-- every row registered after it still takes the lowest free row and the pinned one is the row that drops first when a smaller UI scale
-- places fewer rows (Bags' shared drag row "bmv": at the smallest scale the drag row goes, never the rooms' or the radials' rows).
-- Rows keep their places as before; pad.nrows stays one past the highest row in use (the readers loop 0 .. nrows - 1, a gap is nil).
-- pad26: a ranked name takes its own row (ORDER); any other name the lowest free row (opts.last: ROWS_MAX - 1 first, as pad19)
local function newRow(name, last)
    local idx = SLOT[name]
    if idx == nil or idx >= ROWS_MAX or pad.byRow[idx] then
        idx = nil
        if last and not pad.byRow[ROWS_MAX - 1] then
            idx = ROWS_MAX - 1
        else
            -- first a free row no ranked name owns, then the lowest free row (the old rule: the next one)
            for i = 0, ROWS_MAX - 1 do
                if not pad.byRow[i] and ORDER[i + 1] == nil then idx = i break end
            end
            if idx == nil then
                for i = 0, ROWS_MAX - 1 do
                    if not pad.byRow[i] then idx = i break end
                end
            end
        end
        if idx == nil then return nil end
    end
    local r = { name = name, row = idx, cells = {} }
    pad.nrows = math.max(pad.nrows, idx + 1)
    pad.rows[name] = r
    pad.byRow[r.row] = r
    return r
end

-- pad21 THE SHARED ROW (the 1.0.32 test build, code 1472: with six bags, the cast bar and both radials all 56 rows are taken at the
-- Thor's UI scale, so the Macros room's lazy row "mac" had none and the room said "No pad row"). Two rooms that are never on the bottom
-- screen together may hold ONE row: a secure row registered with opts.share = <a secure row's name> is that row's GUEST - the same row
-- index, but its OWN cells, attributes and onClick (nothing of the host's is touched, so the host's own code - the Calendar's
-- syncCells - runs on its own cells as before). One of them is on the row at a time, the HOST by default: the other's cells are
-- hidden and the other is left out of describe(), so the app finds that row's name missing and never taps it there. pad.lease(name)
-- puts `name` on its row (out of combat: secure cells are shown / hidden only then; in a fight it waits for the fight's end, the last
-- ask winning) and tells every feed (onLayout) so each re-publishes its grid. Each room asks for its row when it comes on the screen,
-- by a tap on ANOTHER row (Book's padtab pick: 39 then 34 = the Macros room's, 39 then 35 = the Calendar's), so no tap is ever under
-- way on the row while its cells change. pad.nrows, pad.byRow (the host) and every other row are unchanged.
pad.tenant = {}          -- row index -> the GUEST on that shared row now (nil = its host)
pad.leaseWait = {}       -- row index -> a lease asked in a fight: the guest's name, or false = the host
local function onRow(r)
    local t = pad.tenant[r.row]
    if r.guestOf then return t == r.name end
    return t == nil
end
function pad.holds(name)
    local r = pad.rows[name]
    return type(r) == "table" and onRow(r)
end

-- Register a plain row. ns = the slot namespace its columns refer to, or nil for a single-cell
-- operation (column 0, no key). opts.last (pad19): pinned to the last row (see newRow).
function pad.op(name, ns, handler, opts)
    local r = pad.rows[name]
    if r then r.handler = handler return r.row end
    r = newRow(name, type(opts) == "table" and opts.last == true)
    if not r then return nil end
    r.ns, r.handler, r.n = ns, handler, ns and COLS or 1
    if pad.geom then makeRow(r) end
    if pad.keysSoon then pad.keysSoon() end          -- pad10: a new plain row may get a row key
    return r.row
end

-- pad30: a KEY-ONLY row: reached only by its far keys (KEY_FAR), never drawn, never laid on the pad, never clicked.
-- handler(col), col 0..ncols-1. Plain Lua (no game action of its own), the same in a fight.
pad.keyOnly = pad.keyOnly or {}
function pad.keyRow(name, ncols, handler)
    if type(name) ~= "string" or type(handler) ~= "function" then return false end
    pad.keyOnly[name] = { n = math.max(1, math.min(tonumber(ncols) or COLS, COLS)), handler = handler }
    if pad.keysSoon then pad.keysSoon() end
    return true
end

-- ---------------------------------------------------------------- secure rows

-- whether a secure cell has a secure action for this click: the template reads "type" with its modifier / button variants
local function hasAction(btn, button)
    local get = _G.SecureButton_GetModifiedAttribute
    if type(get) == "function" then
        local ok, v = pcall(get, btn, "type", button)
        if ok then return v ~= nil end
    end
    return btn:GetAttribute("type") ~= nil
end

local function secureCell(r, col)
    local btn = r.cells[col]
    if btn then return btn end
    -- pad27: NAMED, so a far key can be bound to the cell itself (SetOverrideBindingClick takes a name)
    local nm = ("WCPadSec_" .. tostring(r.name) .. "_" .. col):gsub("[^%w_]", "_")
    btn = CreateFrame("Button", nm, UIParent, "SecureActionButtonTemplate")
    btn:SetFrameStrata("TOOLTIP")
    -- MEASURED on this client (bags probe): a secure button registered for both fires its action
    -- exactly once per press; the template picks the phase from ActionButtonUseKeyDown.
    btn:RegisterForClicks("AnyDown", "AnyUp")
    local row, c = r, col
    -- A POST-hook, never SetScript: replacing OnClick would replace the secure action itself.
    btn:HookScript("OnClick", function(self, button, down)
        local early = row.onPress and not hasAction(self, button)       -- pad6b: no secure action -> the press, as a plain cell
        pad.pressT = clock()                                            -- pad25: our press (down and up): the cursor stays blank
        -- pad27: the far key's cell released: column keys back. Only a release whose PRESS came in this swap: the selector key's own
        -- release may arrive after the swap, on whatever its chord is bound to now, and must not end it
        local sw = pad.keys and pad.keys.swap
        if sw and sw.row == row.name then
            if down then sw.down[c] = true
            elseif sw.down[c] then C_Timer.After(0, function() pcall(pad.keyUnswap) end) end
        end
        if down then
            flash(self)
            if not early then return end
            local t = clock()
            if self.pressedAt and t - self.pressedAt < REPEAT then return end   -- the tap's second press
            self.pressedAt = t
        elseif early then
            return                                                      -- it ran on the press
        end
        pcall(landed, row.row, c)                                         -- pad23: once per tap, as the plain cells
        if type(row.onClick) == "function" then pcall(row.onClick, c) end   -- once per tap
    end)
    r.cells[col] = btn
    return btn
end

-- Build or re-place every secure row. Out of combat only; in combat it is queued.
function pad.buildSecure()
    if not pad.geom then return false end
    if InCombatLockdown() then pad.securePending = true return false end
    -- pad21: a lease asked in a fight, now (the last ask won)
    for idx, want in pairs(pad.leaseWait) do pad.tenant[idx] = want or nil; pad.leaseWait[idx] = nil end
    for _, r in pairs(pad.rows) do
        if r.secure then
            local ok = fits(r.row) and onRow(r)            -- pad21: a shared row's other tenant stays hidden
            for col = 0, r.n - 1 do
                local btn = secureCell(r, col)
                if not r.built and type(r.init) == "function" then pcall(r.init, btn, col) end
                btn:EnableMouse(true)
                place(btn, r.row, col)
                if ok then btn:Show() else btn:Hide() end  -- pad8: never inside a dialog
            end
            -- a row that shrank (a smaller bag): nothing may sit under a stale tap
            for col, btn in pairs(r.cells) do
                if col >= r.n then btn:Hide() end
            end
            r.built = true
        end
    end
    pad.secureAt = geomKey()
    pad.securePending = false
    if pad.keysFarRefresh then pcall(pad.keysFarRefresh) end   -- pad28: the key router follows the secure rows
    return true
end

-- Register or rebuild a secure row: ncols cells, attributes set once by init(button, col).
-- Calling it again (a bag changed size) re-runs init on every cell, out of combat.
-- onClick(col), optional, runs after the secure action, once per tap.
-- opts.onPress (pad6b): cells with no secure action ("type" nil) run onClick on the press instead of the release.
-- opts.share (pad21): the name of a secure row to be the GUEST of (THE SHARED ROW, above): its row, its own cells, off the row until
-- pad.lease(name); with no such host (its add-on off, or not registered), a row of its own as before.
function pad.secureRow(name, ncols, init, onClick, opts)
    local r = pad.rows[name]
    if r and not r.secure then return nil end        -- the name is taken by a plain row
    if not r then
        local host = type(opts) == "table" and type(opts.share) == "string" and pad.rows[opts.share] or nil
        if type(host) == "table" and host.secure and not host.guestOf and host.name ~= name then
            r = { name = name, row = host.row, cells = {}, guestOf = host.name }
            pad.rows[name] = r
        else
            r = newRow(name)
            if not r then return nil end
        end
        r.secure = true
    end
    r.n = math.max(0, math.min(ncols or 0, COLS))
    r.init, r.onClick, r.built = init, onClick, false
    r.onPress = type(opts) == "table" and opts.onPress == true
    pad.buildSecure()
    return r.row
end

-- pad21: put [name] on its shared row (a guest, or its host back). true = it is on the row now; false, "combat" = it waits for the
-- fight's end (the cells are secure); false, "no row" = no such secure row. A row that is not shared: always on its row.
function pad.lease(name)
    local r = pad.rows[name]
    if type(r) ~= "table" or not r.secure then return false, "no row" end
    local want = r.guestOf and r.name or nil
    if pad.tenant[r.row] == want then pad.leaseWait[r.row] = nil return true end
    if InCombatLockdown() then pad.leaseWait[r.row] = want or false; pad.securePending = true return false, "combat" end
    pad.tenant[r.row] = want
    pad.leaseWait[r.row] = nil
    pad.buildSecure()
    for _, fn in ipairs(pad.listeners) do pcall(fn) end
    return true
end

-- ---------------------------------------------------------------- THE KEY CHANNEL (L1, pad10c)
-- The user's pick 2026-10-09 ("L1 key channel", via Home): an action goes out at the controller PRESS, not its release. WHY (Home's
-- lat.log): press -> tap reaching the game p50 196 ms / p90 358 ms, nearly all of it the app waiting for the face button's RELEASE,
-- because a click while a face button is held strays to the freelook park point (TapQuiet). A key binding never meets the cursor.
-- So, INSIDE THE DS FOREVER LAUNCHER (its X server carries the modifiers; adb's keys lost them, Bags 2026-09-27), a plain cell can
-- also be pressed by TWO KEYS, both on CTRL-SHIFT:
--   a ROW key (KEY_ROWS), the cell's row -- a NO-ACTION pick (the user's lock, amended 2026-09-28: a no-action pick may come before
--     the action), one-shot, gone after KEY_PICK_TTL;
--   then a COLUMN key (KEY_COLS: A..Z, 0..9, MINUS, EQUALS, [, ] = the 40 columns), which presses that cell exactly as a click does
--     (pressCell: the same REPEAT guard, the same handler and reply). A column key with no pending row is REFUSED (reported as a
--     "padkey" document), never a guess: a lost row key can never press a wrong cell; a lost column key lets the pick expire.
-- NO ALT, NO F-KEY, NO SYSTEM KEY, EVER (pad10c). pad10 held Ctrl+Alt+Shift, and its row key for Interact's row was F4: Ctrl+Alt+Shift+F4
-- CONTAINS ALT+F4, which Wine turns into the window's close -- the game closed seconds after every world entry (2026-10-09 13:50,
-- 14:03, 14:04; the user's probe). A real Alt makes Wine handle any key as a SYSTEM key (WM_SYSKEYDOWN: Alt+F4 close, Alt+Space the
-- system menu, Alt+Tab / Esc / Enter), and F10 / Shift+F10 are system keys without it. So: the chords are CTRL-SHIFT only -- the
-- gamepad's own emulated modifiers (LB = Ctrl, LT = Shift; Home's read of the game log), so a held LB / LT never changes the chord --
-- and keySafe() refuses any other chord before it is bound or published, whatever the alphabets grow to (tested against an
-- independent list of system chords). An emulated ALT (GamePadEmulateAlt set to a button) only exists inside the game, never as a
-- key we send: for it each key is ALSO bound as ALT-CTRL-SHIFT-<key> to the same dispatcher, so a held emulated Alt cannot lose it.
-- ONE plain dispatcher button holds every binding, the key's own name riding along as the click's "button" (Interact's padSink trick).
-- Bindings are set once, OUT of combat, on our own owner frame, never taking a key the player or another add-on already uses
-- (GetBindingAction); describe() publishes which rows have keys and the column keys, so the app never guesses, and the app keeps
-- clicking for everything else (and while a text box has keyboard focus: bindings do not fire there). Only the hot rows (Home's
-- lat.log order) and this file's own "keytest" row are keyed, each by NAME. Secure rows are not keyed (phase 2).
-- THE SWEEP (pad10c; before keys go live, on the user's word): a CLICK on cell 0 of the plain row "keytest" (its handler does nothing
-- in the game) turns a trace on for KEY_TRACE_S; while it is on, every key the dispatcher hears is reported ("padkeytest": k, the row
-- or column it means, or why it was refused). The app then sends each row key ALONE (a pick that just expires) and keytest's row key
-- with each column key (keytest's cells: no action), so every key is checked once with no game action, and a lost key -- or a key
-- with a side effect -- shows on its own.
-- A KEY MUST NEVER BE SENT UNBOUND (pad10c): when a chord with modifiers has no binding, WoW falls back to the key's PLAIN binding
-- (that is how Shift+1 fires action button 1 for a [mod:shift] macro), so a CTRL-SHIFT-1 nobody bound is the player's "1": a spell. A
-- pad document the app kept from an earlier session (it replays the last one at its start) or from an add-on since rolled back must
-- never make the app send keys. So the keys carry this session's token (describe().keys.s), and the app sends keys only after a
-- HANDSHAKE in this session: its CLICK on keytest's cell 0 (no game action) is answered "padkeytest" { on, s, bound, ... }, and only a
-- live answer whose token matches the document's lets keys go.
local KEY_MOD_NAMES = "CTRL-SHIFT"           -- the game's order for a chord without Alt
local KEY_MODS = KEY_MOD_NAMES .. "-"
local KEY_ROWS = { "INSERT", "HOME", "END", "PAGEUP", "PAGEDOWN", "UP", "DOWN", "LEFT", "RIGHT" }
local KEY_SPARE = { "keytest" }
-- Linux Streaming Edition (2026-11-18, Thor test: the minimap toggle still clicked): no row key is left, so a row key pressed TWICE picks a
-- second row ("page 2"): CTRL-SHIFT RIGHT, RIGHT, column = the "ui" row (layout: minimap, chat, tracker). Both presses come in one line.
-- pad26 (2026-11-20, the user: "selling does not work", Sell junk did): the vendor's per-item Sell (isell) had no key, so every sell
-- went as a click and landed on the parked cursor (padstray). UP UP = isell (UP alone = pause). DOWN is the one double left.
local KEY_PAGE2 = { RIGHT = "ui", LEFT = "lay", UP = "isell", DOWN = "~far" }
-- pad27 THE FAR ROWS (2026-11-20, the user: "using items from bags does not work", and vendor Buy; every row key and double was taken):
-- DOWN DOWN (DOWN alone = spick) opens a FAR pick, and the NEXT key, a column key, is the SELECTOR: KEY_FAR's n-th name (0-based, the
-- column key of n). Published as "DOWN DOWN <selector>"; the column key after it is the cell, as for any row.
--  * a PLAIN far row (ibuy, iqty, keytest) then takes its column key through the dispatcher, exactly as a keyed row;
--  * a SECURE far row (the bags: SecureActionButton cells that /use an item) cannot be pressed from Lua. Out of combat the selector
--    REBINDS the column keys (the same override chords on our own owner) straight onto that row's NAMED secure cells ("CLICK cell:
--    LeftButton", the game's own secure click, as a mouse click on the cell), so the column key presses the cell itself; the column
--    keys go back to the dispatcher at that cell's release, after KEY_SWAP_S at the latest, and at PLAYER_REGEN_DISABLED (before the
--    lockdown). In a fight a secure far pick is refused ("combat"; the bags clear their use cells for the fight anyway).
--  Columns 36-39 (KEY_COLX, navigation keys read by the dispatcher) cannot be rebound: the app clicks those cells of a far row.
-- pad29 (2026-11-21, the user: "picking an item in a bag has some delay"; the Thor's log: bmvq / bagsort / bmv "a cell without keys",
-- spaced 370 ms as clicks): Bags' plain pick rows are far rows too (selectors K, L, M), so a finger on a slot goes as keys.
-- pad30 (2026-11-21, the user: "we want as few automated clicks as possible, to not be flagged for botting"): KEY-ONLY rows
-- (pad.keyRow: no cells, no place on the pad, a handler only) as far rows too: Bags' bcur0..bcur5 (selectors N..S) move the
-- controller's cursor to a slot in ONE step (was bmvq 36 + bagsort + bmv: three steps, 12 keys). Keys only: no click can reach them.
local KEY_FAR = { "ibuy", "iqty", "keytest", "bag0", "bag1", "bag2", "bag3", "bag4", "bag5", "binv", "bmvq", "bagsort", "bmv",
                  "bcur0", "bcur1", "bcur2", "bcur3", "bcur4", "bcur5", "idlg", "aurapick", "talents", "talentn", "chq", "chr", "chs",
                  "extra", "castbar", "ahr" }
-- pad35d (2026-11-23, the AH remote, Interact i186): the auction house's buttons and result lines (secure "click" cells, the Calendar
-- row's guest) are a secure far row too (selector 2); none of their targets reads a modifier.
-- pad35c (2026-11-23, the user: food on the tap-to-cast bar "inconsistent"; the game's padrx: the bar's clicks for slots 3 / 4
-- never arrived): the tap-to-cast bar (ActionBar's secure row "castbar") is a secure far row as the bags are (selector 1): the
-- press copies the cell's type / spell / item / macrotext onto the proxy (COL_SNIP) and casts it itself, in fights too.
-- pad35b (2026-11-23, the user: "clicking around" picking the hearthstone for the tap-to-cast bar; the log: padtab 6 + extra 35
-- went as clicks, "a cell without keys"): the Controller room's Extra / chooser row is a far row too (selector 0). Its handler
-- (PadTabCtl touchExtra) reads no modifier.
-- pad33 (2026-11-21, the user: "the Auction House is very hard to use"; the log: every letter typed into its search box went as a
-- CLICK on the chat rows - chq's row key PAGEDOWN is bound in the live game, chr / chs never had one): the chat rows are far rows
-- (selectors X, Y, Z). The add-on builds the text itself, so the held CTRL-SHIFT means nothing to them. A row that has its own row key
-- keeps it (the far entry is then unused).
-- pad32 (2026-11-21, the user's play log: aurapick x8, talentn x8, talents x1 went as clicks, "a cell without keys"): the Auras pick
-- and the Talents rows are plain rows, now far rows too (selectors U, V, W). Their handlers read no modifier.
-- pad31 (2026-11-21, the user: as few automated clicks as possible; the log: every Bags entry clicked bag0:39, every room switch
-- idlg:25 up to three times): a SECURE far row's "click" cells (the backpack doors, the dialogs' leave / trade / charter buttons) by
-- keys too, columns 36-39 included. The proxy gets the cell's own target, mirrored out of combat ("*clickbutton-wcc_<row>"; the
-- restricted code cannot copy a frame), and the snippet returns "wcc_<row>": the proxy clicks that target itself, as the cell would.
local KEY_SWAP_S = 1.0
-- Linux Streaming Edition (2026-11-18, the 1.0.34 merge: Edit layout, the meters, Buffs / XP bar went as clicks and strayed): secure rows
-- whose cells carry NO secure action (init sets nothing; the press only runs the row's own Lua onClick), so a key may press them as a
-- click on the cell would: only while the row is on its (shared) row, never a cell with an action, the same once-per-tap guard
local KEY_SECURE_PLAIN = { lay = true }
-- Linux Streaming Edition (2026-11-18, Thor trace: LEFT LEFT arrived, the column "[" never did; the letters always do): the punctuation
-- columns 36-39 (MINUS EQUALS [ ]) depend on the keyboard layout (Swedish here), so they go as navigation row keys instead. A row key
-- arriving while a pick is fresh (within KEY_PAGE2_GAP) is that column; RIGHT / LEFT (the page-2 keys) are never columns.
local KEY_COLX = { INSERT = 36, HOME = 37, END = 38, PAGEUP = 39 }
local KEY_PAGE2_GAP = 0.3   -- Linux Streaming Edition: rows that take a secure row's unused key (see the keyed rows below)
local KEY_HOT = { "qact", "qpick", "ipick", "iact", "chq", "pause", "spick", "padtab", "uisw" }   -- Linux Streaming Edition 11-18: uisw takes keytest's RIGHT (PAGEDOWN is bound in the live game)   -- = KEY_ROWS, by name
local KEY_COLS = { "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V",
                   "W", "X", "Y", "Z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "MINUS", "EQUALS", "[", "]" }
-- keys that mean something to Windows, Wine, the launcher or the controller: never bound, never published
local KEY_NEVER = { ESCAPE = true, TAB = true, ENTER = true, SPACE = true, BACKSPACE = true, DELETE = true, PRINTSCREEN = true,
                    SCROLLLOCK = true, PAUSE = true, NUMLOCK = true, CAPSLOCK = true, LWIN = true, RWIN = true, APPS = true,
                    MENU = true, LALT = true, RALT = true, LCTRL = true, RCTRL = true, LSHIFT = true, RSHIFT = true }
local KEY_PICK_TTL = 0.5                     -- seconds a row key waits for its column key
-- pad34 (2026-11-21, the user: "yes, do the fewer keys per word change"; "as few automated inputs as possible"): the TYPING rows stay
-- picked after a column (KEY_STICKY_TTL s from the last one), so the next letter on the same row is its column key alone - a word is
-- the row's keys once, then one key per letter. Only plain column keys continue it: ANY row key ends it (also the navigation keys of
-- columns 36-39: in this mode they are always row keys, so an action right after typing is never read as a letter). Published as
-- keys.sticky; the app leaves the row keys out only while it knows the row is still picked.
local KEY_STICKY = { chq = true, chr = true, chs = true }
local KEY_STICKY_TTL = 2.0
local KEY_TRACE_S = 30                       -- seconds the sweep's trace stays on
local KEY_BTN = "WowCompanionPadKeys"
local keys = { rowOf = {}, keyOf = {}, colOf = {}, colKey = {}, usedRow = {}, pending = nil, bound = false, wantBind = false,
               queued = false, given = 0, n = 0, bad = 0, badAt = -1, traceUntil = -1, session = nil }
pad.keys = keys                              -- for the harness

-- the chord we SEND (mods + key) means nothing to the system: no Alt / Meta, no F-key, no system or controller key
local function keySafe(mods, k)
    if type(mods) ~= "string" or type(k) ~= "string" or k == "" then return false end
    if mods:find("ALT", 1, true) or mods:find("META", 1, true) then return false end
    if KEY_NEVER[k] or k:match("^F%d+$") or k:match("^NUMPAD") or k:match("^PAD") or k:match("BUTTON") then return false end
    return true
end
pad.keySafe = keySafe                        -- for the harness

local function tracing() return GetTime() <= keys.traceUntil end
local function trace(doc)
    doc.type, doc.v = "padkeytest", PADV
    pcall(function() WC.send(WC.encode(doc)); if type(WC.pushThrottled) == "function" then WC.pushThrottled() else WC.push() end end)
end

local function keyBad(why, what)
    keys.bad = keys.bad + 1
    if tracing() then trace({ k = what, err = why }) end
    local t = GetTime()
    if t - keys.badAt < 1 then return end    -- rate-capped, as padstray
    keys.badAt = t
    pcall(WC.emit, { type = "padkey", err = why, k = what, bad = keys.bad, n = keys.n, v = PADV })
end

local function onKey(_, button, down)
    if down == false then return end
    if button == "wcsel" then                                      -- pad28: the router took a secure far row's selector
        keys.pending = nil
        if tracing() then trace({ k = "wcsel", row = "~router" }) end
        return
    end
    local k = type(button) == "string" and button or nil
    local t = clock()
    local rname = k and keys.rowOf[k]
    local colx = k and KEY_COLX[k]
    if rname and colx and keys.pending and not keys.pending.sticky and t - keys.pending.at <= KEY_PAGE2_GAP then rname = nil end   -- a column (above)
    if rname then
        local p2 = KEY_PAGE2[k]
        local pp = keys.pending
        if p2 == "~far" and pp and pp.k == k and not pp.page2 and t - pp.at <= KEY_PAGE2_GAP then
            keys.pending = { far = true, at = t, k = k, page2 = true }
            if tracing() then trace({ k = k, row = "~far" }) end
            return
        end
        if p2 and p2 ~= "~far" and pp and pp.k == k and not pp.page2 and t - pp.at <= KEY_PAGE2_GAP and pad.rows[p2] and (not pad.rows[p2].secure or KEY_SECURE_PLAIN[p2]) then
            keys.pending = { name = p2, at = t, k = k, page2 = true }
            if tracing() then trace({ k = k, row = p2 }) end
            return
        end
        keys.pending = { name = rname, at = t, k = k }
        if tracing() then trace({ k = k, row = rname }) end
        return
    end
    local col = k and (keys.colOf[k] or colx)
    local p = keys.pending
    keys.pending = nil
    if col == nil then return keyBad("unknown key", k) end
    if not p or t - p.at > (p.sticky and KEY_STICKY_TTL or KEY_PICK_TTL) then return keyBad("no row", k) end
    if p.far then                                                    -- pad27: this column key is the far row's SELECTOR
        local fname = KEY_FAR[col + 1]
        local ko = fname and pad.keyOnly[fname]
        if ko then                                                   -- pad30: a key-only row
            keys.pending = { name = fname, at = t, k = k, keyOnly = true }
            if tracing() then trace({ k = k, row = fname }) end
            return
        end
        local fr = fname and pad.rows[fname]
        if not fr or keys.keyOf[fname] then return keyBad("no far row", tostring(fname or col)) end
        if fr.secure then
            local ok, why = pad.keySwap(fr)
            if not ok then return keyBad(why or "swap", fname) end
            if tracing() then trace({ k = k, row = fname, swap = true }) end
            return
        end
        keys.pending = { name = fname, at = t, k = k }
        if tracing() then trace({ k = k, row = fname }) end
        return
    end
    if p.keyOnly then                                                -- pad30: the key-only row's column
        local ko = pad.keyOnly[p.name]
        if not ko or col >= ko.n then return keyBad("no cell", p.name .. ":" .. col) end
        keys.n = keys.n + 1
        if tracing() then trace({ k = k, row = p.name, col = col }) end
        pcall(ko.handler, col)
        return
    end
    local r = pad.rows[p.name]
    if r and r.secure then
        if not KEY_SECURE_PLAIN[p.name] then return keyBad("secure row", p.name) end
        if not onRow(r) then return keyBad("row not held", p.name) end
        local sb = col < (r.n or 0) and r.cells and r.cells[col]
        if not sb or type(r.onClick) ~= "function" then return keyBad("no cell", p.name .. ":" .. col) end
        if hasAction(sb, "LeftButton") then return keyBad("secure action", p.name .. ":" .. col) end
        local ts = clock()
        if sb.pressedAt and ts - sb.pressedAt < REPEAT then return end
        sb.pressedAt = ts
        flash(sb)
        keys.n = keys.n + 1
        if tracing() then trace({ k = k, row = p.name, col = col }) end
        pcall(r.onClick, col)
        return
    end
    local btn = r and not r.secure and r.cells and r.cells[col]
    if not btn then return keyBad("no cell", p.name .. ":" .. col) end
    keys.n = keys.n + 1
    if tracing() then trace({ k = k, row = p.name, col = col }) end
    pressCell(btn, r.row, col, true)
    if KEY_STICKY[p.name] then keys.pending = { name = p.name, at = t, k = k, sticky = true } end   -- pad34
end

local function bindingOf(chord)
    local ok, a = pcall(GetBindingAction, chord, true)
    if not ok then return nil end
    return a or ""
end
-- pad28 THE SECURE KEY ROUTER (beta 2026-11-20, the user: bag items by keys in fights too). Every key of ours is bound to its own
-- SecureActionButton PROXY ("WCPadKeyP_<key>", type "click"), never to the plain dispatcher: the proxy clicks the dispatcher
-- (KEY_DISP, a plain button: the same onKey as before, the key's name riding along as the button), so plain rows work exactly as they
-- did. Its wrap snippet (the restricted environment: it runs in fights too) also follows the FAR pick: DOWN DOWN counts on the header,
-- the selector of a SECURE far row (the bags) is swallowed and remembered ("sel"), and the next column key's proxy DOES that row's
-- cell's action itself: the snippet copies the cell's type / item / macrotext / spell / unit (frame refs "c_<row>_<col>", set out of
-- combat) onto the proxy's "wcsec" button and returns that button. So the action fires on the real key press (no dependence on what
-- a click delegate's Click() passes), and a hook runs the row's own tap work (the bags' proof). No rebinding at a press any more, so
-- the bags work in a fight as out of one. Any row key clears a stale pick.
local KEY_DISP = "WowCompanionPadKeyDisp"
local function proxyName(k) return "WCPadKeyP_" .. k end
local function ours(k) return "CLICK " .. proxyName(k) .. ":" .. k end
-- an emulated Alt exists only inside the game (a gamepad button set as GamePadEmulateAlt)
local function emuAlt()
    local ok, v = pcall(GetCVar, "GamePadEmulateAlt")
    return ok and type(v) == "string" and v ~= "" and v ~= "none"
end
-- the key is free for us: safe to send, and nothing bound to its chord, or it is already ours
local function keyFree(k)
    if not keySafe(KEY_MOD_NAMES, k) then return false end
    local a = bindingOf(KEY_MODS .. k)
    return a == "" or a == ours(k) or a == "CLICK " .. KEY_BTN .. ":" .. k
end
-- the proxy of key [k] (made once, out of combat): [col] = its column for a column key, nil for a row key
-- (2026-11-21: NO clock in these snippets - WoW Forever's restricted environment has no GetTime ("attempt to call a nil value" on
-- every key, the UI froze). Any row key resets the DOWN count and the pick, and a column key spends both, so a stale one lives only
-- until the next key of ours.)
local ROW_SNIP = [[
    local d = 0
    if "%s" == "DOWN" then
        d = owner:GetAttribute("downs") or 0
        if d ~= 1 then d = 0 end
        d = d + 1
    end
    owner:SetAttribute("downs", d)
    owner:SetAttribute("sel", nil)
]]
local COL_SNIP = [[
    local sel = owner:GetAttribute("sel")
    local downs = owner:GetAttribute("downs") or 0
    owner:SetAttribute("downs", 0)
    if sel then
        owner:SetAttribute("sel", nil)
        if not owner:GetAttribute("on_" .. sel) then return false end
        if %d >= (owner:GetAttribute("n_" .. sel) or 0) then return false end
        local t = owner:GetFrameRef("c_" .. sel .. "_%d")
        if not t then return false end
        local ty = t:GetAttribute("type")
        if not ty then return false end
        if ty == "click" then                                     -- pad31: the cell's target, mirrored onto this proxy
            if not self:GetAttribute("wcok_" .. sel) then return false end
            self:SetAttribute("wcrow", sel)
            self:SetAttribute("wcn", (self:GetAttribute("wcn") or 0) + 1)
            return "wcc_" .. sel
        end
        -- "*": the game looks up <modifiers><name><suffix> first, and CTRL-SHIFT is held for every key of ours (the review)
        self:SetAttribute("*type-wcsec", ty)
        self:SetAttribute("*item-wcsec", t:GetAttribute("item"))
        self:SetAttribute("*macrotext-wcsec", t:GetAttribute("macrotext"))
        self:SetAttribute("*spell-wcsec", t:GetAttribute("spell"))
        self:SetAttribute("*unit-wcsec", t:GetAttribute("unit"))
        self:SetAttribute("wcrow", sel)
        self:SetAttribute("wcn", (self:GetAttribute("wcn") or 0) + 1)   -- the hook's signal (hooks see the ORIGINAL button)
        return "wcsec"
    end
    if downs == 2 then
        local fs = owner:GetAttribute("far%d")
        if fs then owner:SetAttribute("sel", fs); return "wcsel" end      -- the dispatcher hears it as "wcsel": its far pick is spent
    end
]]
-- pad31: columns 36-39 of a secure far row: their keys are ROW keys (KEY_COLX), so their snippet first looks for a pending pick;
-- only "click" cells (the doors, the dialogs' buttons) are done this way; anything else falls through as the plain row key (it
-- clears the pick: a lost column never eats the next action)
local COLX_SNIP = [[
    local sel = owner:GetAttribute("sel")
    local t = sel and owner:GetAttribute("on_" .. sel) and %d < (owner:GetAttribute("n_" .. sel) or 0) and owner:GetFrameRef("c_" .. sel .. "_%d")
    if t and t:GetAttribute("type") == "click" and self:GetAttribute("wcok_" .. sel) then
        owner:SetAttribute("sel", nil)
        owner:SetAttribute("downs", 0)
        self:SetAttribute("wcrow", sel)
        self:SetAttribute("wcn", (self:GetAttribute("wcn") or 0) + 1)
        return "wcc_" .. sel
    end
]]
-- pad31b (the review, 2026-11-21): a "click" cell is done by keys only where its TARGET ignores modifiers - every key of ours holds
-- CTRL-SHIFT, and a click delegated inside the key press sees them. The dialogs' cells (StaticPopup / trade / charter buttons, the
-- per-window leaves -> Interact's secure leave -> the window's close) do; the backpack door does NOT (BagSlotOnClick: with a
-- modifier held it runs IsModifiedClick("OPENALLBAGS") instead of ToggleBag), so bag0's doors stay clicks. Rows listed here only.
local KEY_SFX = { idlg = true }
local function proxyFor(k, col)
    keys.proxy = keys.proxy or {}
    local p = keys.proxy[k]
    if p then return p end
    if InCombatLockdown() or not keys.hdr or not keys.disp then return nil end
    local ok = pcall(function()
        p = CreateFrame("Button", proxyName(k), UIParent, "SecureActionButtonTemplate")
        p:RegisterForClicks("AnyDown")
        -- the proxy hears the PRESS only, so it must act on it whatever the player's "cast on key down" setting (SecureActionButton_
        -- ShouldUseOnKeyDown reads this attribute before the setting): else, with the setting off, no key of ours would do anything
        p:SetAttribute("useOnKeyDown", true)
        p:SetAttribute("type", "click")
        p:SetAttribute("clickbutton", keys.disp)
        local cx = KEY_COLX[k]
        local body = col and COL_SNIP:format(col, col, col) or ((cx and COLX_SNIP:format(cx, cx) or "") .. ROW_SNIP:format(k))
        SecureHandlerWrapScript(p, "OnClick", keys.hdr, body)
        -- the press used a far row's cell (button "wcsec"): that row's own once-per-tap work, as a click on the cell would run it
        -- (the bags' "bagsTap" proof); the secure action itself already ran on this proxy (a real key press: on its down edge)
        local hc = col or KEY_COLX[k]
        if hc then
            local col = hc
            p:HookScript("OnClick", function(self)
                local n = self:GetAttribute("wcn")              -- bumped by the snippet when it did a far cell's action
                if n == nil or n == self.wcSeen then return end
                self.wcSeen = n
                local rn = self:GetAttribute("wcrow")
                local r = rn and pad.rows[rn]
                pad.pressT = clock()
                if r then pcall(landed, r.row, col); if type(r.onClick) == "function" then pcall(r.onClick, col) end end
            end)
        end
    end)
    if not ok or not p then return nil end
    keys.proxy[k] = p
    return p
end
local function keyBind(k, col)
    local target = KEY_BTN
    if proxyFor(k, col ~= nil and col or keys.colOf[k]) then target = proxyName(k) end
    if not pcall(SetOverrideBindingClick, keys.owner, true, KEY_MODS .. k, target, k) then return false end
    local want = "CLICK " .. target .. ":" .. k
    if bindingOf(KEY_MODS .. k) ~= want then return false end
    -- the emulated Alt's mirror: a binding only (we never send Alt), and only on a free chord
    if emuAlt() then
        local alt = "ALT-" .. KEY_MODS .. k
        local a = bindingOf(alt)
        if a == "" or a == ours(k) or a == "CLICK " .. KEY_BTN .. ":" .. k then pcall(SetOverrideBindingClick, keys.owner, true, alt, target, k) end
    end
    return true
end
local function giveRow(name, k)
    if keys.keyOf[name] or keys.usedRow[k] then return end
    if keyFree(k) and keyBind(k) then keys.keyOf[name], keys.rowOf[k], keys.usedRow[k] = k, name, true; keys.given = keys.given + 1 end
end

local function keyDownActs()
    local ok, v = pcall(GetCVarBool, "ActionButtonUseKeyDown")
    if ok and v ~= nil then return v == true end
    ok, v = pcall(GetCVar, "ActionButtonUseKeyDown")
    return not (ok and (v == "0" or v == 0))                        -- unreadable: the game's default (on the press)
end
-- pad27: the secure far row's swap (THE FAR ROWS, above). keys.swap = { row, at } while the column keys point at its cells.
function pad.keyUnswap()
    local sw = keys.swap
    if not sw then return true end
    if InCombatLockdown() then return false end
    for _, k in pairs(keys.colKey) do keyBind(k) end
    keys.swap = nil
    return true
end
function pad.keySwap(r)
    if InCombatLockdown() then return false, "combat" end
    if not keyDownActs() then return false, "key up acts" end
    if not (fits(r.row) and onRow(r)) then return false, "row not held" end
    pad.keyUnswap()
    local alt = emuAlt()
    local n = 0
    for col, k in pairs(keys.colKey) do
        local sb = col < (r.n or 0) and r.cells and r.cells[col]
        local nm = sb and sb.GetName and sb:GetName()
        if nm and pcall(SetOverrideBindingClick, keys.owner, true, KEY_MODS .. k, nm, "LeftButton") then
            n = n + 1
            if alt and bindingOf("ALT-" .. KEY_MODS .. k) == ours(k) then
                pcall(SetOverrideBindingClick, keys.owner, true, "ALT-" .. KEY_MODS .. k, nm, "LeftButton")
            end
        end
    end
    if n == 0 then return false, "no cell" end
    local at = clock()
    keys.swap = { row = r.name, at = at, down = {} }
    keys.swaps = (keys.swaps or 0) + 1
    C_Timer.After(KEY_SWAP_S, function() if keys.swap and keys.swap.at == at then pcall(pad.keyUnswap) end end)
    return true
end

-- pad28: what the router knows of the secure far rows (out of combat: a header's attributes and frame refs are set only then): far<col>
-- = the row at that selector, on_<row> = it holds its pad row, n_<row> = its cell count, c_<row>_<col> = the cell. Run after every
-- secure build (pad.buildSecure) and every key bind.
-- pad31: the proxy of column [c] gets cell [cell]'s click target (out of combat), and the cell tells us when its target or type
-- changes (OnAttributeChanged, hooked once): Interact / the doors re-aim their cells only out of combat, as the mirror does
local COLX_KEY = {}
for k, c in pairs(KEY_COLX) do COLX_KEY[c] = k end
function pad.keysMirror(name, c, cell)
    if InCombatLockdown() or not keys.proxy or type(cell) ~= "table" or not KEY_SFX[name] then return end
    local k = (c < 36) and keys.colKey[c] or COLX_KEY[c]
    local p = k and keys.proxy[k]
    if not p then return end
    local ty = cell:GetAttribute("type")
    local tg = ty == "click" and cell:GetAttribute("clickbutton") or nil
    if type(tg) ~= "table" then tg = nil end
    pcall(p.SetAttribute, p, "*type-wcc_" .. name, tg and "click" or nil)
    pcall(p.SetAttribute, p, "*clickbutton-wcc_" .. name, tg)
    pcall(p.SetAttribute, p, "wcok_" .. name, tg and true or nil)
    if not cell.wcMirror then
        cell.wcMirror = true
        pcall(cell.HookScript, cell, "OnAttributeChanged", function(self, an)
            if an == "type" or an == "clickbutton" then pcall(pad.keysMirror, name, c, self) end
        end)
    end
end
function pad.keysFarRefresh()
    if not keys.hdr or InCombatLockdown() or type(SecureHandlerSetFrameRef) ~= "function" then return false end
    for i, name in ipairs(KEY_FAR) do
        local r, col = pad.rows[name], i - 1
        local sec = r and r.secure and not keys.keyOf[name] and true or false
        pcall(keys.hdr.SetAttribute, keys.hdr, "far" .. col, sec and name or nil)
        if sec then
            pcall(keys.hdr.SetAttribute, keys.hdr, "on_" .. name, (fits(r.row) and onRow(r)) and true or nil)
            pcall(keys.hdr.SetAttribute, keys.hdr, "n_" .. name, math.min(r.n or 0, COLS))
            for c, cell in pairs(r.cells or {}) do
                if c < COLS and c < (r.n or 0) then
                    pcall(SecureHandlerSetFrameRef, keys.hdr, "c_" .. name .. "_" .. c, cell)
                    pad.keysMirror(name, c, cell)
                end
            end
        end
    end
    return true
end

-- bind what is not bound yet: the 40 column keys once, then each keyed row's own key (out of combat only)
function pad.bindKeys()
    if type(SetOverrideBindingClick) ~= "function" or type(GetBindingAction) ~= "function" then return false end
    if InCombatLockdown() then keys.wantBind = true; return false end
    keys.wantBind = false
    if not keys.btn then
        local ok = pcall(function()
            keys.btn = CreateFrame("Button", KEY_BTN, UIParent)
            keys.btn:RegisterForClicks("AnyDown")
            keys.btn:SetScript("OnClick", onKey)
            keys.owner = CreateFrame("Frame", "WowCompanionPadKeyOwner", UIParent)
        end)
        if not ok or not keys.btn or not keys.owner then keys.btn = nil; return false end
        -- pad28: the router's header and the dispatcher its proxies click (every click = a press: the proxy acts on the press)
        pcall(function()
            keys.hdr = CreateFrame("Frame", "WowCompanionPadKeyHdr", UIParent, "SecureHandlerBaseTemplate")
            keys.disp = CreateFrame("Button", KEY_DISP, UIParent)
            keys.disp:RegisterForClicks("AnyDown", "AnyUp")
            keys.disp:SetScript("OnClick", function(self, button) onKey(self, button, true) end)
        end)
        if not (keys.hdr and keys.disp) then keys.hdr, keys.disp = nil, nil end
    end
    if not keys.colsDone then
        for col = 0, COLS - 1 do
            local k = (col < 36) and KEY_COLS[col + 1] or nil      -- 36-39: KEY_COLX (no punctuation keys bound)
            if k and keyFree(k) and keyBind(k, col) then keys.colOf[k], keys.colKey[col] = col, k end
        end
        keys.colsDone = true
    end
    -- the keyed rows: their own key, by name (a row that registers later still finds it)
    for i, name in ipairs(KEY_HOT) do
        local r = pad.rows[name]
        if r and not r.secure and KEY_ROWS[i] then giveRow(name, KEY_ROWS[i]) end
    end
    -- Linux Streaming Edition (2026-11-17, Thor test: every HUD switch click strayed, "padstray"): chq's row key PAGEDOWN, never given in
    -- the game (no keys reach chat's typing), goes to a spare row (KEY_SPARE: "uisw", Hub's switches), so those go as keys too
    for _, sn in ipairs(KEY_SPARE) do
        local sr = pad.rows[sn]
        if sr and not sr.secure and not keys.keyOf[sn] then
            giveRow(sn, "PAGEDOWN")     -- chq's key only: never one another keyed row (pause, spick...) may still register for
        end
    end
    keys.bound = next(keys.keyOf) ~= nil and next(keys.colKey) ~= nil
    if keys.bound and not keys.session then
        -- this session's token: (server seconds mod 10^6) x 1000 + a random part, unique across sessions (as the pins' set, q23)
        local okT, t = pcall(GetServerTime)
        if not (okT and type(t) == "number") then okT, t = pcall(time) end
        t = (okT and type(t) == "number") and t or 0
        keys.session = tostring((math.floor(t) % 1000000) * 1000 + math.random(0, 999))
    end
    pcall(pad.keysFarRefresh)                 -- pad28
    return keys.bound
end
-- a bind pass at the end of this frame (rows register in bursts at load)
function pad.keysSoon()
    if keys.queued then return end
    keys.queued = true
    C_Timer.After(0, function()
        keys.queued = false
        local before = keys.given
        pcall(pad.bindKeys)
        if keys.given ~= before then for _, fn in ipairs(pad.listeners) do pcall(fn) end end   -- a new row key: re-publish
    end)
end

-- the sweep's own row: cell 0 (a CLICK) turns the trace on; every cell is a no-action target for the column keys
local function keytestRow()
    if pad.rows.keytest then return end
    pad.op("keytest", "keytest", function(_, col)
        if col == 0 then
            keys.traceUntil = GetTime() + KEY_TRACE_S
            local nr, nc = 0, 0
            for _ in pairs(keys.keyOf) do nr = nr + 1 end
            for _ in pairs(keys.colKey) do nc = nc + 1 end
            -- the handshake's answer: this session's token, whether keys are bound, how many (the app sends keys only on a match)
            trace({ on = true, s = keys.session, bound = keys.bound, mods = KEY_MOD_NAMES, rows = nr, cols = nc, secs = KEY_TRACE_S })
        end
    end)
end

-- NOTHING OF THIS STAYS IN THE PLAYER'S SETUP (the user's ruling 2026-10-09: the controller layer is "an accessory to the addon" and
-- must "not affect peoples normal set up on their charactors" -- the PC showed what the companion had left behind). Every key here is an
-- OVERRIDE binding on our own owner frame: never SetBinding / SaveBindings, so nothing reaches the saved, server-synced binding set the
-- PC also loads, and never a key the player has bound (keyFree). The client drops overrides itself when the UI unloads; at
-- PLAYER_LOGOUT ours are cleared anyway.
function pad.clearKeys()
    if not keys.owner or InCombatLockdown() then return false end
    if not pcall(ClearOverrideBindings, keys.owner) then return false end
    keys.rowOf, keys.keyOf, keys.colOf, keys.colKey, keys.usedRow = {}, {}, {}, {}, {}
    keys.colsDone, keys.bound, keys.pending, keys.session = false, false, nil, nil
    return true
end

local function keysDescribe()
    if not keys.bound then return nil end
    local rows = {}
    for name, k in pairs(keys.keyOf) do
        local r = pad.rows[name]
        if r and fits(r.row) and keySafe(KEY_MOD_NAMES, k) then rows[name] = k end
    end
    for k, p2 in pairs(KEY_PAGE2) do
        local r, owner = p2 ~= "~far" and pad.rows[p2], keys.rowOf[k]
        if owner and rows[owner] and r and (not r.secure or KEY_SECURE_PLAIN[p2]) and fits(r.row) and not rows[p2] then rows[p2] = k .. " " .. k end
    end
    -- pad27: the far rows, "DOWN DOWN <selector>" (DOWN must be a row key of ours and the selector a bound column key)
    local fk = nil
    for k, p2 in pairs(KEY_PAGE2) do if p2 == "~far" and keys.rowOf[k] and rows[keys.rowOf[k]] then fk = k end end
    if fk then
        for i, name in ipairs(KEY_FAR) do
            local r, sel = pad.rows[name], keys.colKey[i - 1]
            -- a secure one only while a binding click acts on the PRESS (ActionButtonUseKeyDown, the default): then a release that
            -- lands on a swapped cell (the selector's own) can never fire an item; with it off those rows stay clicks
            local routed = keys.proxy and keys.proxy[sel] and keys.hdr ~= nil         -- the router really holds this selector's key
            if not r and sel and pad.keyOnly[name] and not rows[name] and keySafe(KEY_MOD_NAMES, sel) then rows[name] = fk .. " " .. fk .. " " .. sel end
            if r and sel and not rows[name] and fits(r.row) and (not r.secure or (onRow(r) and (routed or keyDownActs()))) then
                rows[name] = fk .. " " .. fk .. " " .. sel
            end
        end
    end
    local cols = {}
    for col = 0, COLS - 1 do
        local k = keys.colKey[col]
        cols[col + 1] = (k and keySafe(KEY_MOD_NAMES, k)) and k or ""
    end
    for k, col in pairs(KEY_COLX) do cols[col + 1] = keys.rowOf[k] and k or "" end
    -- pad31 sfx: the secure far rows whose 36-39 "click" cells the router does (KEY_SFX); the app clicks the others' 36-39
    local sfx = {}
    for name in pairs(KEY_SFX) do if rows[name] then sfx[name] = true end end
    local sticky = {}
    for name in pairs(KEY_STICKY) do if rows[name] then sticky[name] = true end end
    return { mods = KEY_MOD_NAMES, ttl = KEY_PICK_TTL, rows = rows, cols = cols, s = keys.session, sfx = sfx,
             sticky = sticky, stickyTtl = KEY_STICKY_TTL }
end

-- ---------------------------------------------------------------- layout

-- Centred on the top edge of the game screen: 3D world on every screen seen so far (the controller
-- hint panel is top-left, the minimap top-right). Invisible, so all it costs is mouse clicks in
-- that strip, and on a handheld nobody clicks the top screen.
-- the stray-press sink (see "A STRAY PRESS LANDS ON THE FREELOOK PARK POINT")
local sink
pad.strays = 0
local strayReportedAt = -1

-- the sink's strata follows the capture's holder (see "WHILE ANYONE HOLDS THE CONTROLLER IT GOES ON TOP")
local function captureHeld()
    local c = WC.capture                                 -- set by WowCompanionInteract when it loads
    if type(c) ~= "table" or type(c.state) ~= "function" then return false end
    local ok, st = pcall(c.state)
    return ok and type(st) == "table" and st.holder ~= nil
end
function pad.sinkSync()
    if not sink then return end
    local want = captureHeld() and "TOOLTIP" or "BACKGROUND"
    if pad.sinkStrata ~= want then
        pad.sinkStrata = want
        sink:SetFrameStrata(want)
    end
end

local function placeSink()
    local g, i = pad.geom, pad.info
    if not g or not i then return end
    if not sink then
        sink = CreateFrame("Button", nil, UIParent)
        pad.sink = sink                                  -- for the harness
        sink:SetFrameStrata("BACKGROUND")
        pad.sinkStrata = "BACKGROUND"
        pcall(sink.SetMouseClickEnabled, sink, true)
        pcall(sink.SetMouseMotionEnabled, sink, false)
        sink:RegisterForClicks("AnyDown", "AnyUp")
        sink:SetScript("OnClick", function(_, _, down)
            if down == false then return end                -- one count per press
            pad.strays = pad.strays + 1
            local t = GetTime()
            if t - strayReportedAt < 1 then return end       -- rate-capped: never a flood (the 09-28 lesson)
            strayReportedAt = t
            pcall(WC.emit, { type = "padstray", n = pad.strays, v = PADV })
        end)
        if C_Timer and type(C_Timer.NewTicker) == "function" then
            C_Timer.NewTicker(SINK_POLL, function() pcall(pad.sinkSync) end)
        end
    end
    sink:SetSize(SINK / i.sx, SINK / i.sy)
    sink:ClearAllPoints()
    sink:SetPoint("CENTER", UIParent, "TOPLEFT", g.pw * PARK_X / i.sx, -(g.ph * PARK_Y) / i.sy)
    sink:Show()
    pad.sinkSync()
end

function pad.layout()
    local i = scaleInfo()
    if not i then return false end
    local w = COLS * CELL_W
    local x0 = math.floor((i.pw - w) / 2)
    local changed = (not pad.geom) or pad.geom.pw ~= i.pw or pad.geom.ph ~= i.ph or pad.info == nil
                    or math.abs(pad.info.sx - i.sx) > 1e-6 or math.abs(pad.info.sy - i.sy) > 1e-6
    pad.info = i
    -- TOP_GAP keeps the cells off the panel's top edge, where Android treats touches specially;
    -- the probe's proven tap was 18 game px down, and the rows straddle that.
    pad.geom = { x = x0, y = TOP_GAP, pw = i.pw, ph = i.ph }
    for _, r in pairs(pad.rows) do if not r.secure then makeRow(r) end end
    pad.buildSecure()
    pcall(placeSink)           -- the sink is a safety net: it must never be able to break the grid
    pcall(placeCal)            -- pad24: the calibration strip, likewise
    if changed then for _, fn in ipairs(pad.listeners) do pcall(fn) end end
    return true
end

-- Called when the published grid changes, so a feed can re-publish it at once.
function pad.onLayout(fn) pad.listeners[#pad.listeners + 1] = fn end

function pad.describe()
    if not pad.geom and not pad.layout() then return nil end
    local rows, sizes = {}, {}
    local secureOK = pad.secureAt ~= nil and pad.secureAt == geomKey()
    for name, r in pairs(pad.rows) do
        if fits(r.row) and onRow(r) and (not r.secure or (r.built and secureOK)) then   -- pad21: only the tenant on a shared row
            rows[name] = r.row
            sizes[name] = r.n
        end
    end
    -- pad26: the registered rows this layout cannot place (a shared row once, by its host), name -> row; normally absent
    local drop
    for name, r in pairs(pad.rows) do
        if not r.guestOf and not fits(r.row) then drop = drop or {}; drop[name] = r.row end
    end
    local g = pad.geom
    -- pad23: a described row whose first cell does not stand where the grid says (its real top, game px from the screen's top, read
    -- off the frame): `off` lists it, so a tap that never lands can be told from a row that moved. Read only; normally absent
    local off
    local top = SN(function() return UIParent:GetTop() end)
    for name, idx in pairs(rows) do
        local r = pad.rows[name]
        local b = r and r.cells and r.cells[0]
        local bt = b and SN(function() return b:GetTop() end)
        if top and bt then
            local real = (top - bt) * pad.info.sy
            if math.abs(real - (g.y + idx * CELL_H)) > 0.5 then
                off = off or {}
                off[name] = math.floor(real * 10 + 0.5) / 10
            end
        end
    end
    -- pad24: the calibration strip while it is up - its box, its press count and where the game saw its last presses ("x,y", newest last)
    local cal
    local cb, c = calBox(), pad.cal
    if cb and c.btn and c.btn:IsShown() then
        cal = { x = cb.x, y = cb.y, w = cb.w, h = cb.h, n = c.n, p = #c.p > 0 and table.concat(c.p, " ") or nil }
    end
    -- popupTop: where the game's dialogs start, in the same game pixels, so any reader can check the grid's bottom
    -- (y + rows * ch) stays above them at whatever UI scale the player picks
    return { v = PADV, x = g.x, y = g.y, cw = CELL_W, ch = CELL_H, cols = COLS,
             popupTop = math.floor(POPUP_TOP_UNITS * pad.info.sy * 10 + 0.5) / 10,
             pw = g.pw, ph = g.ph, rows = rows, sizes = sizes, keys = keysDescribe(), off = off, calib = cal, drop = drop }
end

local f = CreateFrame("Frame")
for _, e in ipairs({ "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "UI_SCALE_CHANGED",
                     "DISPLAY_SIZE_CHANGED", "PLAYER_REGEN_ENABLED", "PLAYER_REGEN_DISABLED", "PLAYER_LOGOUT" }) do
    pcall(function() f:RegisterEvent(e) end)
end
f:SetScript("OnEvent", function(_, event)
    if event == "PLAYER_LOGOUT" then pcall(pad.clearKeys); return end   -- pad10: our key overrides go with us
    if event == "PLAYER_REGEN_DISABLED" then pcall(pad.keyUnswap); return end   -- pad27: before the lockdown, the column keys back
    if event == "PLAYER_REGEN_ENABLED" then
        -- secure work queued during combat: do it now, then let feeds re-publish the grid
        if pad.securePending and pad.buildSecure() then
            for _, fn in ipairs(pad.listeners) do pcall(fn) end
        end
        -- pad10: key bindings asked for in a fight
        if keys.wantBind and pcall(pad.bindKeys) then for _, fn in ipairs(pad.listeners) do pcall(fn) end end
        return
    end
    pad.layout()
    pcall(keytestRow)                         -- pad10c: the sweep's own row, once the rooms' rows are in
    local had = keys.bound
    pcall(pad.bindKeys)                       -- pad10: out of combat at login / a layout change; a no-op once everything is bound
    if keys.bound and not had then for _, fn in ipairs(pad.listeners) do pcall(fn) end end
end)

-- NO SLASH COMMAND, ON PURPOSE. There was a `/wcpad show` that tinted every cell. Typed into the
-- game's chat in controller mode on 2026-09-28 it set off 4,012 ADDON_ACTION_FORBIDDEN on
-- SetPreferredGamepadInteractTarget (Blizzard's gamepad action bar) in 3 minutes and froze the game
-- until a restart. It had no other use, so it is gone (user ruling 11:35). Do not add a command
-- here; if the cells must be seen, set pad.visible from code under a test, never from chat.

-- ---------------------------------------------------------------- pad12 THE PARKED CURSOR (the user, 2026-11-04: "cursor is still
-- sitting in the middle being annoying as hell. can we like hide it"): every tap of the app is a mouse click, and after one the game
-- parks its cursor mid-screen in controller mode, where it stays. While the cursor RESTS (pad13: still for a second, anywhere),
-- over the 3D world (nothing under it but WorldFrame), with nothing held and no spell aiming, it is drawn as a blank picture
-- (SetCursor, Media/cursor_blank.tga, fully transparent); anywhere else, or anything held / aimed, it is the game's own again
-- (ResetCursor). A real mouse moved away gets its cursor back at once. Nothing saved, no setting changed. If this client refuses the
-- picture, nothing changes (every call guarded).
do
    local BLANK = "Interface\\AddOns\\WowCompanion\\Media\\cursor_blank"
    local f = CreateFrame("Frame")
    local hidden, acc = false, 0
    local function plainNum(v) return type(v) == "number" and (type(WC.isPlain) ~= "function" or WC.isPlain(v)) and v or nil end
    -- pad13 (the Thor's screenshots: the game parks it at x 50 %, y about 41 %, not the centre; the user: "make the cursor like 1 pixel
    -- while not using the track pad or touching the top screen"): hidden once it has NOT MOVED for a second, wherever it rests over
    -- the world; the first move (the track pad, a touch, a real mouse) shows it again
    local lastX, lastY, stillAt = nil, nil, 0
    local function parked()
        local x, y = GetCursorPosition()
        x, y = plainNum(x), plainNum(y)
        if not x or not y then return false end
        local now = GetTime()
        if not lastX or math.abs(x - lastX) > 1 or math.abs(y - lastY) > 1 then lastX, lastY, stillAt = x, y, now; return false end
        if now - stillAt < 1.0 then return false end
        if type(GetCursorInfo) == "function" and GetCursorInfo() ~= nil then return false end
        if type(SpellIsTargeting) == "function" and SpellIsTargeting() then return false end
        local focus = nil
        if type(GetMouseFoci) == "function" then local t = GetMouseFoci(); focus = type(t) == "table" and t[1] or nil
        elseif type(GetMouseFocus) == "function" then focus = GetMouseFocus() end
        return focus == nil or focus == WorldFrame
    end
    -- pad14 (the user's test14: the blank cursor "is showing a big black box": the HARDWARE cursor ignores its alpha; the user's pick
    -- "Yes, try software cursor"): WoW's own Hardware Cursor setting (gxCursor) is switched OFF ONCE (WowCompanionDB.cursorSoftSet,
    -- never again, so the player's later choice stays), and the cursor is hidden only while the game draws it itself (gxCursor "0"),
    -- where the picture's alpha works. What the game says is reported (cap probe "cursorsoft"; the app logs it as WCCURSOR).
    local function soft()
        local ok, v = pcall(function() return C_CVar.GetCVar("gxCursor") end)
        return ok and type(v) == "string" and (type(WC.isPlain) ~= "function" or WC.isPlain(v)) and v == "0"
    end
    local cv = CreateFrame("Frame")
    cv:RegisterEvent("PLAYER_ENTERING_WORLD")
    cv:SetScript("OnEvent", function()
        cv:UnregisterEvent("PLAYER_ENTERING_WORLD")
        pcall(function()
            if type(WowCompanionDB) ~= "table" then WowCompanionDB = {} end
            local before = C_CVar.GetCVar("gxCursor")
            local out = { type = "cap", probe = "cursorsoft", v = PADV, before = before }
            if not WowCompanionDB.cursorSoftSet and not InCombatLockdown() then
                WowCompanionDB.cursorSoftSet = true
                if before ~= nil and before ~= "0" then
                    out.set = pcall(C_CVar.SetCVar, "gxCursor", "0") and "0" or "refused"
                    out.after = C_CVar.GetCVar("gxCursor")
                end
            end
            WC.send(WC.encode(out))
        end)
    end)
    -- pad25 (the user, 2026-11-19, streaming: "the cursor keeps randomly showing on the game"): OUR OWN PRESSES never show it. A press
    -- of ours (pad.pressT: a cell, the calibration strip, the layout catcher) ARMS the blank cursor; a move within PRESS_WIN of a press
    -- (to the cell, the game's park after it) or back to the park spot learned (PARK_PX) is ours and keeps it blank wherever it rests;
    -- the first other move is a real mouse (the PC's user, the trackpad, a touch on the top screen): disarmed, pad.humanAt = then.
    -- While armed it is looked at every frame (the game resets it over a unit), otherwise as pad13 (every 0.1 s).
    local PRESS_WIN, PARK_PX, HUMAN_S = 1.5, 2, 0.15
    local armed, armedAt, parkX, parkY, mx, my, pending = false, nil, nil, nil, nil, nil, nil
    pad.humanAt = nil
    local function track()
        local x, y = GetCursorPosition()
        x, y = plainNum(x), plainNum(y)
        if not x or not y then return end
        local c = clock()                                              -- pad.pressT's clock
        local pt = type(pad.pressT) == "number" and pad.pressT or nil
        if pt and pt ~= armedAt then armedAt = pt; armed = true end
        if mx and (math.abs(x - mx) > 1 or math.abs(y - my) > 1) then
            if pt and c - pt <= PRESS_WIN then
                parkX, parkY, pending = x, y, nil                          -- the press's own moves: the last is where the game parks it
            elseif not (parkX and math.abs(x - parkX) <= PARK_PX and math.abs(y - parkY) <= PARK_PX) then
                pending = pending or c                                     -- nothing of ours explains it (yet)
            end
        end
        mx, my = x, y
        -- a posted press's move may reach the game a frame before the press itself: a move is a real mouse only when no press of
        -- ours follows it within HUMAN_S
        if pending then
            if pt and pt >= pending then pending = nil
            elseif c - pending > HUMAN_S then
                pending = nil
                armed = false
                pad.humanAt = GetTime()                                    -- Dialogs d35 compares it with its own GetTime()
            end
        end
    end
    local function busy()
        if type(GetCursorInfo) == "function" and GetCursorInfo() ~= nil then return true end
        return type(SpellIsTargeting) == "function" and SpellIsTargeting() == true
    end
    pad.cursorArmed = function() return armed end
    local function look(_, el)
        acc = acc + el
        if not armed and acc < 0.1 and pad.pressT == armedAt then return end   -- a new press of ours is looked at in its own frame
        acc = 0
        pcall(track)
        local p
        if armed then
            local okB, b = pcall(busy)
            p = not (okB and b) and soft()
        else
            local ok, q = pcall(parked)
            p = ok and q == true and soft()
            if p then local x, y = GetCursorPosition(); parkX, parkY = plainNum(x), plainNum(y) end   -- pad13's rest: the park spot
        end
        if p then
            pcall(SetCursor, BLANK)                                    -- again each look: the game resets it over a unit or an object
            hidden = true
        elseif hidden then
            pcall(ResetCursor)
            hidden = false
        end
    end
    f:SetScript("OnUpdate", look)
    pad.cursorLook = look                                              -- for the harness (tools/test_stream_cursor.py)
end

-- ---------------------------------------------------------------- pad15 OUR ADD-ONS SWITCHED BACK ON (the Thor's log, 2026-11-04: on a
-- character where the game's "WowCompanionSpells has been blocked ..." pop-up was answered with Disable, Spells never loaded again - no
-- Smart Y, no Party mode, its settings gone - and the app's install does not touch the game's per-character add-on list). At each login
-- every DS Forever add-on the game has OFF is switched ON (for every character), and the app is told (cap probe "addonsoff"); it reloads
-- the game's interface once so they load. Never another add-on's state.
-- pad20 (issue #278, the user relaying a player, 2026-11-13: "says waitin on wow controller. i press start and the wheel only pops up on
-- top screen"): the login probe (Chat.lua's "ours") said WowCompanionSpells:DISABLED, yet pad15 found nothing off - its only test was
-- GetAddOnEnableState(name, character) == 0, which that client did not answer so (an argument order / a per-character state it does
-- not report). OFF is now ALSO the game's own reason (GetAddOnInfo's "DISABLED": what the probe read), the state asked both ways and
-- for every character; ON is EnableAddOn for every character and for this one; the probe says how each was found and what the game
-- reports after (`after`: the reason now, "" = loadable), so a report shows whether the switch took.
do
    local OURS = { "WowCompanionSpells", "WowCompanionHub", "WowCompanionQuests", "WowCompanionInteract", "WowCompanionCharacter",
                   "WowCompanionSocial", "WowCompanionCalendar", "WowCompanionGroupFinder", "WowCompanionProfessions", "WowCompanionPvp" }
    local function num(fn) local ok, v = pcall(fn); if ok and type(v) == "number" and (type(WC.isPlain) ~= "function" or WC.isPlain(v)) then return v end end
    local function reasonOf(a)
        local info = (type(C_AddOns) == "table" and C_AddOns.GetAddOnInfo) or rawget(_G, "GetAddOnInfo")
        if type(info) ~= "function" then return nil end
        local ok, _, _, _, _, reason = pcall(info, a)
        return ok and type(reason) == "string" and (type(WC.isPlain) ~= "function" or WC.isPlain(reason)) and reason or (ok and "" or nil)
    end
    -- why [a] is off ("state" = the enable state 0, "reason" = the game's DISABLED), nil = on
    local function offWhy(a, me)
        local A = C_AddOns
        if num(function() return A.GetAddOnEnableState(a, me) end) == 0 then return "state" end
        if num(function() return A.GetAddOnEnableState(a) end) == 0 then return "state" end
        if reasonOf(a) == "DISABLED" then return "reason" end
        return nil
    end
    function WC.addonsOn()
        if type(C_AddOns) ~= "table" or type(C_AddOns.EnableAddOn) ~= "function" then return nil end
        local me = UnitName("player")
        local off, how, after = {}, {}, {}
        for _, a in ipairs(OURS) do
            local why = offWhy(a, me)
            if why then
                local ok1 = pcall(C_AddOns.EnableAddOn, a)                       -- every character
                local ok2 = me and pcall(C_AddOns.EnableAddOn, a, me) or false   -- and this one
                if ok1 or ok2 then
                    off[#off + 1] = a; how[#how + 1] = why
                    after[#after + 1] = reasonOf(a) or "?"
                end
            end
        end
        if #off > 0 then
            pcall(function() if type(C_AddOns.SaveAddOns) == "function" then C_AddOns.SaveAddOns() end end)
            WC.send(WC.encode({ type = "cap", probe = "addonsoff", v = PADV, list = off, how = how, after = after }))
            WC.push()
        end
        return off
    end
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("PLAYER_ENTERING_WORLD")
    ev:SetScript("OnEvent", function()
        ev:UnregisterEvent("PLAYER_ENTERING_WORLD")
        pcall(WC.addonsOn)
    end)
end

-- ---------------------------------------------------------------- pad22 THE LAYOUT EDITOR'S CATCHER AND STORE
-- The user, 2026-11-16: "we need to make a way to basically edit the UI locations on the top screen from our UI menu". The design's
-- picks (all the recommended ones): stage 1 moves DS Forever's OWN top-screen pieces only (the HUD, the compass, the target bar, the
-- party block, the Nintendo bar, the top chat strip); a tap that sets an EXACT spot; a linked piece follows its parent until it is moved;
-- one saved layout per character, plus "Copy from character". The editor itself is Hub.lua's (hub55); this is what every owner reads.
--   THE STORE: WowCompanionDB.lay[name-realm][id] = { dx, dy, s } - our own saved table, plain numbers only: dx / dy in 1080-line pixels
--   (right / down) from the piece's own default anchor, s its size in percent. No entry = the default (and a linked piece follows its
--   parent). Written ONLY by the editor's Save (the player's press) and the HUD's one-time move of its old height / scale (Trail prd18);
--   SvKeep (PadMap m51) carries it with the rest of WowCompanionDB. WC.lay.get(id) is what an owner places by: the editor's VIEW of its
--   draft while it is open (WC.lay.view: id -> entry, or false = the default), else the saved entry.
--   THE CATCHER (the design's "absolute channel": a repeated or stale tap changes nothing): one plain Button of ours, the whole screen, at
--   TOOLTIP strata and frame level 0 - under every pad cell (TOOLTIP, its default level) and the stray-press sink, over every game window
--   (an invisible window a room keeps open by alpha never takes the tap). The PRESS only (a stray release does nothing); where the press
--   landed (GetCursorPosition, read only) is handed to the editor in 1080-line pixels. Left out: the pad's band (describe()'s rows, its
--   gaps too) and the sink at the park point - a tap meant for a spot there would press a cell, so THE REACH SWITCH (L.reach) reads every
--   tap REACH pixels lower (L.reachPx: never less than the band's own bottom, so a spot at the very top is reached on any screen): the app
--   taps under the spot. Its own double-press guard: a second press at the same spot within CATCH_REPEAT
--   (60 ms; TapPad's REPEAT of 0.25 s would cap it at 4 taps a second). INERT (L.inert) it takes the press and does nothing: a fight's
--   start or the editor's close leaves it so for LINGER_S after its last tap (taps already in flight never reach the world), then hides it.
--   One real tap test on the Thor is owed before release (TapPad's rule; probe 5 of the design: 1 px accuracy, taps a second).
do
    local L = { V = PADV, editing = false, view = nil, reach = false, inert = false, REACH = 160, CATCH_REPEAT = 0.06, CATCH_SAME = 1.5,
                LINGER_S = 1.5, BAND_PAD = 2, n = 0, refused = 0, lastAt = -1, lastX = nil, lastY = nil, onSpot = nil }
    WC.lay = L
    local function plain(v) return (type(WC.isPlain) ~= "function" or WC.isPlain(v)) end
    local function num(v) if type(v) == "number" and plain(v) and v == v and v ~= math.huge and v ~= -math.huge then return v end end
    L.num = num
    -- "Name-Realm", the key every per-character store of ours uses
    function L.who()                                                    -- pad27: nil until the realm is known (never "Name-")
        return ((function() if type(WC.charKey) == "function" then return (WC.charKey()) end; local ok, k = pcall(function() local n, r = UnitName("player"), GetRealmName(); if type(n) == "string" and type(r) == "string" and n:find("%S") and r:find("%S") and r ~= "?" and r ~= "_" then return n .. "-" .. r end end); return ok and k or nil end)())
    end
    -- one entry as whole plain numbers (nil = the default)
    function L.clean(e)
        if type(e) ~= "table" then return nil end
        local dx, dy, s = num(e.dx) or 0, num(e.dy) or 0, num(e.s) or 100
        return { dx = math.floor(dx + 0.5), dy = math.floor(dy + 0.5), s = math.floor(s + 0.5) }
    end
    -- [who]'s saved table (nil = none); never made here
    function L.store(who)
        who = who or L.who()
        local db = type(WowCompanionDB) == "table" and WowCompanionDB.lay or nil
        local t = who and type(db) == "table" and db[who] or nil
        return type(t) == "table" and t or nil
    end
    function L.saved(id, who) local t = L.store(who); return t and L.clean(t[id]) or nil end
    -- what an owner places [id] by: the editor's view while it is open, else the saved entry; nil = the default
    function L.get(id)
        if L.editing and type(L.view) == "table" then
            local v = L.view[id]
            if v == false then return nil end
            if v ~= nil then return L.clean(v) end
        end
        return L.saved(id)
    end
    -- the screen in 1080-line pixels: its width (the game's aspect), its height, and the factor from UIParent units
    function L.screen()
        local okH, uh = pcall(function() return UIParent:GetHeight() end)
        local okW, uw = pcall(function() return UIParent:GetWidth() end)
        uh, uw = okH and num(uh) or nil, okW and num(uw) or nil
        if not (uh and uw and uh > 0 and uw > 0) then return 1920, 1080, 1 end
        return uw * 1080 / uh, 1080, 1080 / uh
    end
    -- 1080-line pixels -> UIParent units
    function L.u(px)
        local _, _, k = L.screen()
        return px / k
    end

    -- ---- THE CATCHER
    local catcher
    -- the zones a tap is never read in (1080-line pixels): the pad's band (every row it may hold) and the sink
    function L.forbidden()
        local out = {}
        local g = pad.geom
        if not g or not g.ph or g.ph <= 0 then return out end
        local k = 1080 / g.ph
        local rows = math.max(1, pad.nrows or 0)
        -- pad24: the band takes the calibration strip in (CAL_GAP + CAL_W left of the grid)
        local cb = pad.calBox and pad.calBox()
        local left = cb and (CAL_GAP + CAL_W) or 0
        local hh = math.max(rows * CELL_H, cb and cb.h or 0)
        out[#out + 1] = { x = (g.x - left - L.BAND_PAD) * k, y = (g.y - L.BAND_PAD) * k, w = (left + COLS * CELL_W + 2 * L.BAND_PAD) * k,
                          h = (hh + 2 * L.BAND_PAD) * k, why = "pad" }
        out[#out + 1] = { x = (g.pw * PARK_X - SINK / 2) * k, y = (g.ph * PARK_Y - SINK / 2) * k, w = SINK * k, h = SINK * k, why = "sink" }
        return out
    end
    local function inside(z, x, y) return x >= z.x and x <= z.x + z.w and y >= z.y and y <= z.y + z.h end
    function L.blocked(x, y)
        for _, z in ipairs(L.forbidden()) do if inside(z, x, y) then return z.why end end
        return nil
    end
    -- the reach distance: REACH, or more where the pad's band reaches lower (a smaller screen: the band is taller in 1080-line pixels),
    -- so a spot at the very top always has its tap under the band (the review of 2026-11-16)
    function L.reachPx()
        for _, z in ipairs(L.forbidden()) do
            if z.why == "pad" then return math.max(L.REACH, math.ceil(z.y + z.h + 8)) end
        end
        return L.REACH
    end
    -- where the press landed, in 1080-line pixels from the top-left (nil = not readable)
    function L.cursor()
        local ok, x, y = pcall(GetCursorPosition)
        x, y = ok and num(x) or nil, ok and num(y) or nil
        local okS, es = pcall(function() return UIParent:GetEffectiveScale() end)
        es = okS and num(es) or nil
        local okH, uh = pcall(function() return UIParent:GetHeight() end)
        uh = okH and num(uh) or nil
        if not (x and y and es and es > 0 and uh and uh > 0) then return nil end
        local k = 1080 / uh
        return (x / es) * k, (uh - y / es) * k
    end
    -- one press on the catcher: the guard, the zones, the reach, then the editor's handler with the spot
    function L.press()
        pad.pressT = clock()                                             -- pad25: the editor's tap is ours: the cursor stays blank
        local x, y = L.cursor()
        if not x then L.refused = L.refused + 1; return false, "cursor" end
        local t = clock()
        if L.inert then L.lastAt = t; return false, "inert" end
        if L.lastX and t - L.lastAt < L.CATCH_REPEAT and math.abs(x - L.lastX) <= L.CATCH_SAME and math.abs(y - L.lastY) <= L.CATCH_SAME then
            return false, "repeat"                                       -- the tap's own second press
        end
        L.lastAt, L.lastX, L.lastY = t, x, y
        local why = L.blocked(x, y)
        if why then L.refused = L.refused + 1; return false, why end
        L.n = L.n + 1
        local sy = y - (L.reach and L.reachPx() or 0)
        if type(L.onSpot) == "function" then pcall(L.onSpot, x, sy) end
        return true
    end
    local function make()
        if catcher then return catcher end
        catcher = CreateFrame("Button", nil, UIParent)
        L.catcher = catcher                                              -- for the harness
        catcher:SetFrameStrata("TOOLTIP")
        pcall(catcher.SetFrameLevel, catcher, 0)                         -- under every pad cell and the sink (their default level)
        catcher:SetAllPoints(UIParent)
        catcher:EnableMouse(true)
        pcall(catcher.SetMouseMotionEnabled, catcher, false)             -- click only: the parked cursor's hover is unchanged
        catcher:RegisterForClicks("AnyDown")                             -- the press only
        catcher:SetScript("OnClick", function(_, _, down) if down ~= false then L.press() end end)
        catcher:Hide()
        return catcher
    end
    -- on: the catcher shown and live; [fn](x, y) gets every spot
    function L.catchOn(fn)
        make()
        L.onSpot, L.inert, L.lingerTo = fn, false, nil
        catcher:Show()
        return true
    end
    -- off: inert at once, hidden LINGER_S after its last tap (taps still in flight land on it, never on the world)
    function L.catchOff()
        if not catcher or not catcher:IsShown() then return end
        L.inert = true
        L.inertAt = clock()
        local token = {}
        L.lingerTo = token
        local function later()
            if L.lingerTo ~= token or not L.inert then return end
            local left = L.LINGER_S - (clock() - math.max(L.lastAt or -1, L.inertAt or -1))
            if left > 0.01 then C_Timer.After(left, later); return end
            catcher:Hide()
            L.lingerTo = nil
        end
        C_Timer.After(L.LINGER_S, later)
    end
    function L.catching() return catcher ~= nil and catcher:IsShown() and not L.inert end
    -- the catcher as the app reads it: its rect, the zones left out, the reach distance (1080-line pixels)
    function L.catchDescribe()
        local w, h = L.screen()
        return { x = 0, y = 0, w = math.floor(w + 0.5), h = h, no = L.forbidden(), reach = L.reachPx(), on = L.catching() or nil,
                 inert = (catcher ~= nil and catcher:IsShown() and L.inert) or nil }
    end
end
