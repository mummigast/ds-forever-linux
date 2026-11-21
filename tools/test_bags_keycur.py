"""bags-keycur1 (2026-11-21): Bags' KEY-ONLY rows bcur0..bcur5 (TapPad pad30) move the controller's cursor to a slot in ONE step
(column = slot - 1), what bmvq 36 + the bag's name + the bmv cell did in three. Reuses test_bags_bindbox's world (Bags.lua + TapPad)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'test_bags_bindbox.py')).read()
exec(compile(src[:src.index('# ================================================================ 1.')], 'test_bags_bindbox.py', 'exec'))
fails = 0
def ok(c, what):
    global fails
    print(("PASS " if c else "FAIL ") + what)
    if not c: fails += 1
G = boot(bags=True)
names = G.eval('(function() local t={} for k in pairs((WowCompanion.pad and WowCompanion.pad.keyOnly) or {}) do t[#t+1]=k end table.sort(t) return table.concat(t,",") end)()')
ok(names == "bcur0,bcur1,bcur2,bcur3,bcur4,bcur5", "k1. Bags registers bcur0..bcur5 as key-only rows (%s)" % names)
G.execute('WowCompanion._bagsTouch(29)')
G.execute('WowCompanion.pad.keyOnly.bcur0.handler(2)')
cur = dict(G.eval('WowCompanion._bagsCtlDoc().cur').items())
ok(cur.get('bag') == 0 and cur.get('slot') == 3, "k2. bcur0 column 2 = the cursor on bag 0 slot 3, one step (%s)" % cur)
print("test_bags_keycur: %s" % ("ALL PASS" if fails == 0 else "%d failed" % fails))
