"""KEYS: THE FAR ROWS (TapPad pad27, Linux Streaming Edition 2026-11-20; the user: "using items from bags does not work", vendor Buy
too: every row key and double was taken, so those rows clicked, and a click lands on the parked cursor), under tools/wowstub.py.

    python -B tools/test_keys_far.py

Proves: far rows are published as "DOWN DOWN <selector>"; DOWN DOWN + selector + column presses a PLAIN far row's cell (ibuy,
keytest = the handshake by keys); for a SECURE far row (a bag) the selector rebinds the column keys onto its named cells, so the
column key fires the cell's secure action (/use the item) and the keys go back to the dispatcher at the release; refused in combat;
PLAYER_REGEN_DISABLED puts the keys back; DOWN alone is still spick. Needs lupa. Exit code 1 on any failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world, docs  # noqa: E402

fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


L, errs = boot_world()
check(not errs, "0: the world loads", errs)
L.execute('''
local pad = WowCompanion.pad
pad.clearKeys()
SetOverrideBinding(CreateFrame("Frame"), false, "CTRL-SHIFT-PAGEDOWN", "COMBATLOGPAGEDOWN")   -- as in the live game
for _, n in ipairs({ "spick", "pause", "ibuy" }) do if not pad.rows[n] then pad.op(n, n, function() end) end end
-- a stand-in bag row: cell c uses item 1000 + c (the real Bags.lua sets type/item the same way)
BAGTAPS = {}
pad.secureRow("bag0", 20, function(btn, col) btn:SetAttribute("type", "item"); btn:SetAttribute("item", "item:" .. (1000 + col)) end,
              function(col) BAGTAPS[#BAGTAPS + 1] = col end)
pad.bindKeys()
FIRED = {}
for name, r in pairs(pad.rows) do
    local h = r.handler
    if type(h) == "function" then r.handler = function(k, c) FIRED[#FIRED + 1] = name .. ":" .. tostring(c); return h(k, c) end end
end
''')
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
cols = [KT['cols'][i] for i in range(1, 41)] if KT else []
check(rows.get('spick') == 'DOWN', "1: spick keeps DOWN", rows)
check(rows.get('ibuy') == 'DOWN DOWN ' + cols[0], "2: ibuy = DOWN DOWN + selector 0", rows.get('ibuy'))
check(rows.get('keytest') == 'DOWN DOWN ' + cols[2], "3: keytest = DOWN DOWN + selector 2 (the handshake by keys)", rows.get('keytest'))
check(rows.get('bag0') == 'DOWN DOWN ' + cols[3], "4: the secure bag0 = DOWN DOWN + selector 3", rows.get('bag0'))


def key(k):
    """one key as the game delivers it: whatever CTRL-SHIFT-<k> is bound to now, down then up"""
    L.execute('tapKey("CTRL-SHIFT-%s")' % k)


def fired():
    n = int(L.eval('#FIRED'))
    out = [L.eval('FIRED[%d]' % i) for i in range(1, n + 1)]
    L.execute('FIRED = {}')
    return out


def actions():
    n = int(L.eval('#ACTIONS'))
    out = [L.eval('ACTIONS[%d].item' % i) for i in range(1, n + 1)]
    L.execute('ACTIONS = {}')
    return out


def tick(s):
    L.execute('runTimers(NOW + %s)' % s)


L.execute('ACTIONS = {}')
tick(1)
for k in ('DOWN', 'DOWN', cols[0], cols[7]):
    key(k)
check(fired() == ['ibuy:7'], "5: DOWN DOWN sel0 + column 7 = ibuy:7", '')
tick(1)
key('DOWN'); key(cols[4])
check(fired() == ['spick:4'], "6: DOWN alone is still spick")
def hdr(a):
    return L.eval('WowCompanionPadKeyHdr:GetAttribute("%s")' % a)


# pad28: the router. No rebinding: every key stays bound to its proxy; the bag cell is reached through the proxy's snippet
tick(1)
for k in ('DOWN', 'DOWN', cols[3]):
    key(k)
check(L.eval('WowCompanion.pad.keys.swap == nil') and hdr('sel') == 'bag0', "7: the bag selector is remembered by the router (no swap)",
      hdr('sel'))
check(L.eval('GetBindingAction("CTRL-SHIFT-%s")' % cols[5]) == 'CLICK WCPadKeyP_%s:%s' % (cols[5], cols[5]),
      "8: column 5's key stays bound to its proxy", L.eval('GetBindingAction("CTRL-SHIFT-%s")' % cols[5]))
key(cols[5])
tick(0)
got = actions()
check(got == ['item:1005'], "9: the column key used bag0 slot 6's item (the cell's secure action, via the router)", got)
check(hdr('sel') is None and fired() == [], "10: the pick is spent; the dispatcher got no stray column")
tick(1)
key('INSERT'); key(cols[2])
check(fired() == ['qact:2'], "11: an ordinary row after a bag press still works")
# a pick whose column was lost: the next action's row key clears it
tick(1)
for k in ('DOWN', 'DOWN', cols[3]):
    key(k)
key('INSERT'); key(cols[4])
check(fired() == ['qact:4'] and actions() == [], "12: a lost column: the next row key clears the pick (no item)")
# IN A FIGHT: the whole point
tick(1)
L.execute('fire("PLAYER_REGEN_DISABLED"); COMBAT = true')
for k in ('DOWN', 'DOWN', cols[3], cols[7]):
    key(k)
tick(0)
got = actions()
check(got == ['item:1007'], "13: IN COMBAT a bag item is used by keys", got)
for k in ('DOWN', 'DOWN', cols[0], cols[2]):
    key(k)
check(fired() == ['ibuy:2'], "14: in combat a PLAIN far row (ibuy) still goes through the dispatcher", '')
key('DOWN'); key(cols[1])
check(fired() == ['spick:1'], "15: in combat DOWN alone is still spick")
L.execute('COMBAT = false; fire("PLAYER_REGEN_ENABLED")')
check(not L.eval('#SNIPERR > 0'), "16: no snippet error", L.eval('SNIPERR[1]'))
# keytest by keys answers the handshake
tick(1)
L.execute('SENT = {}') if L.eval('type(SENT)') == 'table' else None
for k in ('DOWN', 'DOWN', cols[2], cols[0]):
    key(k)
hs = [d for d in docs(L) if d.get('type') == 'padkeytest' and d.get('on')]
check(bool(hs) and hs[-1].get('s') == KT['s'], "17: keytest:0 by keys answers the handshake with this session's token", hs[-1:] or '')

# ActionButtonUseKeyDown off: the router does not depend on it, the secure far rows stay published
L.execute('_G.GetCVarBool = function(n) if n == "ActionButtonUseKeyDown" then return false end end')
r2 = dict(L.eval('WowCompanion.pad.describe().keys')['rows'].items())
check('bag0' in r2 and 'ibuy' in r2, "18: key-up setting off: the far rows (bags too) stay published", r2.get('bag0'))
# the bag row's own tap work ran (its onClick: the bags' proof that a tap landed)
# with the setting off, the proxies still act on the press (their own useOnKeyDown); a bag item and a plain row still work
tick(1)
fired(); L.execute('ACTIONS = {}; ACT_ON_DOWN = false')       # the stub's own switch for the setting
for k in ('DOWN', 'DOWN', cols[3], cols[6]):
    key(k)
got = actions()
check(got == ['item:1006'], "18b: cast-on-key-down OFF: a bag item by keys still works", got)
tick(1)
key('INSERT'); key(cols[1])
got = fired()
check(got == ['qact:1'], "18c: cast-on-key-down OFF: a plain row still works", got)
L.execute('ACT_ON_DOWN = true')
check(L.eval('#BAGTAPS') >= 2, "19: the row's own tap work ran for each bag press", L.eval('#BAGTAPS'))

# 2026-11-21: tests 20-22 (time-outs on the DOWN count / bag pick) REMOVED: the game's restricted environment has no GetTime,
# the secure snippets keep no clock (the stub's RESTRICTED has none either, so a snippet calling it fails here as in the game).
# pad29: Bags' pick rows (plain) are far rows with selectors 10-12; a finger on a slot = bmvq 36, bagsort 10 + bag, bmv slot - 1
L.execute("""
local pad = WowCompanion.pad
for _, n in ipairs({ "bmvq", "bagsort", "bmv" }) do
    if not pad.rows[n] then pad.op(n, n, function() end) end
    local r, name = pad.rows[n], n
    local h = r.handler
    if type(h) == "function" and not r.wcTest then r.wcTest = true; r.handler = function(k, c) FIRED[#FIRED + 1] = name .. ":" .. tostring(c); return h(k, c) end end
end
pad.bindKeys()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('bmvq') == 'DOWN DOWN ' + cols[10], "23: bmvq = DOWN DOWN + selector 10", rows.get('bmvq'))
check(rows.get('bagsort') == 'DOWN DOWN ' + cols[11], "24: bagsort = DOWN DOWN + selector 11", rows.get('bagsort'))
check(rows.get('bmv') == 'DOWN DOWN ' + cols[12], "25: bmv = DOWN DOWN + selector 12", rows.get('bmv'))
fired(); tick(1)
for k in ('DOWN', 'DOWN', cols[10], 'INSERT', 'DOWN', 'DOWN', cols[11], cols[11], 'DOWN', 'DOWN', cols[12], cols[3]):
    key(k)
