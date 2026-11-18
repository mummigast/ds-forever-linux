"""TELL MEMORY (Linux Streaming Edition 2026-11-17; the user: "do the tell taps too"), off-device under tools/wowstub.py's game.

    python -B tools/test_tell_memory.py

The app clicked two "tells" after every login although the add-ons could know the answer themselves:
  (a) Quests q35, where Start goes while a room holds (qact 35 / 36): it only repeats PadMap's per-character D-pad toolbar choice
      (WowCompanionSpellsDB.dpad). Quests now derives it at entering the world and says it in guestack {op "start"}.
  (b) PadMap m165, B's pet follow (padtab 39 then 36 / 37): kept in memory only. It is now kept per character in
      WowCompanionSpellsDB.petFollowB and put back 1 s after entering the world, so the padmap says pf.on at once.
Proves: toolbar off -> "game" said at login with no tap; toolbar on / never asked -> "rooms"; the pet word kept when the app says it,
restored at the next login (a fresh game state with the saved table), not for another character, cleared when the app says off.
Needs lupa. Exit code 1 on any failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world, docs  # noqa: E402

_L, _ = boot_world(login='')
KEY = _L.eval('WHO') + "-" + _L.eval('REALM')
fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


def boot(db_lua=''):
    pre = 'CLASS = "HUNTER"\nUNITS.pet = { name = "Wolf", alive = true }\n' + (('WowCompanionSpellsDB = ' + db_lua + '\n') if db_lua else '')
    L, errs = boot_world(pre=pre)
    # the app's first steps (as test_b_pet_follow: trust, the mode), so the padmap carries its full fields
    L.execute('__IN.ACT.trust(); advance(1); __IN.N.setMode(true); advance(1)')
    L.execute('NOW = NOW + 2; tick(0.1); advance(0.6); NOW = NOW + 2; tick(0.1); advance(0.6)')
    return L, errs


def start_words(L):
    return [d.get('why') for d in docs(L) if d.get('type') == 'guestack' and d.get('op') == 'start']


def pf_on(L):
    pm = [d for d in docs(L) if d.get('type') == 'padmap']
    return ((pm[-1].get('m') or {}).get('pf') or {}).get('on') if pm else None


# (a) Start's way derived at login
L, errs = boot('{ dpad = { ["%s"] = false } }' % KEY)
check(not errs, "a0: the world loads", errs)
w = start_words(L)
check(w and w[-1] == "game", "a1: toolbar OFF -> Quests says 'game' at login by itself", w)
L, errs = boot('{ dpad = { ["%s"] = true } }' % KEY)
w = start_words(L)
check(w and w[-1] == "rooms", "a2: toolbar ON -> 'rooms'", w)
L, errs = boot()
w = start_words(L)
check(w and w[-1] == "rooms", "a3: never asked -> 'rooms' (Quests' default, as the app expects)", w)

# (b) B's pet follow memory: dropped at the 1.0.34 merge (2026-11-18); upstream's Smart pet replaced petFollowB

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
