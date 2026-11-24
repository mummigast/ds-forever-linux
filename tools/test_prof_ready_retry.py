"""Professions p28 (2026-11-24, the user: "professions tab ... wont display on bottom screen until it has viewed it once"): an open
profession whose recipe data is not ready (IsTradeSkillReady false) is looked at again every 0.25 s for at most 5 s. Harness of
test_prof_voice.py. Run: python -B tools/test_prof_ready_retry.py
"""
import os
import sys
from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, 'companion', 'app', 'src', 'main', 'assets', 'companion', 'addons', 'WowCompanionProfessions',
                        'Professions.lua'), encoding='utf-8').read()
passes = fails = 0


def check(ok, what, got=None):
    global passes, fails
    if ok:
        passes += 1; print('PASS', what)
    else:
        fails += 1; print('FAIL', what, '->', got)


L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r'''
local stub
stub = setmetatable({}, { __index = function() return stub end, __call = function() return stub end })
setmetatable(_G, { __index = function(_, k) return stub end })
NOW = 100
function GetTime() return NOW end
TIMERS = {}
C_Timer = { NewTicker = function() return stub end, NewTimer = function() return stub end,
            After = function(s, fn) TIMERS[#TIMERS + 1] = { at = NOW + s, fn = fn } end }
function run(dt)
    local upto = NOW + (dt or 0)
    for _ = 1, 10000 do
        local bi, best = nil, nil
        for i, t in ipairs(TIMERS) do if t.at <= upto and (not best or t.at < best.at) then bi, best = i, t end end
        if not bi then break end
        table.remove(TIMERS, bi)
        if best.at > NOW then NOW = best.at end
        pcall(best.fn)
    end
    NOW = upto
end
HANDLERS = {}
function CreateFrame(kind, name)
    local fr = setmetatable({ attrs = {}, name = name, ev = {} }, { __index = function() return stub end })
    function fr:SetScript(k, fn) if k == "OnEvent" then HANDLERS[#HANDLERS + 1] = { fr = fr, fn = fn } end end
    function fr:RegisterEvent(e) self.ev[e] = true; return true end
    function fr:SetAttribute(k, v) self.attrs[k] = v end
    function fr:GetName() return self.name end
    if name then _G[name] = fr end
    return fr
end
function fire(ev, ...) for _, h in ipairs(HANDLERS) do if h.fr.ev[ev] then pcall(h.fn, h.fr, ev, ...) end end end
COMBAT = false
function InCombatLockdown() return COMBAT end
function UnitAffectingCombat() return COMBAT end
function UnitName() return "Shamy" end
function GetRealmName() return "Forever" end
TRACE = {}
for _, n in ipairs({ "SetBinding", "SaveBindings", "DeleteMacro", "CreateMacro", "EditMacro", "SetCVar", "ShowUIPanel", "HideUIPanel",
                     "ToggleProfessionsBook", "CloseTradeSkill", "SetOverrideBinding", "SetOverrideBindingClick" }) do
    _G[n] = function() TRACE[#TRACE + 1] = n end
end
CLOSEVIS = true
ProfessionsFrame = { IsShown = function() return true end, IsVisible = function() return true end }
ProfessionsFrameCloseButton = { IsVisible = function() return CLOSEVIS end }
ProfessionMicroButton = { IsVisible = function() return true end }
SENT, SPECS, ROWS, SLOTS = {}, {}, {}, {}
local nslot = {}
WowCompanion = {
    S = function(fn) local ok, v = pcall(fn); if ok then return v end end,
    SN = function(fn) local ok, v = pcall(fn); if ok and type(v) == "number" then return v end end,
    CALL = function(fn, ...) return pcall(fn, ...) end,
    send = function(t) SENT[#SENT + 1] = t end, encode = function(t) return t end, push = function() end,
    isPlain = function() return true end, ABSENT = {}, SECRET = {}, THREW = {},
    pad = { op = function(name, ns, h) ROWS[name] = h; return {} end, secureRow = function() return {} end,
            slotFor = function(ns, key)
                SLOTS[ns] = SLOTS[ns] or {}
                if SLOTS[ns][key] == nil then nslot[ns] = (nslot[ns] or -1) + 1; SLOTS[ns][key] = nslot[ns] end
                return SLOTS[ns][key]
            end,
            describe = function() return { rows = { prof = 37 } } end, onLayout = function() end, retain = function() end },
    capture = { version = 17,
                take = function(g, spec) SPECS[#SPECS + 1] = spec; return true end,
                release = function() return true end,
                state = function() return { holder = "professions" } end,
                bnext = function(g, w) BNEXT = w end,
                refused = function() REFUSED = (REFUSED or 0) + 1; return true end,
                pass = function() return true end },
}
function lastSpec() return SPECS[#SPECS] end
function lastAck(op) for i = #SENT, 1, -1 do local t = SENT[i]; if t.type == "profack" and t.op == op then return t end end end
function lastDoc() for i = #SENT, 1, -1 do local t = SENT[i]; if t.type == "prof" then return t.p end end end
function passHas(spec, k) if not spec.pass then return false end; for _, x in ipairs(spec.pass) do if x == k then return true end end; return false end
function extraHas(spec, k) if not spec.extra then return false end; for _, x in ipairs(spec.extra) do if x == k then return true end end; return false end
''')
load = L.eval('function(src) local f, e = loadstring(src, "@Professions.lua"); if not f then error(e) end; return f end')
ok_load = True
try:
    load(SRC)('WowCompanionProfessions')
except Exception as e:  # noqa: BLE001
    ok_load = False; print(e)
check(ok_load, "Professions.lua loads (stand-in game) with no error")
check(L.eval('ROWS.prof ~= nil'), "its control row registered")
L.execute('fire("PLAYER_LOGIN"); fire("TRADE_SKILL_SHOW"); run(1)')


# p28 (2026-11-24, the user: a profession showed on the bottom screen only from its second viewing): while the window is open and the
# game's recipe data is not ready, the book is looked at again every 0.25 s, for 5 s at most; then it stops
L.execute("""
READY = false; ASKS = 0
C_TradeSkillUI = setmetatable({ IsTradeSkillReady = function() ASKS = ASKS + 1; return READY end }, getmetatable(_G))
fire("TRADE_SKILL_CLOSE"); run(1); ASKS = 0
fire("TRADE_SKILL_SHOW"); run(2)
""")
a2 = L.eval('ASKS')
check(a2 >= 6, "p28: data not ready -> asked again every 0.25 s (%d asks in 2 s)" % a2, a2)
L.execute('run(10); A10 = ASKS; run(10)')
check(L.eval('ASKS') == L.eval('A10') and L.eval('A10') <= 26, "p28: ... and it stops after 5 s (%s asks)" % L.eval('A10'), L.eval('ASKS'))
L.execute('fire("TRADE_SKILL_CLOSE"); run(1); ASKS = 0; run(3)')
check(L.eval('ASKS') == 0, "p28: closed -> no more asks", L.eval('ASKS'))
print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
