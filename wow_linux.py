# SPDX-License-Identifier: GPL-3.0-or-later
# Part of a personal fork of DS Forever (GPL-3.0). See FORK.md.
"""WoW Forever on Linux: find the install, tell where the game is (login / character select / world),
and start it through Battle.net. Ports of DS Forever Desktop's WowLocator, LoginLog and WowFlow.Classify.
Nothing here reads, stores or types credentials."""
import glob, os, re, subprocess, time
from pathlib import Path

HOME = Path.home()
STEAM_ROOTS = [HOME / ".local/share/Steam", HOME / ".steam/steam",
               HOME / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
WOW_SUB = "Program Files (x86)/World of Warcraft/_forever_"


# ---------------------------------------------------------------- finding the game
def find_installs():
    """Every WoW Forever folder in the usual Wine/Proton prefixes, newest log first."""
    pats = []
    for s in STEAM_ROOTS:
        pats.append(str(s / "steamapps/compatdata/*/pfx/drive_c" / WOW_SUB))
    pats += [str(HOME / "Games/*/drive_c" / WOW_SUB),                      # Lutris, Heroic
             str(HOME / "Games/*/*/drive_c" / WOW_SUB),
             str(HOME / ".var/app/com.usebottles.bottles/data/bottles/bottles/*/drive_c" / WOW_SUB),
             str(HOME / ".local/share/bottles/bottles/*/drive_c" / WOW_SUB),
             str(HOME / ".wine/drive_c" / WOW_SUB)]
    found = {Path(p).resolve() for pat in pats for p in glob.glob(pat)}
    def age(p):
        try:
            return (p / "Logs/General.log").stat().st_mtime
        except OSError:
            return 0
    return sorted(found, key=age, reverse=True)

def steam_prefix_of(game_dir):
    """(steam_root, appid) when the game lives in a Steam compatdata prefix, else None."""
    m = re.search(r"^(.*)/steamapps/compatdata/(\d+)/pfx/", str(game_dir))
    return (Path(m.group(1)), int(m.group(2))) if m else None

def proton_for(steam_root, appid):
    """The Proton build Steam uses for this appid (CompatToolMapping), as a path to its `proton` script."""
    names = {"proton_hotfix": "Proton Hotfix", "proton_experimental": "Proton - Experimental"}
    tool = None
    try:
        t = (steam_root / "config/config.vdf").read_text(errors="replace")
        m = re.search(r'"%d"\s*\{[^}]*?"name"\s*"([^"]*)"' % appid, t)
        tool = m.group(1) if m else None
    except OSError:
        pass
    cands = []
    if tool:
        cands += [steam_root / "steamapps/common" / names.get(tool, tool) / "proton",
                  steam_root / "compatibilitytools.d" / tool / "proton"]
        m = re.match(r"proton_(\d+)$", tool)          # proton_9 -> "Proton 9.0"
        if m:
            cands += [Path(p) / "proton" for p in glob.glob(str(steam_root / f"steamapps/common/Proton {m.group(1)}*"))]
    cands += [steam_root / "steamapps/common/Proton Hotfix/proton",
              steam_root / "steamapps/common/Proton - Experimental/proton"]
    return next((c for c in cands if c.exists()), None)


# ---------------------------------------------------------------- processes and connections
WOW_PROC = "wow.exe"            # Wine names its processes after the .exe (comm)
BNET_PROC = "battle.net.exe"

def pid_of(name):
    """PID of a process whose name is exactly `name` (case-insensitive), not any command line mentioning it."""
    r = subprocess.run(["pgrep", "-i", "-x", re.escape(name)], capture_output=True, text=True)
    pids = [int(x) for x in r.stdout.split()]
    if not pids:   # fallback: the .exe as the program path of a command line (".../Wow.exe" or "C:\\...\\Wow.exe")
        r = subprocess.run(["pgrep", "-i", "-f", r"^[^ ]*[\\/]" + re.escape(name) + r"( |$)"], capture_output=True, text=True)
        pids = [int(x) for x in r.stdout.split()]
    return pids[0] if pids else None

def uptime_s(pid):
    try:
        start = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])
        boot = float(Path("/proc/uptime").read_text().split()[0])
        return boot - start / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError):
        return 0.0

def connections(pid):
    """(game, auth): established TCP connections of the game process. game = realm servers (not 80/443/1119),
    auth = Battle.net's 1119 (a sign-in in progress)."""
    r = subprocess.run(["ss", "-Htnp", "state", "established"], capture_output=True, text=True)
    game = auth = 0
    for line in r.stdout.splitlines():
        if f"pid={pid}," not in line:
            continue
        cols = line.split()
        port = cols[3].rsplit(":", 1)[-1] if len(cols) > 3 else ""
        if port == "1119":
            auth += 1
        elif port not in ("80", "443"):
            game += 1
    return game, auth


