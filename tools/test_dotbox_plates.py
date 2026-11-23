"""THE DOT BOX'S PLATE PICK (Hub, beta A7, 2026-11-20; the stutter review: up to two walks of 40 nameplate tokens per 0.1 s step).
Under tools/wowstub.py with the real Hub.lua. Proves: the plate over the dot is picked through C_NamePlate.GetNamePlates (only the
plates that exist); the answer is kept for the step (a second ask in the same step walks nothing); a new step asks again; the
player's own plate and a plate beside the dot are never picked; without plate tokens the old 1..40 walk still finds it.

    python -B tools/test_dotbox_plates.py
Needs lupa. Exit code 1 on any failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world  # noqa: E402

fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


L, errs = boot_world()
check(not [e for e in errs if e.startswith('hub')], "0: the world loads (hub)", errs)
L.execute('''
local DB = WowCompanion.dotBox
DB.dot = function() return 500, 300 end
local function plate(tok, x, y)
    return { namePlateUnitToken = tok, IsForbidden = function() return false end, IsShown = function() return true end,
             GetCenter = function() return x, y end, GetEffectiveScale = function() return 1 end }
end
PLATES = { plate("nameplate3", 900, 400), plate("nameplate7", 510, 420), plate("nameplate9", 500, 330) }
LIVE = { nameplate3 = true, nameplate7 = true, nameplate9 = true }
ME = "nameplate9"                                      -- the player's own plate: never picked
ASKED = 0
UIParent.GetEffectiveScale = function() return 1 end           -- the stub has no scale; the game always does
C_NamePlate = {                                         -- a plain table (the stub's is a catch-all)
    GetNamePlates = function() ASKED = ASKED + 1; return PLATES end,
    GetNamePlateForUnit = function(tok) for _, p in ipairs(PLATES) do if p.namePlateUnitToken == tok then return p end end end,
}
UnitExists = function(u) return LIVE[u] == true end
UnitIsUnit = function(a, b) return b == "player" and a == ME end
''')
L.execute('WowCompanion.dotBox.stepN = WowCompanion.dotBox.stepN + 1')
got = L.eval('WowCompanion.dotBox.platePick()')
check(got == 'nameplate7', "1: the plate just above the dot (not the player's, not the one far right)", got)
L.eval('WowCompanion.dotBox.platePick()')
check(L.eval('ASKED') == 1, "2: a second ask in the same step walks nothing", L.eval('ASKED'))
L.execute('WowCompanion.dotBox.stepN = WowCompanion.dotBox.stepN + 1')
L.eval('WowCompanion.dotBox.platePick()')
check(L.eval('ASKED') == 2, "3: a new step asks again", L.eval('ASKED'))
L.execute('for _, p in ipairs(PLATES) do p.namePlateUnitToken = nil end; WowCompanion.dotBox.stepN = WowCompanion.dotBox.stepN + 1')
L.execute('''local real = C_NamePlate.GetNamePlateForUnit
C_NamePlate.GetNamePlateForUnit = function(tok)
    local want = { nameplate3 = 1, nameplate7 = 2, nameplate9 = 3 }
    return want[tok] and PLATES[want[tok]] or nil
end''')
got = L.eval('WowCompanion.dotBox.platePick()')
check(got == 'nameplate7', "4: plates without tokens: the 1..40 walk still finds it", got)
L.execute('LIVE = {}; WowCompanion.dotBox.stepN = WowCompanion.dotBox.stepN + 1')
got = L.eval('WowCompanion.dotBox.platePick()')
check(got is None, "5: no plates: nothing", got)

# hub75: the game's world tooltip of ANOTHER unit gives way to the box; the same unit's is the box; anyone else's stands (counted)
L.execute('''
local DB = WowCompanion.dotBox
DB.pick = function() return "softenemy" end
UnitIsUnit = function(a, b) if b == "player" then return false end; return a == b or (a == "mouseover" and b == "softenemy" and SAME) end
UnitGUID = function(u) return "G-" .. u end
WowCompanionDB = WowCompanionDB or {}; WowCompanionDB.dotBox = nil
TT = { shown = true, owner = UIParent, unit = "mouseover", set = nil }
GameTooltip = {
    IsShown = function() return TT.shown end, GetOwner = function() return TT.owner end,
    GetUnit = function() if TT.unit then return "Name", TT.unit end end,
    SetOwner = function(_, o) TT.owner = o end, SetUnit = function(_, u) TT.set = u; TT.unit = u end,
    Show = function() TT.shown = true end, Hide = function() TT.shown = false end, HookScript = function() end,
}
''')
L.execute('SAME = false; WowCompanion.dotBox.step()')
check(L.eval('TT.set') == 'softenemy', "6: the game's world tooltip of another unit: the box takes over", L.eval('TT.set'))
L.execute('TT.set = nil; GameTooltip.wcDotBox = nil; WowCompanion.dotBox.mine = false; TT.owner = UIParent; TT.unit = "mouseover"; SAME = true; WowCompanion.dotBox.step()')
check(L.eval('TT.set') is None, "7: the game already shows this very unit: left as it is", L.eval('TT.set'))
L.execute('TT.set = nil; TT.owner = { GetName = function() return "ContainerFrame1Item3" end }; TT.unit = nil; SAME = false; WowCompanion.dotBox.step()')
check(L.eval('TT.set') is None, "8: a bag slot's tooltip stands", L.eval('TT.set'))
check(L.eval('WowCompanionDB.dotBox.block["ContainerFrame1Item3"]') == 1, "9: ... and the block is counted by its owner",
      L.eval('WowCompanionDB.dotBox.block and WowCompanionDB.dotBox.block["ContainerFrame1Item3"]'))

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
