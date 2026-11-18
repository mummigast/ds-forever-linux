# SPDX-License-Identifier: GPL-3.0-or-later
# dsf-linux-helper: unofficial Linux helper for DS Forever (GPL-3.0). See README.md.
"""WoW Forever on Linux: find the install, tell where the game is (login / character select / world),
and start it through Battle.net. Ports of DS Forever Desktop's WowLocator, LoginLog and WowFlow.Classify.
Nothing here reads, stores or types credentials."""
import glob, os, re, subprocess, threading, time
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

def steam_client_root(lib_root=None):
    """The Steam client's own folder (has config/config.vdf). A game in a library on another drive still belongs to it."""
    roots = ([Path(lib_root)] if lib_root else []) + STEAM_ROOTS
    return next((r for r in roots if (r / "config/config.vdf").exists()), Path(lib_root) if lib_root else None)

def _vdf_block(text, key):
    """The text inside `"key" { ... }` (first match), braces balanced; None when missing."""
    m = re.search(r'"%s"\s*\{' % re.escape(key), text, re.I)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0); i += 1
    return text[m.end():i - 1]

def compat_tool(client_root, appid):
    """Steam's Proton choice for appid from CompatToolMapping, else its default ("0"); None when unset."""
    try:
        mapping = _vdf_block((client_root / "config/config.vdf").read_text(errors="replace"), "CompatToolMapping")
    except OSError:
        return None
    for key in (str(appid), "0"):
        blk = _vdf_block(mapping or "", key)
        m = re.search(r'"name"\s*"([^"]+)"', blk or "")
        if m:
            return m.group(1)
    return None

def steam_libraries(client_root):
    """Every Steam library folder (libraryfolders.vdf), the client's own first."""
    libs = [client_root]
    try:
        t = (client_root / "steamapps/libraryfolders.vdf").read_text(errors="replace")
        libs += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s*"([^"]+)"', t)]
    except OSError:
        pass
    seen, out = set(), []
    for l in libs:
        k = str(l.resolve()) if l.exists() else str(l).rstrip("/")
        if k not in seen:
            seen.add(k); out.append(l)
    return out

def proton_for(steam_root, appid):
    """The Proton build Steam uses for this appid, as a path to its `proton` script."""
    client = steam_client_root(steam_root)
    tool = compat_tool(client, appid) if client else None
    names = {"proton_hotfix": "Proton Hotfix", "proton_experimental": "Proton - Experimental"}
    commons = [lib / "steamapps/common" for lib in steam_libraries(client)] if client else [Path(steam_root) / "steamapps/common"]
    cands = []
    if tool:
        cands += [c / names.get(tool, tool) / "proton" for c in commons]
        cands += [client / "compatibilitytools.d" / tool / "proton"] if client else []
        m = re.match(r"proton_(\d+)$", tool)          # proton_9 -> "Proton 9.0"
        if m:
            cands += [Path(p) / "proton" for c in commons for p in sorted(glob.glob(str(c / f"Proton {m.group(1)}*")))]
    cands += [c / n / "proton" for n in ("Proton Hotfix", "Proton - Experimental") for c in commons]
    return next((c for c in cands if c.exists()), None)


# ---------------------------------------------------------------- processes and connections
WOW_PROC = os.environ.get("DSF_WOW_PROC", "wow.exe")   # Wine names its processes after the .exe (comm); tests override
BNET_PROC = "battle.net.exe"