# ---------------------------------------------------------------- the game's own log lines (LoginLog)
SCREEN_RE = re.compile(r'\[Lua\] Switching to screen="([^"]+)"')
FATAL_RE = re.compile(r'Fatal login error received result="([^"]*)"')

class LoginLog:
    LOGIN = "AccountLogin"
    def __init__(self):
        self.reset()
    def reset(self):
        self.last_screen, self.error, self.signin_started = None, None, False
    def line(self, line):
        if "[Lua] Switching to screen=" in line:
            m = SCREEN_RE.search(line)
            if m:
                self.last_screen, self.error = m.group(1), None
                if self.last_screen == self.LOGIN:
                    self.signin_started = False
            return
        if "[Connection]" not in line:
            return
        if "Glue login started" in line:
            self.signin_started, self.error = True, None
            return
        m = FATAL_RE.search(line)
        if m:
            self.error, self.signin_started = short_error(m.group(1)), False
    @property
    def past_login(self):
        return self.last_screen is not None and self.last_screen != self.LOGIN and self.error is None

def short_error(raw):
    r = re.sub(r"\.\s*\(", " (", (raw or "").strip())
    if r.startswith("(") and r.endswith(")"):
        r = r[1:-1]
    r = r or "unknown"
    return r if len(r) <= 60 else r[:57] + "..."


# ---------------------------------------------------------------- where the game is (WowFlow.Classify)
LOAD_GRACE_S, WORLD_DOC_S = 25, 90

def classify(up, uptime, game_conns, auth_conns, log, doc_age):
    if not up:
        return "none"
    if doc_age is not None and doc_age < WORLD_DOC_S:
        return "world"
    if game_conns >= 2:
        return "world"
    if game_conns == 1:
        return "charselect"
    if log.past_login:
        return "charselect"
    if log.error is not None:
        return "login"
    if auth_conns > 0 or log.signin_started:
        return "signing_in"
    if uptime < LOAD_GRACE_S:
        return "starting"
    return "login"

class WowState:
    """Polled view of the game for the bridge's `wow` message."""
    def __init__(self):
        self.log = LoginLog()
        self.last_doc = None          # monotonic time of the add-on's last document
    def restart(self):
        self.log.reset(); self.last_doc = None
    def doc_seen(self):
        self.last_doc = time.monotonic()
    def snapshot(self, start_state=None, start_why=""):
        pid = pid_of(WOW_PROC)
        up = pid is not None
        game, auth = connections(pid) if up else (0, 0)
        doc_age = time.monotonic() - self.last_doc if self.last_doc else None
        screen = classify(up, uptime_s(pid) if up else 0, game, auth, self.log, doc_age)
        if not up and start_state == "starting":
            screen = "starting"
        state = "running" if up else (start_state or "stopped")
        bnet = "unknown" if pid_of(BNET_PROC) else "not_running"
        return {"found": True, "flavor": "forever", "running": up, "state": state,
                "why": "" if up else start_why, "screen": screen, "focused": up, "bnet": bnet,
                "needs_you": False, "login_error": (self.log.error or "") if screen == "login" else ""}


# ---------------------------------------------------------------- bringing WoW to the front (KDE Plasma 6, best effort)
KWIN_JS = """
const wins = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (const w of wins) {
    const cls = (w.resourceClass || "").toString().toLowerCase();
    if (cls.indexOf("wow.exe") >= 0 || w.caption === "World of Warcraft") {
        if (w.minimized) w.minimized = false;
        workspace.activeWindow = w;
        break;
    }
}
"""

def focus_window():
    """Raise WoW's window via a one-shot KWin script. False when not on KDE (other desktops: no-op)."""
    import tempfile, uuid
    name = "dsf_focus_" + uuid.uuid4().hex[:8]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(KWIN_JS); path = f.name
    def call(obj, method, *args):
        return subprocess.run(["gdbus", "call", "--session", "--dest", "org.kde.KWin", "--object-path", obj,
                               "--method", method, *args], capture_output=True, text=True, timeout=5)
    try:
        r = call("/Scripting", "org.kde.kwin.Scripting.loadScript", path, name)
        m = re.search(r"\((-?\d+),\)", r.stdout)
        if r.returncode != 0 or not m or int(m.group(1)) < 0:
            return False
        call(f"/Scripting/Script{m.group(1)}", "org.kde.kwin.Script.run")
        return True
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            call("/Scripting", "org.kde.kwin.Scripting.unloadScript", name)
        except (OSError, subprocess.SubprocessError):
            pass
        os.unlink(path)
