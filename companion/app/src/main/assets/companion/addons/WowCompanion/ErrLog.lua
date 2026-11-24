-- WowCompanion / ErrLog.lua (Linux Streaming Edition, 2026-11-24; the user: "got a lot of errors recently, warning from wow that addons were
-- generating lua errors"). READ ONLY, A DIAGNOSTIC: every Lua error the game reports (any add-on's) is counted here, then handed to the
-- game's own error handler exactly as before (the "too many errors" warning, scriptErrors: all unchanged). Kept per session in
-- WowCompanionDB.luaErr (the session before in luaErrPrev): up to MAX distinct errors {msg, n, first, last, where = a short stack}, read
-- after a /reload. Nothing is sent to the app (PadMap's svkeep leaves luaErr / luaErrPrev out: no extra traffic).
local MAX, STACK = 30, 600
local log = { list = {}, dropped = 0 }
local by = {}          -- message -> its entry (not saved)
local busy = false
local db_done = false
local function record(msg)
    if busy then return end
    busy = true
    pcall(function()
        local m = tostring(msg):sub(1, 400)
        local e = by[m]
        local t = GetTime and GetTime() or 0
        if e then
            e.n, e.last = e.n + 1, t
        elseif #log.list < MAX then
            local st = debugstack and debugstack(3, 8, 0) or ""
            e = { msg = m, n = 1, first = t, last = t, where = tostring(st):sub(1, STACK) }
            by[m] = e
            log.list[#log.list + 1] = e
        else
            log.dropped = log.dropped + 1
        end
    end)
    busy = false
end
if type(geterrorhandler) == "function" and type(seterrorhandler) == "function" then
    local prev = geterrorhandler()
    seterrorhandler(function(msg, ...)
        record(msg)
        if type(prev) == "function" then return prev(msg, ...) end
    end)
end
-- THE GAME'S "Your AddOns are experiencing a large number of errors" POP-UP (the user, 2026-11-24: it kept popping up in a fight and the
-- bottom screen could do nothing else). The client calls the global OnExcessiveErrors (Blizzard_DebugUtil: StaticPopup_Show
-- "TOO_MANY_LUA_ERRORS", whose button 1 disables ALL add-ons). Ours counts it here instead (log.excessive); the errors stay recorded.
local function hush() log.excessive = (log.excessive or 0) + 1 end
local function quiet()
    if rawget(_G, "OnExcessiveErrors") ~= hush then _G.OnExcessiveErrors = hush end
end
pcall(quiet)
local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:RegisterEvent("ADDON_LOADED")
-- the game's "<add-on> has been blocked from an action only available to the Blizzard UI": the event names the add-on and the
-- protected function (the pop-up does not); kept as an error line "BLOCKED <addon> <function>" with the stack where it fired
f:RegisterEvent("ADDON_ACTION_BLOCKED")
f:RegisterEvent("ADDON_ACTION_FORBIDDEN")
f:SetScript("OnEvent", function(self, event, name, fn)
    if event == "ADDON_ACTION_BLOCKED" or event == "ADDON_ACTION_FORBIDDEN" then
        record((event == "ADDON_ACTION_BLOCKED" and "BLOCKED " or "FORBIDDEN ") .. tostring(name) .. " " .. tostring(fn)
               .. (InCombatLockdown and InCombatLockdown() and " (in combat)" or ""))
        return
    end
    pcall(quiet)        -- Blizzard_DebugUtil loading after us would put the game's own back
    -- the 2026-11-24 taint hunt left the game's taint log on (taintLog 2, a CVar the client keeps): put back to off ONCE per account
    if event == "PLAYER_LOGIN" then
        pcall(function()
            local db = rawget(_G, "WowCompanionDB")
            if type(db) ~= "table" or db.taintLogReset1 then return end
            db.taintLogReset1 = true
            local get = (type(C_CVar) == "table" and C_CVar.GetCVar) or GetCVar
            if get and get("taintLog") == "2" then
                if type(C_CVar) == "table" and C_CVar.SetCVar then C_CVar.SetCVar("taintLog", "0") else SetCVar("taintLog", "0") end
            end
        end)
    end
    if name ~= "WowCompanion" then return end
    if event ~= "ADDON_LOADED" or db_done then return end
    db_done = true
    if type(rawget(_G, "WowCompanionDB")) ~= "table" then _G.WowCompanionDB = {} end
    local db = _G.WowCompanionDB
    db.luaErrPrev = db.luaErr
    db.luaErr = log
end)
