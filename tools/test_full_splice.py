"""FULL1 (Core.lua, 2026-11-20, perf3's ~45 ms frames at each event "full" document): the full document is SPLICED from its parts'
JSON (each part encoded once) instead of one encode of the whole table. Proves, under tools/wowstub.py with the real Safety.lua
encoder and the real Core.lua: the spliced document parses to EXACTLY what one encode of the old table gave (fields, values, the
hud, equipment present or absent); the dedupe still drops an identical bar; WC.snapT carries each part's time.

    python -B tools/test_full_splice.py
Needs lupa. Exit code 1 on any failure."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world, docs, ADDONS  # noqa: E402

fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


L, errs = boot_world(files=("safety",), login='')
check(not errs, "0: Safety loads", errs)
core = open(os.path.join(ADDONS, "WowCompanion", "Core.lua"), encoding="utf-8").read()
L.execute('''
local WC = WowCompanion
HUD = { v = 1, L = { fr = { { e = false, f = 3 }, { e = true } } }, name = "Ünïcødé", n = 3.5 }
SLOTS = { { slot = 1, id = 133, usable = true }, { slot = 2, id = 5, usable = false } }
EQUIP = nil
function WC.collectActionBar()
    WC._hudJsonNow = WC.encode(HUD)
    return { slots = SLOTS, combat = false, page = 1, hud = HUD }
end
function WC.collectPlayer() return { hp = 100, name = "Me", lvl = 12 } end
function WC.collectMap() return { mapID = 1429, x = 0.5, y = 0.25, quests = {}, pois = { { n = "Inn" } } } end
function WC.collectBags() return { bags = { { bag = 0, slots = 20, free = 3 } } } end
function WC.collectEquipped() return EQUIP end
WC.push = WC.push or function() end
''')
load = L.eval('function(src) local f, e = loadstring(src, "@Core.lua"); if not f then error(e) end; return f end')
try:
    load(core)('WowCompanion')
    loaded = True
except Exception as e:
    loaded = False
    print(e)
check(loaded, "1: Core.lua loads")


def expected(reason, equipped):
    L.execute('EQUIP = %s' % equipped)
    s = L.eval('''WowCompanion.encode({ type = "full", v = WowCompanion.VERSION, reason = "%s",
        actionbar = WowCompanion.collectActionBar(), player = WowCompanion.collectPlayer(), map = WowCompanion.collectMapSafe(),
        bags = WowCompanion.collectBags(), equipped = WowCompanion.collectEquipped() })''' % reason)
    return json.loads(s)


n0 = len(docs(L))
L.execute('EQUIP = nil; WowCompanion.snapshot("manual")')
got = [d for d in docs(L)[n0:] if d.get('type') == 'full']
check(len(got) == 1 and got[-1] == expected("manual", "nil"), "2: no equipment: the spliced doc = the old encode", got[-1:] or '')
n0 = len(docs(L))
L.execute('EQUIP = { head = { id = 7, n = "Cap" } }; WowCompanion.snapshot("PLAYER_EQUIPMENT_CHANGED")')
got = [d for d in docs(L)[n0:] if d.get('type') == 'full']
check(len(got) == 1 and got[-1] == expected("PLAYER_EQUIPMENT_CHANGED", '{ head = { id = 7, n = "Cap" } }'),
      "3: with equipment: the spliced doc = the old encode", got[-1:] or '')
n0 = len(docs(L))
r = L.eval('WowCompanion.snapshot("ACTIONBAR_UPDATE_USABLE")')
check(r is False and not [d for d in docs(L)[n0:] if d.get('type') == 'full'], "4: an identical bar is still dropped", r)
L.execute('SLOTS[2].usable = true')
r = L.eval('WowCompanion.snapshot("ACTIONBAR_UPDATE_USABLE")')
check(r is True, "5: a changed bar is sent", r)
T = L.eval('WowCompanion.snapT')
check(T['sent'] and T['reason'] == 'ACTIONBAR_UPDATE_USABLE' and all(T[k] is not None for k in ('bar', 'map', 'bags', 'player', 'send')),
      "6: WC.snapT has each part's time", dict(T.items()))

# beta B1a: the bags' own last document is spliced in (no second collect)
L.execute('WowCompanion.bagsJsonNow = function() return \'{"bags":[{"bag":0,"slots":20,"free":9}],"ctl":{"x":1}}\' end; '
          'WowCompanion.collectBags = function() error("collected again") end')
n0 = len(docs(L))
L.execute('WowCompanion.snapshot("manual")')
got = [d for d in docs(L)[n0:] if d.get('type') == 'full']
check(len(got) == 1 and got[-1]['bags'] == {"bags": [{"bag": 0, "slots": 20, "free": 9}], "ctl": {"x": 1}},
      "7: the bags' last document is spliced, no second collect", got[-1:] or '')

# perf eq1: what is worn is collected again only after an event that changes it, or after 30 s
L.execute('EQN = 0; EQUIP = { head = { id = 9 } }; WowCompanion.collectEquipped = function() EQN = EQN + 1; return EQUIP end')
L.execute('fire("PLAYER_EQUIPMENT_CHANGED"); WowCompanion.snapshot("manual"); WowCompanion.snapshot("manual")')
check(L.eval('EQN') == 1, "8: two full docs, one equipment collect (the second reuses it)", L.eval('EQN'))
got = [d for d in docs(L) if d.get('type') == 'full'][-1]
check(got.get('equipped') == {"head": {"id": 9}}, "9: ... and the reused equipment is in the doc", got.get('equipped'))
L.execute('fire("UPDATE_INVENTORY_DURABILITY"); WowCompanion.snapshot("manual")')
check(L.eval('EQN') == 2, "10: a durability change collects again", L.eval('EQN'))
L.execute('fire("UNIT_INVENTORY_CHANGED", "party1"); WowCompanion.snapshot("manual")')
check(L.eval('EQN') == 2, "11: another unit's inventory does not", L.eval('EQN'))
L.execute('NOW = NOW + 31; WowCompanion.snapshot("manual")')
check(L.eval('EQN') == 3, "12: after 30 s it is collected again (timed text)", L.eval('EQN'))

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
