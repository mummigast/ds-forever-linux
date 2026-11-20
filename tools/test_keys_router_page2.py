"""KEYS PAGE 2 THROUGH THE ROUTER (pad28: the same checks, every key pressed through its binding and secure proxy).
KEYS PAGE 2 (Linux Streaming Edition 2026-11-18; Thor test: the minimap toggle still clicked, and CTRL-SHIFT-PAGEDOWN is bound
in the live game), off-device under tools/wowstub.py's game.

    python -B tools/test_keys_page2.py

Proves: with PAGEDOWN taken by the game, uisw still gets a row key (RIGHT); the "ui" row is published as "RIGHT RIGHT";
RIGHT + column fires uisw, RIGHT RIGHT + column fires ui; a slow second RIGHT does not make page 2; the qact row still works.
Needs lupa. Exit code 1 on any failure."""
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
LAYHIT = {}
pad.secureRow("lay", 40, function() end, function(col) LAYHIT[#LAYHIT + 1] = col end)   -- a stand-in for Hub's layout row (no actions)
if not pad.rows.isell then pad.op("isell", "isell", function() end) end      -- pad26: the vendor's Sell row (Interact's, when loaded)
if not pad.rows.pause then pad.op("pause", "pause", function() end) end      -- UP's own row (Hub's, when loaded)
pad.bindKeys()
FIRED = {}
for name, r in pairs(pad.rows) do
    local h = r.handler
    if type(h) == "function" then r.handler = function(k, c) FIRED[#FIRED + 1] = name .. ":" .. tostring(c); return h(k, c) end end
end
''')
KT = L.eval('WowCompanion.pad.describe().keys')
rows = dict(KT['rows'].items()) if KT else {}
pads = [{'keys': {'cols': [KT['cols'][i] for i in range(1, 41)]}}] if KT else []
check(rows.get('uisw') == 'RIGHT', "1: uisw gets RIGHT although PAGEDOWN is bound", rows)
check(rows.get('ui') == 'RIGHT RIGHT', "2: ui is published as RIGHT RIGHT", rows)
check('keytest' not in rows, "3: keytest gets nothing (its spare PAGEDOWN is bound)", rows)
cols = pads[-1]['keys']['cols'] if pads else []


def press(*ks):
    # pad28: as the game delivers them: CTRL-SHIFT-<key> -> its binding (the secure proxy) -> the router -> the dispatcher
    for k in ks:
        ok = L.eval('tapKey("CTRL-SHIFT-%s")' % k)
        if not ok:
            raise SystemExit("FAIL: CTRL-SHIFT-%s is not bound" % k)


def fired():
    n = int(L.eval('#FIRED'))
    out = [L.eval('FIRED[%d]' % i) for i in range(1, n + 1)]
    L.execute('FIRED = {}')
    return out


press('RIGHT', cols[3])
check(fired() == ['uisw:3'], "4: RIGHT + column fires uisw")
L.execute('NOW = NOW + 1')
press('RIGHT', 'RIGHT', cols[6])
check(fired() == ['ui:6'], "5: RIGHT RIGHT + column fires ui")
L.execute('NOW = NOW + 1')
press('RIGHT', 'RIGHT', cols[6], 'RIGHT', cols[2])
got = fired()
check(got == ['ui:6', 'uisw:2'], "6: a ui press then a uisw press in one line", got)
L.execute('NOW = NOW + 1')
press('RIGHT')
L.execute('NOW = NOW + 0.4')
press('RIGHT', cols[1])
got = fired()
check(got == ['uisw:1'], "7: a slow second RIGHT is a fresh uisw pick, not page 2", got)
L.execute('NOW = NOW + 1')
press('INSERT', cols[5])
got = fired()
check(got == ['qact:5'], "8: qact (INSERT) unchanged", got)

check(rows.get('lay') == 'LEFT LEFT', "9: the plain secure row lay is published as LEFT LEFT", rows)
L.execute('NOW = NOW + 1')
press('LEFT', 'LEFT', cols[38])
check(L.eval('#LAYHIT') == 1 and L.eval('LAYHIT[1]') == 38, "10: LEFT LEFT + column runs lay's onClick", L.eval('#LAYHIT'))
L.execute('NOW = NOW + 1')
press('LEFT', cols[4])
got = fired()
check(got == ['padtab:4'] and L.eval('#LAYHIT') == 1, "11: one LEFT is still padtab", got)
L.execute('local b = WowCompanion.pad.rows.lay.cells[7]; b:SetAttribute("type", "macro"); NOW = NOW + 1')
press('LEFT', 'LEFT', cols[7])
check(L.eval('#LAYHIT') == 1, "12: a lay cell WITH a secure action is never pressed by a key", L.eval('#LAYHIT'))
L.execute('WowCompanion.pad.tenant[WowCompanion.pad.rows.lay.row] = "someoneelse"; NOW = NOW + 1')
press('LEFT', 'LEFT', cols[9])
check(L.eval('#LAYHIT') == 1, "13: not pressed while another row holds lay's row", L.eval('#LAYHIT'))

check(cols[36:40] == ['INSERT', 'HOME', 'END', 'PAGEUP'], "14: columns 36-39 are navigation keys, no punctuation", cols[36:40])
L.execute('NOW = NOW + 1')
press('INSERT', 'INSERT')
got = fired()
check(got == ['qact:36'], "15: INSERT then INSERT = qact column 36", got)
L.execute('NOW = NOW + 1')
press('RIGHT', 'END')
got = fired()
check(got == ['uisw:38'], "16: RIGHT END = uisw column 38 (the friendly-plate switch)", got)
L.execute('NOW = NOW + 1')
press('INSERT')
L.execute('NOW = NOW + 0.4')
press('HOME', cols[2])
got = fired()
check(got == ['qpick:2'], "17: a stale pick: HOME is a fresh row pick, not a column", got)

# pad26 (2026-11-20, "selling does not work"): the vendor's Sell row goes as keys, UP UP; UP alone stays pause
check(rows.get('isell') == 'UP UP', "18: isell is published as UP UP", rows)
L.execute('NOW = NOW + 1')
press('UP', 'UP', cols[12])
got = fired()
check(got == ['isell:12'], "19: UP UP + column fires isell", got)
L.execute('NOW = NOW + 1')
press('UP', cols[4])
got = fired()
check(got == ['pause:4'], "20: one UP is still pause", got)

# pad28: IN A FIGHT the proxies still hand plain rows to the dispatcher (bindings set out of combat, snippets run in the lockdown)
L.execute('fire("PLAYER_REGEN_DISABLED"); COMBAT = true; NOW = NOW + 1')
press('INSERT', cols[9])
got = fired()
check(got == ['qact:9'], "22: in combat INSERT + column = qact (through the proxy)", got)
L.execute('NOW = NOW + 1')
press('RIGHT', 'RIGHT', cols[4])
got = fired()
check(got == ['ui:4'], "23: in combat RIGHT RIGHT + column = ui (page 2 through the proxies)", got)
check(not L.eval('#SNIPERR > 0') and not L.eval('#HANDLEERR > 0'), "24: no snippet or frame-handle error in combat",
      (L.eval('SNIPERR[1]'), L.eval('HANDLEERR[1]')))
L.execute('COMBAT = false')

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
