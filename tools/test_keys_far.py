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
check(L.eval('#BAGTAPS') >= 2, "19: the row's own tap work ran for each bag press", L.eval('#BAGTAPS'))

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