got = fired()
check(got == ['bmvq:36', 'bagsort:11', 'bmv:3'], "26: a slot pick by keys: bmvq 36 (INSERT), bagsort 11, bmv 3", got)

# pad30: key-only rows (Bags' bcur0..5): one far step moves the bag cursor; never laid on the pad, never in describe().rows
L.execute("""
local pad = WowCompanion.pad
CURTAPS = {}
pad.keyRow("bcur2", 40, function(col) CURTAPS[#CURTAPS + 1] = col end)
pad.bindKeys()
""")
D = L.eval('WowCompanion.pad.describe()')
KT = D['keys'] if D else None
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('bcur2') == 'DOWN DOWN ' + cols[15], "27: bcur2 = DOWN DOWN + selector 15", rows.get('bcur2'))
check(D is not None and D['rows']['bcur2'] is None, "28: a key-only row takes no pad row (not in describe().rows)", '')
tick(1)
for k in ('DOWN', 'DOWN', cols[15], cols[6]):
    key(k)
check(L.eval('#CURTAPS') == 1 and L.eval('CURTAPS[1]') == 6, "29: DOWN DOWN sel15 + column 6 = bcur2 column 6, in ONE step", L.eval('CURTAPS[1]'))
check(fired() == [], "30: ... and no plain row fired with it", '')
tick(1)
for k in ('DOWN', 'DOWN', cols[15], 'INSERT'):
    key(k)
