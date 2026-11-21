-- WowCompanion / Sink.lua
-- The export channel: a JSON line out through C_Log.LogMessage -> Logs/General.log,
-- which the Android app tails.
--
-- MEASURED FACTS this file exists to handle:
--   * General.log is BLOCK-BUFFERED at ~48 KiB (49152 B). NOT line-flushed. Nothing reaches
--     disk until the buffer fills, a /reload happens, or the player logs out.
--     Measured: a 150 s run at 10 Hz produced exactly ONE growth event, +49191 B at t=73 s.
--   * There is NO flush trigger. 129 [F] FATAL writes over 25 min produced 2 flushes, both
--     exactly 48 KiB. Severity does not matter.
--   * Therefore: latency = 49152 / emit_rate. THE CONSEQUENCE IS INVERTED FROM INTUITION —
--     compressing or shrinking the payload makes the companion SLOWER. Do not "optimise" bytes.
--   * Writing is effectively free: 124 lines x 500 chars (~64 KB) measured dt = 0.0000 s.
--     So we force a flush on demand by padding, and it costs disk bytes, never frame time.
--   * General.log is TRUNCATED at every client launch, so it never accumulates across sessions.
--   * The engine's own [N][Lua] chatter shares this file, hence the magic prefix.

local ADDON = ...
local WC = _G.WowCompanion

WC.PROTO   = "WCB1"
WC.VERSION = "0.1.0"

local BUFFER_BYTES = 49152          -- measured
local PAD_TARGET   = 61440          -- 1.25x: we estimate our own bytes and cannot see the file,
                                    -- so overshoot. An undershoot costs the ENTIRE push.
local LOG_PREFIX_BYTES = 29         -- "9/25 21:30:45.728  [N][Lua] "
local MAX_LINE = 900                -- C_Log max message length is UNMEASURED; stay conservative
local PADLINE  = string.rep("x", 500)

-- Pad-length probe, run once at load. C_Log's maximum message length has never been
-- measured, so the pad is 500 chars and a flush costs ~118 separate calls. If longer lines
-- survive intact, the same 48 KiB costs a tenth of the calls. The reader checks which of
-- these arrive whole; until then nothing depends on the answer.
function WC.probeLineLengths()
    for _, n in ipairs({ 900, 2000, 4000, 8000, 16000 }) do
        pcall(C_Log.LogMessage, WC.PROTO .. "|probe" .. n .. "|" .. string.rep("p", n) .. "|END")
    end
end

local seq = 0
local pendingBytes = 0

local function raw(s)
    -- seq is incremented BEFORE the call so that a refused line (a secret leaked into the
    -- string) shows up to the reader as a GAP. Otherwise a refusal is invisible on both sides.
    seq = seq + 1
    local line = WC.PROTO .. "|" .. seq .. "|" .. s
    local ok = pcall(C_Log.LogMessage, line)
    pendingBytes = pendingBytes + #line + LOG_PREFIX_BYTES
    return ok
end

