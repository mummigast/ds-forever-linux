"""X INTERACTS IN A FIGHT TOO (PadMap m186; the user 2026-11-24 in Warsong Gulch: "I cannot pick up or take flags in wsg with X button",
"or loot player corpses with X"), off-device: the router's REAL secure pre-click snippet (PRE) for X (pos 5, wc-interact), game stubbed
(test_smarty.py's way).

    python tools/test_x_interact_fight.py

In the fight state a bare X casts its In-combat spell; with the game's soft-interact target present (a flag, a corpse, a node) it is
Forever's own Interact instead. Y (pos 6) in a fight with a soft-interact target keeps its fight spell. Needs lupa."""
import os
import re
import sys

import lupa

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, '..', 'companion', 'app', 'src', 'main', 'assets', 'companion', 'addons', 'WowCompanionSpells',
                        'PadMap.lua'), encoding='utf-8').read()
fails = 0


def check(ok, name, got=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' else ''))
    if not ok:
        fails += 1


L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute('''
function newtable(...) return {...} end
function mkframe(attrs, refs)
  local f = { a = attrs or {}, refs = refs or {} }
  function f:GetAttribute(k) return self.a[k] end
  function f:SetAttribute(k, v) self.a[k] = v end
  function f:GetFrameRef(k) return self.refs[k] end
  function f:IsShown() return true end
  function f:GetID() return 0 end
  return f
end
TRUE = {}
function SecureCmdOptionParse(s) local c = s:match("^%[(.-)%]"); if TRUE[c] then return "1" end return nil end
function GetGamePadState() return { buttons = {} } end
''')
pre = re.search(r'local PRE = \[=\[(.*?)\]=\]', SRC, re.S).group(1)
run = L.execute('return function(self, button, down) ' + pre + ' end')


def press(pos, conds=(), fight=True):
    L.execute('TRUE = {}')
    for c in conds:
        L.execute('TRUE["%s"] = true' % c)
    attrs = L.table_from({"wc-n-top": 1, "wc-dest-top-1": "ForeverInteractButton", "wc-pos": pos,
                          "wc-state": "fight" if fight else "idle", "wc-fight-type": "spell", "wc-fight-spell": "Wrath"})
    if pos == 5:
        attrs["wc-interact"] = True
    mk = L.eval('mkframe')
    btn = mk(attrs, L.table_from({"wc-hdr": mk(L.table_from({})), "wc-bar-top-1": mk(L.table_from({}))}))
    run(btn, "LeftButton", True)
    return btn.a["wc-kind"], btn.a["type"], btn.a["spell"]


k = press(5)
check(k[0] == "fight" and k[2] == "Wrath", "X in a fight, nothing to interact with: its In-combat spell", k)
k = press(5, ["@softinteract,exists", "combat"])
check(k[0] == "native", "X in a fight with a soft-interact target (the flag, a corpse): Forever's own Interact", k)
k = press(6, ["@softinteract,exists", "combat"])
check(k[0] == "fight", "Y in a fight with a soft-interact target: still its fight spell", k)
k = press(5, ["@softinteract,exists"], fight=False)
check(k[0] == "native", "X out of a fight with a soft-interact target: Forever's Interact (as before)", k)
print("failed: %d" % fails)
sys.exit(1 if fails else 0)