check(L.eval('#CURTAPS') == 2 and L.eval('CURTAPS[2]') == 36, "31: a key-only row's column 36 by INSERT", L.eval('CURTAPS[2]'))

# pad31: a SECURE far row's "click" cells by keys (the dialogs' leave buttons, the backpack doors), columns 36-39 too
L.execute("""
local pad = WowCompanion.pad
TGT_HITS = {}
local function target(name) local f = CreateFrame("Button", name, UIParent); f:SetScript("OnClick", function() TGT_HITS[#TGT_HITS + 1] = name end); return f end
local t25, t38 = target("LeaveTarget25"), target("DoorTarget38")
IDLGTAPS = {}
pad.secureRow("idlg", 40, function(btn, col)
    if col == 25 then btn:SetAttribute("type", "click"); btn:SetAttribute("clickbutton", t25)
    elseif col == 38 then btn:SetAttribute("type", "click"); btn:SetAttribute("clickbutton", t38) end
end, function(col) IDLGTAPS[#IDLGTAPS + 1] = col end)
if pad.buildSecure then pad.buildSecure() end
pad.bindKeys()
if pad.keysFarRefresh then pad.keysFarRefresh() end
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('idlg') == 'DOWN DOWN ' + cols[19], "32: idlg = DOWN DOWN + selector 19", rows.get('idlg'))
check(KT is not None and KT['sfx']['idlg'] is True and KT['sfx']['bag0'] is None, "33: sfx lists idlg (36-39 by keys), not bag0 (its doors stay clicks)", '')
def hits():
    n = int(L.eval('#TGT_HITS')); out = [L.eval('TGT_HITS[%d]' % i) for i in range(1, n + 1)]; L.execute('TGT_HITS = {}'); return out
fired(); hits(); tick(1)
for k in ('DOWN', 'DOWN', cols[19], cols[25]):
    key(k)
got = hits()
check(got == ['LeaveTarget25'], "34: DOWN DOWN sel19 + column 25 clicks the leave cell's own target", got)
check(L.eval('#IDLGTAPS') >= 1 and L.eval('IDLGTAPS[#IDLGTAPS]') == 25, "35: ... and the row's own tap work ran for column 25", L.eval('#IDLGTAPS'))
tick(1)
for k in ('DOWN', 'DOWN', cols[19], 'END'):
    key(k)
got = hits()
check(got == ['DoorTarget38'], "36: column 38 by END (a COLX key) clicks that cell's target", got)
check(fired() == [], "37: ... and no plain row fired with either", '')
# a target re-aimed out of combat follows (OnAttributeChanged mirror)
L.execute('local t = CreateFrame("Button", "NewTarget25", UIParent); t:SetScript("OnClick", function() TGT_HITS[#TGT_HITS + 1] = "NewTarget25" end); WowCompanion.pad.rows.idlg.cells[25]:SetAttribute("clickbutton", t)')
tick(1)
for k in ('DOWN', 'DOWN', cols[19], cols[25]):
    key(k)
got = hits()
check(got == ['NewTarget25'], "38: a re-aimed cell's new target is the one clicked", got)
# a cell with no action (type cleared, as a door when the bags show): nothing
L.execute('WowCompanion.pad.rows.idlg.cells[38]:SetAttribute("type", nil)')
tick(1)
for k in ('DOWN', 'DOWN', cols[19], 'END'):
    key(k)
check(hits() == [], "39: a cell with no action: nothing clicked", '')

# pad31b: the bag row's click cells (the backpack door reads modifiers) get no mirror: no key path for them
L.execute("""
local pad = WowCompanion.pad
DOORHIT = 0
local door = CreateFrame("Button", "DoorBackpack", UIParent); door:SetScript("OnClick", function() DOORHIT = DOORHIT + 1 end)
pad.rows.bag0.cells[5]:SetAttribute("type", "click"); pad.rows.bag0.cells[5]:SetAttribute("clickbutton", door)
pad.keysFarRefresh()
""")
tick(1)
for k in ('DOWN', 'DOWN', cols[3], cols[5]):
    key(k)
check(L.eval('DOORHIT') == 0, "40: a bag row's click cell is not pressed by keys (no mirror)", L.eval('DOORHIT'))

# pad36 / pad36b (2026-11-24, the user: Start wheel -> Map "the game kept the controller"): the Map room's row is a secure far row
# (selector 29) whose action-less cells are HANDLER cells (KEY_HND): the hold cell 0 by keys runs the row's handler, nothing clicked
L.execute("""
local pad = WowCompanion.pad
MAPTAPS = {}
local close = CreateFrame("Button", "MapCloseTarget", UIParent); close:SetScript("OnClick", function() TGT_HITS[#TGT_HITS + 1] = "MapCloseTarget" end)
pad.secureRow("mapw", 40, function(btn, col)
    if col == 5 then btn:SetAttribute("type", "click"); btn:SetAttribute("clickbutton", close) end
end, function(col) MAPTAPS[#MAPTAPS + 1] = col end, { onPress = true })
if pad.buildSecure then pad.buildSecure() end
pad.bindKeys()
pad.keysFarRefresh()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('mapw') == 'DOWN DOWN ' + cols[29], "40a: mapw = DOWN DOWN + selector 29", rows.get('mapw'))
hits(); tick(1)
for k in ('DOWN', 'DOWN', cols[29], cols[0]):
    key(k)
check(L.eval('#MAPTAPS') >= 1 and L.eval('MAPTAPS[#MAPTAPS]') == 0 and hits() == [],
      "40b: the hold cell (no action) by keys runs the Map row's handler for column 0, nothing clicked", L.eval('#MAPTAPS'))
tick(1)
for k in ('DOWN', 'DOWN', cols[29], cols[5]):
    key(k)
check(hits() == ['MapCloseTarget'], "40c: the close cell by keys clicks the map's close button", '')

# pad38 (2026-11-24): the Group Finder's plain rows are far rows 33-35, the last selectors (column keys 33-35, never COLX)
L.execute("""
local pad = WowCompanion.pad
GFTAPS = {}
pad.op("gfw", "gfw", function(key) GFTAPS[#GFTAPS + 1] = key end)
for i = 0, 3 do pad.slotFor("gfw", "k" .. i) end
pad.bindKeys()
pad.keysFarRefresh()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('gfw') == 'DOWN DOWN ' + cols[35], "40d: gfw = DOWN DOWN + selector 35 (the last column key)", rows.get('gfw'))
tick(1)
for k in ('DOWN', 'DOWN', cols[35], cols[3]):
    key(k)
check(L.eval('#GFTAPS') >= 1, "40e: a gfw cell by keys runs the Group Finder's handler", L.eval('#GFTAPS'))

# pad32: the Auras pick and the Talents rows are far rows (selectors 20-22)
L.execute("""
local pad = WowCompanion.pad
for _, n in ipairs({ "aurapick", "talents", "talentn" }) do
    if not pad.rows[n] then pad.op(n, n, function() end) end
    local r, name = pad.rows[n], n
    local h = r.handler
    if type(h) == "function" and not r.wcTest then r.wcTest = true; r.handler = function(k, c) FIRED[#FIRED + 1] = name .. ":" .. tostring(c); return h(k, c) end end
end
pad.bindKeys()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('aurapick') == 'DOWN DOWN ' + cols[20] and rows.get('talents') == 'DOWN DOWN ' + cols[21] and rows.get('talentn') == 'DOWN DOWN ' + cols[22],
      "41: aurapick / talents / talentn = DOWN DOWN + selectors 20 / 21 / 22", (rows.get('aurapick'), rows.get('talents'), rows.get('talentn')))
fired(); tick(1)
for k in ('DOWN', 'DOWN', cols[22], cols[4]):
    key(k)
check(fired() == ['talentn:4'], "42: talentn column 4 by keys", '')

# pad33: the chat rows as far rows (selectors 23-25), unless a row has its own row key
L.execute("""
local pad = WowCompanion.pad
for _, n in ipairs({ "chr", "chs" }) do
    if not pad.rows[n] then pad.op(n, n, function() end) end
    local r, name = pad.rows[n], n
    local h = r.handler
    if type(h) == "function" and not r.wcTest then r.wcTest = true; r.handler = function(k, c) FIRED[#FIRED + 1] = name .. ":" .. tostring(c); return h(k, c) end end
end
pad.bindKeys()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('chr') == 'DOWN DOWN ' + cols[24] and rows.get('chs') == 'DOWN DOWN ' + cols[25], "43: chr / chs = DOWN DOWN + selectors 24 / 25",
      (rows.get('chr'), rows.get('chs')))
fired(); tick(1)
for k in ('DOWN', 'DOWN', cols[25], 'INSERT', 'DOWN', 'DOWN', cols[24], cols[5]):
    key(k)
check(fired() == ['chs:36', 'chr:5'], "44: chs 36 (INSERT) then chr 5, by keys", '')

# pad34: the typing rows stay picked: after the row's keys, one key per letter; "ll" is two letters; any row key ends it
KT = L.eval('WowCompanion.pad.describe().keys')
check(KT['sticky']['chr'] is True and KT['sticky']['qact'] is None, "45: keys.sticky lists the typing rows", '')
fired(); tick(1)
for k in ('DOWN', 'DOWN', cols[24], cols[5], cols[6], cols[6], cols[7]):
    key(k)
check(fired() == ['chr:5', 'chr:6', 'chr:6', 'chr:7'], "46: a word on chr: row keys once, then one key per letter (the double letter twice)", '')
key('INSERT'); key(cols[3])
check(fired() == ['qact:3'], "47: a row key (INSERT) right after typing is a row, never chr's column 36", '')
tick(1)
key(cols[5])
check(fired() == [], "48: after the stickiness ran out a lone column key is nothing", '')
for k in ('DOWN', 'DOWN', cols[24], cols[5]):
    key(k)
tick(3)
key(cols[6])
check(fired() == ['chr:5'], "49: 3 s later the row is no longer picked (KEY_STICKY_TTL 2 s)", '')

# pad39 (2026-11-27, the user: "Start with spellbook spell cells"): THE SECOND FAR BANK. The Spellbook row "spells" (secure, 40 cells:
# handler cells, and "click" cells for the micro buttons / the close) is DOWN DOWN DOWN + selector 0; its handler cells run its handler,
# 36-39 too (navigation keys: COLX_SNIP's handler branch); its click cell clicks its target; DOWN DOWN + selector 0 is still ibuy
L.execute("""
local pad = WowCompanion.pad
SPTAPS = {}
local micro = CreateFrame("Button", "SpellMicroTarget", UIParent); micro:SetScript("OnClick", function() TGT_HITS[#TGT_HITS + 1] = "SpellMicroTarget" end)
pad.secureRow("spells", 40, function(btn, col)
    if col == 2 then btn:SetAttribute("type", "click"); btn:SetAttribute("clickbutton", micro) end
end, function(col) SPTAPS[#SPTAPS + 1] = col end, { onPress = true })
if pad.buildSecure then pad.buildSecure() end
pad.bindKeys()
pad.keysFarRefresh()
""")
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
check(rows.get('spells') == 'DOWN DOWN DOWN ' + cols[0], "50: spells = DOWN DOWN DOWN + selector 0 (the second far bank)", rows.get('spells'))
check(KT and dict(KT['sfx'].items()).get('spells') is True, "50b: spells is published in sfx (its 36-39 by keys)", '')
hits(); fired(); tick(1)
for k in ('DOWN', 'DOWN', 'DOWN', cols[0], cols[7]):
    key(k)
check(L.eval('#SPTAPS') >= 1 and L.eval('SPTAPS[#SPTAPS]') == 7 and hits() == [], "51: a Spellbook handler cell (7) by keys runs its handler, nothing clicked",
      L.eval('#SPTAPS'))
tick(1)
colx37 = KT['cols'][38]
for k in ('DOWN', 'DOWN', 'DOWN', cols[0], colx37):
    key(k)
check(L.eval('SPTAPS[#SPTAPS]') == 37, "52: a handler cell at column 37 (a navigation key) by keys runs its handler", L.eval('SPTAPS[#SPTAPS]'))
tick(1)
for k in ('DOWN', 'DOWN', 'DOWN', cols[0], cols[2]):
    key(k)
check(hits() == ['SpellMicroTarget'], "53: the Spellbook's click cell by keys clicks its target (the micro button)", '')
fired(); tick(1)
for k in ('DOWN', 'DOWN', cols[0], cols[7]):
    key(k)
check(fired() == ['ibuy:7'], "54: DOWN DOWN + selector 0 is still the first bank's ibuy", '')
tick(1)
key('DOWN'); key(cols[4])
check(fired() == ['spick:4'], "55: DOWN alone is still spick", '')

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