def _cmdline(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return ""

def _procs():
    """(pid, comm) of every process, read straight from /proc (far cheaper than several pgrep runs)."""
    out = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                out.append((int(d), Path(f"/proc/{d}/comm").read_text().strip()))
            except OSError:
                pass
    return out

_CMD_RE = {}
def pid_of(name, must_contain=None, procs=None):
    """PID of a process named exactly `name` (case-insensitive; Wine names processes after their .exe), else one whose
    command line runs it (".../Wow.exe" or "C:\\...\\Wow.exe", spaces allowed). must_contain: a text its command line
    must have, e.g. "_forever_" so retail WoW (also Wow.exe) is not taken for WoW Forever."""
    procs = _procs() if procs is None else procs
    me = os.getpid()
    pids = [pid for pid, comm in procs if comm.lower() == name.lower()[:15]]
    if not pids:
        rx = _CMD_RE.setdefault(name, re.compile(r"(^|[\\/])" + re.escape(name) + r"( |$)", re.I))
        # only Wine processes can be it; their comm is not always the .exe (Battle.net's is "CrBrowserMain"), but the
        # binary behind them is Wine's preloader: one readlink each instead of reading every command line
        def wineish(pid, comm):
            c = comm.lower()
            if "wine" in c or "preloader" in c or ".exe" in c:
                return True
            try:
                return "wine" in os.readlink(f"/proc/{pid}/exe")
            except OSError:
                return False
        pids = [pid for pid, comm in procs if pid != me and wineish(pid, comm) and rx.search(_cmdline(pid))]
    if must_contain:
        hits = [p for p in pids if must_contain.lower() in _cmdline(p).lower()]
        # a Wine process's command line normally has its full path; if none says, keep the plain match
        pids = hits or [p for p in pids if "_retail_" not in _cmdline(p).lower() and "_classic" not in _cmdline(p).lower()]
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
        self.lock = threading.Lock()  # the log follower (a worker thread) and the snapshot (another) share this state
    def restart(self):
        with self.lock:
            self.log.reset(); self.last_doc = None
    def line(self, text):
        with self.lock:
            self.log.line(text)
    def doc_seen(self):
        self.last_doc = time.monotonic()
    def snapshot(self, start_state=None, start_why=""):
        with self.lock:
            return self._snapshot(start_state, start_why)
    def _snapshot(self, start_state=None, start_why=""):
        procs = _procs()
        pid = pid_of(WOW_PROC, "_forever_", procs)
        up = pid is not None
        game, auth = connections(pid) if up else (0, 0)
        doc_age = time.monotonic() - self.last_doc if self.last_doc else None
        screen = classify(up, uptime_s(pid) if up else 0, game, auth, self.log, doc_age)
        if not up and start_state == "starting":
            screen = "starting"
        state = "running" if up else (start_state or "stopped")
        bnet = "unknown" if pid_of(BNET_PROC, procs=procs) else "not_running"
        return {"found": True, "flavor": "forever", "running": up, "state": state,
                "why": "" if up else start_why, "screen": screen, "focused": up, "bnet": bnet,
                "needs_you": False, "login_error": (self.log.error or "") if screen == "login" else ""}


# ---------------------------------------------------------------- bringing WoW to the front (KDE Plasma 6, best effort)
KWIN_JS = """
let pick = null;
const wins = workspace.windowList ? workspace.windowList() : workspace.clientList();
for (const w of wins) {
    const cls = (w.resourceClass || "").toString().toLowerCase();
    const cap = (w.caption || "").toString();
    // WoW Forever's own process first (retail/Classic share the class and title); else class or title
    if (PID > 0 && w.pid === PID) { pick = w; break; }
    if (!pick && (cls.indexOf("wow.exe") >= 0 || cap.indexOf("World of Warcraft") === 0)) pick = w;
}
if (pick) {
    if (pick.minimized) pick.minimized = false;
    workspace.activeWindow = pick;
}
"""

def focus_window():
    """Raise WoW's window via a one-shot KWin script. False when not on KDE (other desktops: no-op)."""
    import tempfile, uuid
    name = "dsf_focus_" + uuid.uuid4().hex[:8]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write("const PID = %d;\n" % (pid_of(WOW_PROC, "_forever_") or 0) + KWIN_JS); path = f.name
    def call(obj, method, *args):
        return subprocess.run(["gdbus", "call", "--session", "--dest", "org.kde.KWin", "--object-path", obj,
                               "--method", method, *args], capture_output=True, text=True, timeout=5)
    try:
        r = call("/Scripting", "org.kde.kwin.Scripting.loadScript", path, name)
        m = re.search(r"\((-?\d+),\)", r.stdout)
        if r.returncode != 0 or not m or int(m.group(1)) < 0:
            return False
        call(f"/Scripting/Script{m.group(1)}", "org.kde.kwin.Script.run")
        time.sleep(1)                     # KWin reads and runs the script asynchronously: don't pull it away first
        return True
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            call("/Scripting", "org.kde.kwin.Scripting.unloadScript", name)
        except (OSError, subprocess.SubprocessError):
            pass
        os.unlink(path)


def idle_close_due(running, thor_seen, alone_since, now, idle_s):
    """True when WoW should be closed: it runs, a Thor used it this run, and no Thor has been connected for idle_s seconds
    (0 = never). A WoW started on the PC alone (no Thor seen since it started) is never closed."""
    return bool(idle_s and running and thor_seen and alone_since is not None and now - alone_since >= idle_s)
