"""KEYS PAGE 2 (Linux Streaming Edition 2026-11-18; Thor test: the minimap toggle still clicked, and CTRL-SHIFT-PAGEDOWN is bound
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
    for k in ks:
        L.execute('_G.WowCompanionPadKeys:GetScript("OnClick")(_G.WowCompanionPadKeys, "%s", true)' % k)


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

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