-- sink1 (issue #358, 2026-11-15: "Some Cyrillic characters are replaced with question marks (?)"): a long document was cut every
-- MAX_LINE BYTES, so a letter of two or more bytes (Cyrillic, accents, CJK) could be split between two lines; the app decodes each
-- line's bytes on their own, and both halves became U+FFFD ("?"). A cut now steps back off UTF-8 continuation bytes (0x80-0xBF), so
-- every part holds whole letters (a part is at most 3 bytes shorter). An ASCII document is cut exactly where it was.
WC.SINKV = "sink1"
-- the parts of [json], each at most MAX_LINE bytes, never ending inside a UTF-8 letter
function WC.cuts(json, max)
    max = max or MAX_LINE
    local parts, at, len = {}, 1, #json
    while at <= len do
        local e = math.min(at + max - 1, len)
        if e < len then
            local back = e
            while back > at do
                local nb = json:byte(back + 1)
                if not nb or nb < 128 or nb >= 192 then break end
                back = back - 1
            end
            local nb = json:byte(back + 1)
            if nb and (nb < 128 or nb >= 192) then e = back end    -- a run of continuation bytes longer than a part: cut as before
        end
        parts[#parts + 1] = json:sub(at, e)
        at = e + 1
    end
    return parts
end

-- Send one JSON document, fragmenting if it exceeds the safe line length.
-- Fragments carry part=i/n and the reader reassembles before parsing.
function WC.send(json)
    if WC.perf and WC.perf.on then WC.perf.sn = WC.perf.sn + 1; WC.perf.sb = WC.perf.sb + #json end
    if #json <= MAX_LINE then
        return raw("1/1|" .. json)
    end
    local parts = WC.cuts(json, MAX_LINE)
    local n = #parts
    for i = 1, n do
        raw(i .. "/" .. n .. "|" .. parts[i])
    end
    return true
end

-- Force everything written so far out to disk by filling the engine's buffer.
-- Costs ~48-60 KB of log and, measurably, no time. Call this after anything the player
-- is actually waiting to see; never on a timer, and never when nothing is pending.
--
-- COALESCED: several emits in the same frame share ONE flush. The first version paid three
-- separate 60 KB pads for hello + login + manual, two of them 4 ms apart -- 296 pad lines to
-- carry 5 lines of data. A flush scheduled at the end of the frame fixes that for free.
WC.flushMs, WC.flushMax, WC.flushes = 0, 0, 0

function WC.flush()
    if pendingBytes <= 0 then return end
    -- debugprofilestop() has millisecond resolution; GetTime() only advances once a frame,
    -- which is why an earlier measurement of this loop read 0.0000 s and was believed.
    local t0 = debugprofilestop()
    local need = PAD_TARGET - pendingBytes
    if need > 0 then
        local lines = math.ceil(need / (500 + LOG_PREFIX_BYTES))
        for i = 1, lines do
            pcall(C_Log.LogMessage, WC.PROTO .. "|pad|" .. PADLINE)
        end
    end
    pendingBytes = 0
    WC.flushMs = debugprofilestop() - t0
    if WC.flushMs > WC.flushMax then WC.flushMax = WC.flushMs end
    WC.flushes = WC.flushes + 1
end

local lastFlushAt = 0
-- Seconds between flushes. THIS NUMBER IS THE MAP'S REFRESH RATE -- nothing reaches the bottom
-- screen until a flush pushes it out of the engine's 48 KiB buffer.
--
-- It was 2.0, chosen to bound log volume. That is fine for a quest list and hopeless for a map
-- you are trying to walk by: the arrow moved in two-second jumps. 0.3 s puts it just under the
-- position ticker (0.25 s), so in practice every position change flushes, and end-to-end
-- latency is one flush plus one app poll -- about half a second.
--
-- The cost is real and worth stating: a flush is ~60 KB whatever it carries, so moving costs
-- ~200 KB/s of log. It is only paid WHILE MOVING -- collectPos emits nothing when the position
-- key is unchanged, so standing still writes nothing at all. The app truncates the log when it
-- gets large (see LogTail.MAX_LOG_BYTES) so the file cannot grow without bound.
-- 0.15 s. Was 2.0 (a quest list's cadence), then 0.3, and the map still read as laggy when
-- walking: at 0.3 the arrow lands ~3 frames behind where you are. This sits under the 0.1 s
-- position ticker so every sampled step gets its own flush, and end-to-end (flush + the app's
-- 100 ms poll) is about a quarter second.
-- It is paid ONLY WHILE MOVING -- collectPos emits nothing when the position key is unchanged,
-- so standing still still writes zero bytes.
-- 0.2 s. It went 2.0 -> 0.3 -> 0.15 chasing a smooth arrow, and that was the wrong lever:
-- MEASURED at 0.15 it ran at 9.4 flushes/s, 292 KB/s, 2741 pad lines per 56 lines of real
-- data, and cost the game about one dropped frame in ten. Smoothness now comes from the
-- 30 Hz sample ring in Trail.lua, which rides along for free, so the flush only has to be
-- often enough to keep END-TO-END LATENCY down -- and the app hides the rest of that in its
-- playback buffer. Going the other way from here costs frames in the game, not just bytes.
local FLUSH_INTERVAL = 0.2

-- Throttled push: call it as often as you like. It flushes at most every FLUSH_INTERVAL,
-- which bounds both the latency AND the log volume (~24 KB/s at 2 s).
--
-- NOTHING PENDING, NO CLOCK RESET. It used to stamp lastFlushAt even when flush() had nothing
-- to write, so polling it while idle would push the first flush of the next walk back by up
-- to a whole interval -- the worst possible moment to be late, because a START is the one
-- thing the app cannot predict.
--
-- A REFUSAL IS NO LONGER LOST. A push inside the interval used to be dropped outright, and the
-- bytes it was for sat in the buffer until some unrelated push came along. Outdoors that is the
-- next 0.1 s position tick, so nobody noticed; in an INSTANCE there is no map position, the
-- ticker returns early, and the next push was the 15 s heartbeat (found by the cast session).
-- So a refusal with bytes pending arms ONE retry, a backstop for SILENCE:
--  * never more than one outstanding (retryQueued), however many pushes are refused;
--  * it flushes only after a whole FLUSH_INTERVAL with no refused push. While a caller is still
--    pushing, that caller's own next push flushes, exactly as before. MEASURED in the harness
--    (tools/test_sink_rearm.py): a retry fired simply "at the end of the interval" lands on the
--    same instant as the next position tick, flushes the older sample a moment before the fresh
--    one is written, and so raised the walking flush rate from 3.35/s to 4.6/s while making the
--    arrow's latency WORSE. This way the walking flushes are identical to the old ones;
--  * it goes back through this same check, so the cap stays one flush per FLUSH_INTERVAL;
--  * if something else flushed meanwhile it finds nothing pending and does nothing.
-- The callback is made once, here, so a refusal allocates nothing.
local lastRefusedAt = 0
local retryQueued = false
local function retry()
    retryQueued = false
    if pendingBytes <= 0 then return end
    local quiet = GetTime() - lastRefusedAt
    if quiet < FLUSH_INTERVAL then
        retryQueued = true
        C_Timer.After(FLUSH_INTERVAL - quiet, retry)
        return
    end
    WC.pushThrottled()
end

function WC.pushThrottled()
    if pendingBytes <= 0 then return end
    local now = GetTime()
    if now - lastFlushAt < FLUSH_INTERVAL then
        lastRefusedAt = now
        if not retryQueued then
            retryQueued = true
            C_Timer.After(FLUSH_INTERVAL, retry)
        end
        return
    end
    lastFlushAt = now
    WC.flush()
end

local flushQueued = false
-- Ask for a push. Many callers in one frame produce exactly one pad burst.
--
-- THIS GOES THROUGH THE THROTTLE TOO. It did not, and that is why the measured flush rate was
-- 9.4/s against a 0.15 s interval that should have capped it at 6.7: every harvest, chat
-- batch and zone change added its own unthrottled 48 KiB on top of the position stream.
function WC.push()
    if flushQueued then return end
    flushQueued = true
    C_Timer.After(0, function()
        flushQueued = false
        WC.pushThrottled()
    end)
end

-- Send now, push at end of frame.
function WC.emit(tbl)
    WC.send(WC.encode(tbl))
    WC.push()
end

function WC.seqNow() return seq end

-- ---------------------------------------------------------------- spread1 (Linux Edition 2026-11-20, the user: "a small stutter when
-- i initiate combat", option 3: spread the work). perf1 measured the combat-start frame at ~110 ms (normal ~10): every module answers
-- PLAYER_REGEN_DISABLED in the same frame, and the heavy ones (Core's full snapshot, the bags document) each encode tens of KB.
-- WC.spread(key, fn): run fn on a LATER frame, AT MOST ONE spread job per frame, in the order asked. A key already waiting is not
-- queued twice (its first fn runs). With the queue empty a job runs on the next frame, exactly when C_Timer.After(0) would have.
-- Only for work the app can wait a few frames for (documents); never for anything secure or anything the lockdown cuts off.
do
    local q, waiting = {}, {}
    local runner = CreateFrame("Frame")
    runner:Hide()
    runner:SetScript("OnUpdate", function(self)
        local job = table.remove(q, 1)
        if not job then self:Hide(); return end
        waiting[job.k] = nil
        local ok, err = pcall(job.fn)
        if not ok and WC.noteError then pcall(WC.noteError, "spread " .. tostring(job.k) .. ": " .. tostring(err)) end
        if #q == 0 then self:Hide() end
    end)
    function WC.spread(key, fn)
        if waiting[key] then return false end
        waiting[key] = true
        q[#q + 1] = { k = key, fn = fn }
        runner:Show()
        return true
    end
    function WC.spreadQueued() return #q end
end

-- spread2 (2026-11-20, perf3's hitch watcher: a ~140 ms frame at EVERY 15 s heartbeat, out of combat, no event: Core's full document
-- and 18 add-ons' heartbeat riders -- each re-sending its whole list -- all ran in the one frame, inside WC.snapshot). A rider now
-- hooks the snapshot through WC.onSnapshot(key, fn): fn(reason) runs on a later frame through WC.spread, one rider per frame, in
-- the order asked. Same reasons, same documents, just not all at once. (key + reason: two different reasons both run.)
function WC.onSnapshot(key, fn)
    if type(WC.snapshot) ~= "function" then return false end
    hooksecurefunc(WC, "snapshot", function(reason)
        if type(WC.spread) ~= "function" then return fn(reason) end
        WC.spread("ride:" .. key .. ":" .. tostring(reason), function() fn(reason) end)
    end)
    return true
end

-- ---------------------------------------------------------------- perf1 (Linux Edition 2026-11-20, the user: "a small stutter when i
-- initiate combat", option 3: spread the combat-start work). MEASURE FIRST, READ ONLY: from the first PLAYER_REGEN_DISABLED handler
-- (this file's frame registers before the other modules') to the next two frames: how long, how many documents were encoded and
-- sent, how many bytes, the encoder's time. One "perf" document per fight start (and the last 10 in WowCompanionDB.perf).
do
    local P = { on = false, t0 = 0, n = 0, sn = 0, sb = 0, en = 0, ems = 0, frames = 0, f1 = 0 }
    WC.perf = P
    local enc = WC.encode
    if type(enc) == "function" then
        WC.encode = function(...)
            if not P.on then return enc(...) end
            local s = debugprofilestop()
            local r = enc(...)
            P.en = P.en + 1; P.ems = P.ems + (debugprofilestop() - s)
            return r
        end
    end
    local f = CreateFrame("Frame")
    f:RegisterEvent("PLAYER_REGEN_DISABLED")
    f:SetScript("OnEvent", function()
        P.on, P.t0, P.sn, P.sb, P.en, P.ems, P.frames, P.f1, P.f2 = true, debugprofilestop(), 0, 0, 0, 0, 0, 0, 0
        P.last, P.fr = P.t0, {}
        f:Show()
    end)
    -- perf2 (spread1): the work now lands on later frames, so every one of the first 8 frames is timed (fr = each frame's ms,
    -- max_ms = the worst); first_ms / two_ms stay comparable with perf1. q = spread jobs still waiting at the end.
    local FRAMES = 8
    f:SetScript("OnUpdate", function(self)
        if not P.on then self:Hide(); return end
        P.frames = P.frames + 1
        local now = debugprofilestop()
        local ms = now - P.t0
        P.fr[P.frames] = math.floor((now - P.last) + 0.5); P.last = now
        if P.frames == 1 then P.f1 = ms end
        if P.frames == 2 then P.f2 = ms end
        if P.frames < FRAMES then return end
        P.on = false; self:Hide()
        P.n = P.n + 1
        local mx = 0
        for i = 1, #P.fr do if P.fr[i] > mx then mx = P.fr[i] end end
        local r = { type = "perf", v = "perf2", n = P.n, first_ms = math.floor(P.f1 + 0.5), two_ms = math.floor(P.f2 + 0.5),
                    all_ms = math.floor(ms + 0.5), max_ms = mx, fr = P.fr,
                    docs = P.sn, bytes = P.sb, enc = P.en, enc_ms = math.floor(P.ems + 0.5),
                    q = WC.spreadQueued and WC.spreadQueued() or -1,
                    fps = math.floor((GetFramerate and GetFramerate() or 0) + 0.5) }
        if type(WowCompanionDB) == "table" then
            WowCompanionDB.perf = WowCompanionDB.perf or {}
            table.insert(WowCompanionDB.perf, r)
            while #WowCompanionDB.perf > 10 do table.remove(WowCompanionDB.perf, 1) end
        end
        pcall(function() WC.send(WC.encode(r)) end)
    end)
    f:Hide()
end

-- ---------------------------------------------------------------- perf3 (Linux Edition 2026-11-20, the user: combat start "still stuttering,
-- but ALOT less, check code for other instances of these stutters"). READ ONLY, A HITCH WATCHER: every frame that took > HITCH_MS
-- (frame to frame, so it holds every event handler run in between) is reported as a "hitch" document: its ms, the events that fired
-- in it (top 8 by count), the documents encoded in it by type (count, ms), bytes sent, the spread queue, and, where this client has
-- C_AddOnProfiler, each add-on's own time in that frame (top 6). At most one per 2 s; the last 20 in WowCompanionDB.hitch.
-- Loading screens are skipped (they are long frames by nature).
do
    local HITCH_MS, GAP_S = 40, 2
    local H = { ev = {}, dt = {}, bytes = 0, last = 0, sentAt = -1e9, loading = false, n = 0 }
    WC.hitch = H
    local enc = WC.encode
    if type(enc) == "function" then
        WC.encode = function(t, ...)
            local s0 = debugprofilestop()
            local r = enc(t, ...)
            local ty = type(t) == "table" and (rawget(t, "type") or "?") or "?"
            local d = H.dt[ty]
            if not d then d = { 0, 0 }; H.dt[ty] = d end
            d[1] = d[1] + 1; d[2] = d[2] + (debugprofilestop() - s0)
            return r
        end
    end
    local snd = WC.send
    WC.send = function(json, ...) if type(json) == "string" then H.bytes = H.bytes + #json end; return snd(json, ...) end
    local evf = CreateFrame("Frame")
    pcall(evf.RegisterAllEvents, evf)
    evf:SetScript("OnEvent", function(_, e)
        if e == "LOADING_SCREEN_ENABLED" then H.loading = true elseif e == "LOADING_SCREEN_DISABLED" then H.loading = false end
        H.ev[e] = (H.ev[e] or 0) + 1
    end)
    local prof = type(C_AddOnProfiler) == "table" and type(C_AddOnProfiler.GetAddOnMetric) == "function"
                 and type(Enum) == "table" and type(Enum.AddOnProfilerMetric) == "table" and Enum.AddOnProfilerMetric.LastTime
    local names = nil
    local function addonTimes()
        if not prof then return nil end
        if not names then
            names = {}
            local n = (C_AddOns and C_AddOns.GetNumAddOns and C_AddOns.GetNumAddOns()) or 0
            for i = 1, n do
                local nm = C_AddOns.GetAddOnInfo(i)
                if nm and C_AddOns.IsAddOnLoaded(i) then names[#names + 1] = nm end
            end
        end
        local out = {}
        for _, nm in ipairs(names) do
            local ok, v = pcall(C_AddOnProfiler.GetAddOnMetric, nm, prof)
            if ok and type(v) == "number" and v >= 1 then out[#out + 1] = { nm, math.floor(v * 10 + 0.5) / 10 } end
        end
        table.sort(out, function(a, b) return a[2] > b[2] end)
        while #out > 6 do table.remove(out) end
        return out
    end
    local function top(t, n, key)
        local a = {}
        for k, v in pairs(t) do a[#a + 1] = { k, v } end
        table.sort(a, function(x, y) return key(x[2]) > key(y[2]) end)
        local out = {}
        for i = 1, math.min(n, #a) do out[i] = a[i] end
        return out
    end
    local f = CreateFrame("Frame")
    f:SetScript("OnUpdate", function()
        local now = debugprofilestop()
        local ms = now - H.last
        H.last = now
        -- a burst (a fight's start is two heavy frames in a row): up to 3 consecutive hitch frames, then the 2 s gap again
        local burst = H.prevHitch and (H.burst or 0) < 3
        if ms > HITCH_MS and not H.loading and (burst or GetTime() - H.sentAt >= GAP_S) and ms < 5000 then
            H.burst = burst and (H.burst or 0) + 1 or 1
            H.sentAt = GetTime(); H.n = H.n + 1
            local docs = {}
            for _, e in ipairs(top(H.dt, 8, function(v) return v[2] end)) do
                docs[#docs + 1] = { e[1], e[2][1], math.floor(e[2][2] + 0.5) }
            end
            local evs = {}
            for _, e in ipairs(top(H.ev, 8, function(v) return v end)) do evs[#evs + 1] = { e[1], e[2] } end
            local r = { type = "hitch", v = "perf3", n = H.n, ms = math.floor(ms + 0.5), ev = evs, docs = docs, bytes = H.bytes,
                        q = WC.spreadQueued and WC.spreadQueued() or -1, combat = InCombatLockdown() and true or false,
                        fps = math.floor((GetFramerate and GetFramerate() or 0) + 0.5) }
            -- perf4: Core's snapshot ran in this frame: each part's ms (bar, equipment, player, map, bags, send) and its reason
            local ST = WC.snapT
            if type(ST) == "table" and type(ST.at) == "number" and ST.at > now - ms then
                local function r1(v) return type(v) == "number" and math.floor(v * 10 + 0.5) / 10 or nil end
                r.snap = { reason = ST.reason, sent = ST.sent, bar = r1(ST.bar), eq = r1(ST.eq), player = r1(ST.player), map = r1(ST.map),
                           bags = r1(ST.bags), send = r1(ST.send), bytes = ST.bytes }
            end
            local okA, at = pcall(addonTimes)
            if okA and at then r.addons = at end
            if type(WowCompanionDB) == "table" then
                WowCompanionDB.hitch = WowCompanionDB.hitch or {}
                table.insert(WowCompanionDB.hitch, r)
                while #WowCompanionDB.hitch > 20 do table.remove(WowCompanionDB.hitch, 1) end
            end
            H.ev, H.dt, H.bytes = {}, {}, 0
            pcall(function() WC.send(WC.encode(r)) end)
        end
        H.prevHitch = ms > HITCH_MS and H.burst ~= nil and GetTime() == H.sentAt
        H.ev, H.dt, H.bytes = {}, {}, 0
    end)
end
