"""encode1 (Sink.lua WC.wrapJson, 2026-11-20): a document wrapped around an already-encoded doc parses to EXACTLY what
WC.encode of the whole table gives (nested tables, unicode, numbers, extra fields, v nil).

    python -B tools/test_wrap_json.py
Needs lupa. Exit code 1 on any failure."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world, docs, ADDONS  # noqa: E402

fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


L, errs = boot_world(files=("safety",), login='')
check(not errs, "0: Safety loads", errs)
sink = open(os.path.join(ADDONS, "WowCompanion", "Sink.lua"), encoding="utf-8").read()
L.globals().loadstring  # noqa: B018
ok = L.execute('''
local f, e = loadstring(%s)
if not f then return tostring(e) end
local ok, err = pcall(f)
return ok and "" or tostring(err)
''' % ('[==[' + sink + ']==]'))
check(ok == "" and L.eval('type(WowCompanion.wrapJson)') == "function", "1: Sink.lua loads, WC.wrapJson exists", ok)

L.execute('''
local WC = WowCompanion
local doc = { list = { { id = 1, n = "Ünïcødé ✓ \\"q\\"", x = 0.25 }, { id = 2, n = "b", sub = { 1, 2.5, -3 } } }, big = 12345678, flag = true, s = "a\\nb" }
A = WC.wrapJson("padmap", 7, "m", WC.encode(doc), { sch = 3, none = nil, w = "x" })
B = WC.encode({ type = "padmap", v = 7, m = doc, sch = 3, w = "x" })
C = WC.wrapJson("calendar", nil, "c", WC.encode(doc))
D = WC.encode({ type = "calendar", c = doc })
''')
g = L.globals()
a, b, c, d = (json.loads(g[k]) for k in "ABCD")
check(a == b, "2: with v and extra fields: same dict", (a, b))
check(c == d and "v" not in c, "3: v nil: same dict, no v key", (c, d))
check(a["m"]["list"][0]["n"] == 'Ünïcødé ✓ "q"', "4: unicode and quotes survive")
print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
