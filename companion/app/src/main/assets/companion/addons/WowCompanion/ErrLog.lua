-- WowCompanion / ErrLog.lua (Linux Streaming Edition, 2026-11-24; the user: "got a lot of errors recently, warning from wow that addons were
-- generating lua errors"). READ ONLY, A DIAGNOSTIC: every Lua error the game reports (any add-on's) is counted here, then handed to the
-- game's own error handler exactly as before (the "too many errors" warning, scriptErrors: all unchanged). Kept per session in
-- WowCompanionDB.luaErr (the session before in luaErrPrev): up to MAX distinct errors {msg, n, first, last, where = a short stack}, read
-- after a /reload. Nothing is sent to the app (PadMap's svkeep leaves luaErr / luaErrPrev out: no extra traffic).
local MAX, STACK = 30, 600
local log = { list = {}, dropped = 0 }
local by = {}          -- message -> its entry (not saved)
local busy = false
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
local f = CreateFrame("Frame")
f:RegisterEvent("ADDON_LOADED")
f:SetScript("OnEvent", function(self, _, name)
    if name ~= "WowCompanion" then return end
    self:UnregisterEvent("ADDON_LOADED")
    if type(rawget(_G, "WowCompanionDB")) ~= "table" then _G.WowCompanionDB = {} end
    local db = _G.WowCompanionDB
    db.luaErrPrev = db.luaErr
    db.luaErr = log
end)
