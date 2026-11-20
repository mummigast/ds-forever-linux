#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# dsf-linux-helper: unofficial Linux helper for DS Forever (GPL-3.0). See README.md.
"""DS Forever bridge for Linux: lets the DS Forever app on an AYN Thor use a Linux PC that already
streams WoW Forever with Sunshine. Replaces the bridge part of DS Forever Desktop (Windows only).

Speaks docs/STREAM_BRIDGE_PROTOCOL.md v1 (DS Forever's bridge protocol):
  - follows WoW's General.log, reassembles the add-on's WCB1 documents (port of WcbAssembler.cs)
  - WebSocket server on <pc>:48210/v1/ws: ws and wss on the same port (self-signed cert, fingerprint in mDNS/welcome)
  - pairing: 6-digit code shown here, HMAC proof from the Thor, token stored in the state file
  - mDNS advert _dsforever._tcp via avahi-publish
  - Moonlight PIN to Sunshine: automatic via Sunshine's API when SUNSHINE_USER/SUNSHINE_PASS are set,
    otherwise printed for you to type into Sunshine's web UI (https://localhost:47990 → PIN)

Never touches credentials, bindings, macros or CVars. Video/audio/controller stay Moonlight <-> Sunshine.
"""
import argparse, asyncio, base64, re, shutil, hashlib, hmac, json, os, secrets, socket, ssl, subprocess, sys, time, urllib.request
from pathlib import Path

ENV_FILE = Path.home() / ".config/dsf-bridge/env"
if ENV_FILE.exists():
    for _l in ENV_FILE.read_text().splitlines():
        _k, _sep, _v = _l.strip().partition("=")
        if _sep and not _k.startswith("#"):
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

import websockets
import paircode, wow_linux
import addons, pc_addons
from websockets.asyncio.server import serve

PROTO = 1
VERSION = "linux-0.2"
PORT = int(os.environ.get("DSF_PORT", "48210"))
def _game_dir():
    if os.environ.get("DSF_WOW_DIR"):
        return Path(os.environ["DSF_WOW_DIR"])
    found = wow_linux.find_installs()
    return found[0] if found else Path("/nonexistent/World of Warcraft/_forever_")
GAME_DIR = _game_dir()
LOG = GAME_DIR / "Logs" / "General.log"
STATE = Path(os.environ.get("DSF_STATE", Path.home() / ".config/dsf-bridge/state.json"))
SUNSHINE_DIRS = [Path.home() / ".var/app/dev.lizardbyte.app.Sunshine/config/sunshine",   # Flatpak
                 Path.home() / ".config/sunshine"]                                        # native / AppImage
SUNSHINE_DIR = next((d for d in SUNSHINE_DIRS if (d / "sunshine.conf").exists()), SUNSHINE_DIRS[1])

def _sunshine_port():
    try:
        m = re.search(r"^\s*port\s*=\s*(\d+)", (SUNSHINE_DIR / "sunshine.conf").read_text(), re.M)
        return int(m.group(1)) if m else 47989
    except OSError:
        return 47989
_base = _sunshine_port()
SUNSHINE_HTTP, SUNSHINE_HTTPS, SUNSHINE_WEB = _base, _base - 5, _base + 1   # Sunshine's own port layout
SUNSHINE_STATE = SUNSHINE_DIR / "sunshine_state.json"
MAX_BACKLOG_BYTES = 8 * 1024 * 1024
MAX_BACKLOG_DOCS = 50_000


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- state (devices, host id)
def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}

def write_private(path, text):
    """Write a file that is mode 600 from its first byte (no moment where others can read it)."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)

def save_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    write_private(tmp, json.dumps(s, indent=1))
    tmp.replace(STATE)

state = load_state()
state.setdefault("host_id", secrets.token_hex(16))
state.setdefault("devices", {})          # device_id -> {"token_sha": ..., "name": ...}
save_state(state)

def sunshine_uniqueid():
    try:
        d = json.loads(SUNSHINE_STATE.read_text())
        return d.get("root", d).get("uniqueid")
    except Exception:
        return None

PC_NAME = os.environ.get("DSF_PC_NAME") or socket.gethostname().split(".")[0]


# ---------------------------------------------------------------- WCB1 reassembly (WcbAssembler.cs)
DAYS_BEFORE = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

def game_time(raw, at):
    try:
        head = raw[:at].strip()
        date, rest = head.split(" ", 1)
        t = rest.strip().split(" ", 1)[0]
        mon, day = (int(x) for x in date.split("/"))
        h, mi, sec = t.split(":")
        doy = DAYS_BEFORE[max(0, min(11, mon - 1))] + day
        return ((doy * 24 + int(h)) * 60 + int(mi)) * 60_000 + int(float(sec) * 1000)
    except Exception:
        return -1

DIGITS = re.compile(r"^[0-9]{1,9}$")

class Assembler:
    MAGIC = "WCB1|"
    def __init__(self):
        self.reset()
    def reset(self):
        self.frags, self.order, self.last = {}, [], -1
    def line(self, raw, out):
        raw = raw.rstrip("\r\n")
        i = raw.find(self.MAGIC)
        if i < 0:
            return
        body = raw[i + len(self.MAGIC):]
        if body.startswith("pad|"):
            return
        parts = body.split("|", 2)
        if len(parts) < 3 or not DIGITS.match(parts[0]):
            return
        seq, spec, payload = int(parts[0]), parts[1], parts[2]
        if self.last >= 0 and seq != self.last + 1:
            out.append({"t": "gap", "seq": seq, "expected": self.last + 1})
        self.last = seq
        a, _, b = spec.partition("/")
        if not (DIGITS.match(a) and DIGITS.match(b)):
            return
        idx, total = int(a), int(b)
        if total < 1 or total > 4096 or idx < 1 or idx > total:   # cap: a bad line must not allocate gigabytes
            return
        gt = game_time(raw, i)
        if total == 1:
            out.append({"t": "doc", "seq": seq, "gt": gt, "doc": payload}); return
        key = seq - (idx - 1)
        slots = self.frags.get(key)
        if slots is None or len(slots) != total:
            slots = [None] * total
            self.frags[key] = slots
            self.order.append(key)
            while len(self.frags) > 256 and self.order:
                self.frags.pop(self.order.pop(0), None)
        slots[idx - 1] = payload
        if all(s is not None for s in slots):
            del self.frags[key]
            out.append({"t": "doc", "seq": key, "gt": gt, "doc": "".join(slots)})


# ---------------------------------------------------------------- log follower (LogTailer.cs, simplified for Linux)
class Tailer:
    def __init__(self, path):
        self.path, self.asm = path, Assembler()
        self.offset, self.ino, self.head, self.carry = None, None, b"", b""
    def poll(self):
        """Return a list of messages (doc/gap/log restart)."""
        out = []
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return out
        with open(self.path, "rb") as f:
            head = f.read(64)
            restart = self.offset is not None and (st.st_ino != self.ino or st.st_size < self.offset
                                                   or (len(self.head) == 64 and head[:64] != self.head))
            if self.offset is None or restart:
                if restart:
                    out.append({"t": "log", "event": "restart", "path": str(self.path), "flavor": "forever"})
                    log("WoW restarted, resyncing")
                    wow.restart()             # before the new log's lines are read, so their screen state counts
                self.asm.reset(); self.carry = b""
                self.offset = 0 if restart else max(0, st.st_size - MAX_BACKLOG_BYTES)
                self.ino = st.st_ino
            self.head = head
            if st.st_size <= self.offset:
                return out
            f.seek(self.offset)
            data = f.read(min(st.st_size - self.offset, MAX_BACKLOG_BYTES))
            self.offset += len(data)
        data = (self.carry + data).replace(b"\0", b"")
        lines = data.split(b"\n")
        self.carry = lines.pop()[-1024 * 1024:]
        for ln in lines:
            text = ln.decode("utf-8", "replace")
            wow.line(text)
            self.asm.line(text, out)
        return out


# ---------------------------------------------------------------- sessions
sessions = {}          # device_id -> websocket
feed_lock = asyncio.Lock()   # a joining Thor gets welcome + backlog before any live document
backlog = []           # messages since the current log began
pairing = {"code": None, "wrong": 0, "locked_at": 0.0, "pin": None}
LOCK_S = 300        # a Thor (IP address) with 5 wrong codes waits this long
PER_IP, TOTAL = 5, 30   # wrong codes allowed per address / in total per code (then everyone waits and a new code comes up)
misses = {}         # ip -> [wrong codes, time of the last one]
PEERS = {}          # front door: local port of the inner connection -> the real client address

def attempts_left(ip):
    n, at = misses.get(ip, [0, 0.0])
    if n and time.time() - at > LOCK_S:              # old misses expire
        misses.pop(ip, None); n = 0
    if pairing["locked_at"] and time.time() - pairing["locked_at"] > LOCK_S:
        new_code()
    return 0 if pairing["locked_at"] else max(0, PER_IP - n)

def new_code():
    pairing["code"] = f"{secrets.randbelow(1_000_000):06d}"
    pairing["wrong"] = 0
    for ip in [k for k, (n, _) in misses.items() if n < PER_IP]:
        misses.pop(ip)                              # a new code: full attempts again, except addresses still locked out
    pairing["locked_at"] = 0.0
    log(f"*** Pairing code for the Thor: {pairing['code'][:3]} {pairing['code'][3:]} ***")
    net = paircode.encode_tail(lan_addresses(), PORT)
    if net: log(f"*** Other network (Thor on WireGuard / another subnet): {paircode.groups(net)} ***")
    code_file = STATE.parent / "pairing-code.txt"
    write_private(code_file, pairing["code"] + "\n")

STEAM_PREFIX = wow_linux.steam_prefix_of(GAME_DIR)          # (steam_root, appid) of a Steam/Proton install
PROTON = Path(os.environ["DSF_PROTON"]) if os.environ.get("DSF_PROTON") else (
    wow_linux.proton_for(*STEAM_PREFIX) if STEAM_PREFIX else None)
wow = wow_linux.WowState()
ADDONS_DIR = GAME_DIR / "Interface" / "AddOns"
addon_lock = asyncio.Lock()

# the Streaming Edition's own copy: this helper lives in the app's repository, so its add-ons match the app that was built
REPO_ADDONS = Path(__file__).resolve().parent.parent / "companion/app/src/main/assets/companion"

def addon_source():
    """DSF_ADDONS_SRC (a folder with manifest.txt + addons/), else the repository's own copy (the app built from the same
    checkout), else upstream DS Forever's latest release (verified)."""
    if os.environ.get("DSF_ADDONS_SRC"):
        return Path(os.environ["DSF_ADDONS_SRC"])
    if (REPO_ADDONS / "manifest.txt").is_file() and (REPO_ADDONS / "addons").is_dir():
        return REPO_ADDONS
    return addons.fetch_upstream(log)

async def addon_pass(force=False, allow_new=False, thor_set=0):
    """Install/update DS Forever's add-ons in the PC game. allow_new only when a Thor is actually using DS Forever."""
    async with addon_lock:
        try:
            src = await asyncio.to_thread(addon_source)
            src_set = addons.parse_manifest((Path(src) / "manifest.txt").read_text())[0]
            if thor_set > src_set and not os.environ.get("DSF_ADDONS_SRC"):
                try:                                    # the Thor's APK is newer than our copy: take upstream's release
                    up = await asyncio.to_thread(addons.fetch_upstream, log)
                    if addons.parse_manifest((up / "manifest.txt").read_text())[0] > src_set:
                        src = up
                except Exception as e:
                    log("upstream add-ons:", e)
            msg = await asyncio.to_thread(addons.install, src, ADDONS_DIR, force, allow_new, log)
        except Exception as e:
            msg = f"add-on update failed: {e}"
        if thor_set and addons.installed_set(ADDONS_DIR) < thor_set:
            msg += f" (the Thor has set {thor_set}; update this bridge's add-on source)"
        return msg
# ---------------------------------------------------------------- the Thor's add-ons on the PC (pc_addons.py; Linux Edition 2026-11-20)
PC_ADDONS_REC = STATE.parent / "pc-addons.json"
PC_ADDONS_CACHE = Path.home() / ".cache/dsf-bridge/pc-addons"
pc_want = {"m": None}                                 # the latest "addons_want" (run again before WoW starts and when it closes)

async def pc_addons_pass(ws=None):
    m = pc_want["m"]
    if not m:
        return
    async with addon_lock:
        try:
            res = await asyncio.to_thread(pc_addons.run, m, GAME_DIR, PC_ADDONS_REC, PC_ADDONS_CACHE, wow_running(), log)
        except Exception as e:
            res = {"t": "addons_pc", "state": "done", "ok": False, "line": f"add-ons on the PC failed: {e}", "items": []}
    try:
        if ws is not None:
            await send(ws, res)
        else:
            await broadcast([res])
    except Exception:
        pass

START_CMD = os.environ.get("DSF_START_CMD")   # optional: your own shell command that starts WoW Forever
wow_start = {"state": None, "why": "", "at": 0.0}

def session_env():
    """The desktop session's current environment (DISPLAY, WAYLAND_DISPLAY…): a service started at boot, before the
    desktop, doesn't have it, and Steam/Proton need it to open windows."""
    env = dict(os.environ)
    try:
        out = subprocess.run(["systemctl", "--user", "show-environment"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            k, sep, v = line.partition("=")
            if sep and k in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP",
                             "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"):
                env[k] = v
    except (OSError, subprocess.SubprocessError):
        pass
    return env

def bnet_running():
    return wow_linux.pid_of(wow_linux.BNET_PROC) is not None

async def start_wow(retried=False):
    """Start WoW Forever like Desktop does: Battle.net first (via its Steam shortcut), then
    Battle.net.exe --exec="launch WoWF" in the same Proton prefix. Never touches credentials."""
    if wow_running() or wow_start["state"] == "starting" or time.time() - wow_start["at"] < 120:
        return
    wow_start.update(state="starting", why="", at=time.time())
    await pc_addons_pass()                            # the Thor's wanted add-ons in before WoW reads its AddOns folder
    await broadcast([{"t": "wow", **_info()["wow"]}, {"t": "status", "text": "Starting WoW on your PC…"}])
    log("Starting WoW Forever")
    try:
        if START_CMD:
            subprocess.Popen(START_CMD, shell=True, start_new_session=True, env=session_env())
        elif not (STEAM_PREFIX and PROTON):
            raise RuntimeError("can't start WoW here: set DSF_START_CMD (WoW is not in a Steam/Proton prefix)")
        else:
            steam_root, appid = STEAM_PREFIX
            stale = bnet_running()                       # a Battle.net already up (maybe from hours ago)
            if not stale:
                gameid = (appid << 32) | 0x02000000      # a non-Steam shortcut's game id
                url = f"steam://rungameid/{gameid}"
                client = wow_linux.steam_client_root(steam_root)
                if "/.var/app/com.valvesoftware.Steam/" in str(client):
                    cmd = ["flatpak", "run", "com.valvesoftware.Steam", url]
                elif shutil.which("steam"):
                    cmd = ["steam", url]
                else:
                    cmd = ["xdg-open", url]
                subprocess.Popen(cmd, start_new_session=True, env=session_env(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(60):
                    await asyncio.sleep(2)
                    if bnet_running():
                        break
                await asyncio.sleep(10)   # let Battle.net sign in / settle
            if wow_running():
                wow_start.update(state=None); return
            launch_wowf(steam_root, appid)
            if stale and not retried:
                # an old Battle.net can ignore the launch (seen 2026-11-17: up since the evening before, no WoW): after a
                # minute, close that Proton session and start fresh once
                for _ in range(30):
                    await asyncio.sleep(2)
                    if wow_running():
                        wow_start.update(state=None); return
                log("Battle.net ignored the launch: restarting it")
                await broadcast([{"t": "status", "text": "Restarting Battle.net on your PC…"}])
                n = await asyncio.to_thread(close_prefix, steam_root, appid)
                log(f"closed {n} processes of the old session")
                wow_start.update(state=None, at=0)
                await asyncio.sleep(3)
                return await start_wow(retried=True)
        for i in range(1, 91):
            await asyncio.sleep(2)
            if wow_running():
                wow_start.update(state=None); return
            # a Battle.net that has just started ignores a launch until its home page is up (2026-11-17: sent ~12 s after
            # it appeared, nothing; the same command by hand a few minutes later started WoW at once): send it again
            if not START_CMD and STEAM_PREFIX and PROTON and i % 20 == 0 and bnet_running():
                log("no WoW yet: asking Battle.net again")
                launch_wowf(*STEAM_PREFIX)
        wow_start.update(state="start_failed", why="no WoW window after 3 minutes (Battle.net may need you to sign in on the PC)")
    except Exception as e:
        wow_start.update(state="start_failed", why=str(e))
    log("WoW start failed:", wow_start["why"])
    await broadcast([{"t": "wow", **_info()["wow"]}, {"t": "status", "text": "WoW didn't start: " + wow_start["why"]}])

def launch_wowf(steam_root, appid):
    """Battle.net.exe --exec="launch WoWF" in WoW's Proton prefix ("launch_uid wowf" only selects the game)."""
    env = dict(session_env(), STEAM_COMPAT_DATA_PATH=str(steam_root / f"steamapps/compatdata/{appid}"),
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(wow_linux.steam_client_root(steam_root)))
    subprocess.Popen([str(PROTON), "run", r"C:\Program Files (x86)\Battle.net\Battle.net.exe", "--exec=launch WoWF"],
                     env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def close_wow_gently(steam_root, appid):
    """Asks WoW Forever's window to close, as its X does (taskkill without /F = WM_CLOSE), inside its own Proton prefix: the game
    exits cleanly and writes its settings and SavedVariables. Battle.net stays."""
    env = dict(session_env(), STEAM_COMPAT_DATA_PATH=str(steam_root / f"steamapps/compatdata/{appid}"),
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(wow_linux.steam_client_root(steam_root)))
    subprocess.run([str(PROTON), "run", "taskkill", "/IM", "Wow.exe"], env=env, timeout=30,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def wait_wow_gone(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not wow_running():
            return True
        await asyncio.sleep(1)
    return not wow_running()

async def end_session(ws, m):
    """The Thor's clean disconnect (its pause menu's power button, Exit game; Linux Edition 2026-11-20, as Desktop 0.2.39): WoW
    Forever closes on the PC. With quit_asked (the Thor tapped the game's own Exit Game) its own exit is waited for up to 30 s; then
    its window is asked to close (up to 20 s); only a WoW that stays is ended (its whole prefix, as the idle close). Then the add-ons
    that waited for a closed WoW go in."""
    await send(ws, {"t": "session_ending"})
    if not wow_running():
        await send(ws, {"t": "session_ended", "wow": "none", "put_back": False, "why": ""}); return
    log("End session from the Thor: closing WoW")
    gone = bool(m.get("quit_asked")) and await wait_wow_gone(30)
    if not gone and STEAM_PREFIX and PROTON:
        try:
            await asyncio.to_thread(close_wow_gently, *STEAM_PREFIX)
        except Exception as e:
            log("gentle close:", e)
        gone = await wait_wow_gone(20)
    if not gone and STEAM_PREFIX:
        log("WoW did not close: ending it")
        await asyncio.to_thread(close_prefix, *STEAM_PREFIX)
        gone = await wait_wow_gone(10)
    log("WoW closed" if gone else "WoW is still running")
    await send(ws, {"t": "session_ended", "wow": "closed" if gone else "left", "put_back": False,
                    "why": "" if gone else "WoW did not close"})
    if gone:
        spawn(pc_addons_pass())

def close_prefix(steam_root, appid):
    """Ends every process of WoW's Proton session (Battle.net, its agent, wineserver, Steam's reaper for it): by PID,
    matched on the prefix path in the process's environment or command line, never our own process tree."""
    tail = f"/steamapps/compatdata/{appid}"
    me = {os.getpid(), os.getppid()}
    pids = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) in me:
            continue
        try:
            env = Path(f"/proc/{d}/environ").read_bytes().split(b"\0")
            argv = Path(f"/proc/{d}/cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        envs = {k: v for k, _, v in (e.decode(errors="replace").partition("=") for e in env)}
        # only what Proton / Steam set for this game: never a process that merely mentions the path in its arguments
        ours = envs.get("STEAM_COMPAT_DATA_PATH", "").rstrip("/").endswith(tail) or \
               envs.get("WINEPREFIX", "").rstrip("/").endswith(tail + "/pfx") or \
               (argv and argv[0].endswith(b"/reaper") and f"AppId={appid}".encode() in argv)
        if ours:
            pids.append(int(d))
    found = len(pids)
    for sig in (15, 9):
        for pid in pids:
            try: os.kill(pid, sig)
            except OSError: pass
        if sig == 15:
            time.sleep(5)
            pids = [p for p in pids if Path(f"/proc/{p}").exists()]
    return found

def wow_running():
    return wow_linux.pid_of(wow_linux.WOW_PROC, "_forever_") is not None

def lan_addresses():
    """This PC's IPv4 addresses on its networks (the Thor follows the PC when DHCP moves it)."""
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=3).stdout
        return [m.group(1) for m in re.finditer(r"inet (\d+\.\d+\.\d+\.\d+)/", out)
                if not m.group(1).startswith(("100.", "172.17.", "10.88."))]   # skip Tailscale/CGNAT and container bridges
    except (OSError, subprocess.SubprocessError):
        return []

def wow_now():
    """Just the game's state (no LAN addresses etc.): what the 2 s loop needs."""
    w = wow.snapshot(wow_start["state"], wow_start["why"])
    w["found"] = GAME_DIR.exists()
    return w

_info_cache = [0.0, None]
def info():
    """The bridge's state for welcome / /v1/info; computed at most every 2 s (it runs pgrep, ss and ip)."""
    if _info_cache[1] is not None and time.monotonic() - _info_cache[0] < 2:
        return _info_cache[1]
    _info_cache[1] = _info(); _info_cache[0] = time.monotonic()
    return _info_cache[1]

def _info():
    w = wow.snapshot(wow_start["state"], wow_start["why"])
    w["found"] = GAME_DIR.exists()
    return {"proto": PROTO, "bridge_port": PORT, "host_id": state["host_id"], "pc_name": PC_NAME, "ver": VERSION,
            "sunshine": {"http_port": SUNSHINE_HTTP, "https_port": SUNSHINE_HTTPS},
            "wow": w,
            "lan": lan_addresses(), "stream": "unknown", "pairing_open": True, **({"tls": True, "fp": FINGERPRINT} if FINGERPRINT else {})}

_tasks = set()
def spawn(coro):
    """create_task that keeps a reference (asyncio only holds weak ones) and logs failures."""
    t = asyncio.create_task(coro); _tasks.add(t)
    def done(t):
        _tasks.discard(t)
        if not t.cancelled() and t.exception() and not isinstance(t.exception(), websockets.ConnectionClosed):
            log("task failed:", t.exception())
    t.add_done_callback(done)
    return t

def token_sha(tok):
    return hashlib.sha256(tok.encode("utf-8", "replace")).hexdigest()

async def send(ws, msg):
    await ws.send(json.dumps(msg, separators=(",", ":")))

async def broadcast(msgs):
    async def one(ws):
        try:
            tr = getattr(ws, "transport", None)
            if tr and tr.get_write_buffer_size() > 16 * 1024 * 1024:
                raise asyncio.TimeoutError          # 16 MB unread: the Thor is not reading
            for m in msgs:
                await asyncio.wait_for(send(ws, m), 10)
        except asyncio.TimeoutError:                 # a Thor that stopped reading: drop it (it reconnects), don't wait again
            log("a Thor stopped reading: closing its connection")
            for d, s in list(sessions.items()):
                if s is ws:
                    del sessions[d]
            spawn(ws.close(1011, "not reading"))
        except Exception:
            pass
    await asyncio.gather(*(one(ws) for ws in list(sessions.values())))   # all at once: one slow Thor doesn't hold up the rest

def _sunshine(method, path, body=None, csrf=None):
    """Sunshine's local web API (127.0.0.1 only), basic auth from SUNSHINE_USER / SUNSHINE_PASS."""
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE   # its own self-signed cert, localhost only
    auth = "Basic " + base64.b64encode(f"{os.environ['SUNSHINE_USER']}:{os.environ['SUNSHINE_PASS']}".encode()).decode()
    headers = {"Authorization": auth, "Content-Type": "application/json"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(f"https://127.0.0.1:{SUNSHINE_WEB}{path}", method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
        return json.loads(r.read() or b"{}")

def sunshine_pin(pin, name):
    """Give the Moonlight PIN to Sunshine (2026.914+: needs the waiting request's pairing_id). True when taken."""
    try:
        waiting = _sunshine("GET", "/api/pin").get("pairings") or []
        if not waiting:
            return False
        try:
            csrf = _sunshine("GET", "/api/csrf-token").get("csrf_token")
        except Exception:
            csrf = None
        for p in reversed(waiting):           # newest request first
            r = _sunshine("POST", "/api/pin", {"pairing_id": p.get("id"), "pin": pin, "name": name}, csrf)
            if r.get("status") in (True, "true"):
                return True
    except Exception as e:
        log("Sunshine PIN API:", e)
    return False

def sunshine_paired_count():
    """How many Moonlight clients Sunshine has paired (its state file), None if unreadable."""
    try:
        d = json.loads(SUNSHINE_STATE.read_text())
        return len(d.get("root", d).get("named_devices") or [])
    except Exception:
        return None

async def hand_pin(ws, pin, name):
    # Sunshine accepts the PIN only while the Thor's pairing request is waiting: retry for 90 s.
    if not (os.environ.get("SUNSHINE_USER") and os.environ.get("SUNSHINE_PASS")):
        log(f"*** Enter Moonlight PIN {pin} in Sunshine's web UI (https://localhost:{SUNSHINE_WEB} → PIN); also: dsf-bridge code ***")
        await send(ws, {"t": "status", "text": f"Enter PIN {pin} in Sunshine on the PC"})
        before = sunshine_paired_count()
        for _ in range(90):                 # tell the Thor once Sunshine lists a new paired client
            await asyncio.sleep(2)
            if before is not None and (sunshine_paired_count() or 0) > before:
                try:
                    await send(ws, {"t": "pair_stream", "ok": True})
                except Exception:
                    pass
                log("Sunshine paired the Thor"); return
        try:
            await send(ws, {"t": "pair_stream", "ok": False, "error": "no PIN entered in Sunshine within 3 minutes"})
        except Exception:
            pass
        return
    for _ in range(45):
        await asyncio.sleep(2)
        if ws.state.name != "OPEN":
            return                                # the Thor went away
        if await asyncio.to_thread(sunshine_pin, pin, name):
            await send(ws, {"t": "pair_stream", "ok": True}); log("Sunshine took the PIN"); return
    await send(ws, {"t": "pair_stream", "ok": False, "error": "the stream pairing timed out"})

async def handle(ws):
    path = ws.request.path
    if path != "/v1/ws":
        await ws.close(1008, "not found"); return
    origin = ws.request.headers.get("Origin")
    if origin and not re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin):
        await ws.close(4403, "native clients only"); return      # no web pages (as Desktop)
    device = None
    nonce = None
    ra = ws.remote_address or ("?", 0)
    peer = PEERS.get(ra[1], ra[0])               # through the front door every client looks like 127.0.0.1
    async def idle_guard():                      # sockets that never pair or say hello don't stay open
        await asyncio.sleep(300)                 # long enough to read and type the code
        if not (device and sessions.get(device) is ws):
            await ws.close(4401, "unauthorized")
    guard = asyncio.create_task(idle_guard())
    try:
        async for raw in ws:
            try:
                m = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(m, dict):
                continue
            t = m.get("t")
            if t in ("pair_hello", "hello") and device and sessions.get(device) is ws:
                del sessions[device]                     # this socket re-identifies: forget its old session
            if t == "pair_hello":
                device = str(m.get("device_id", ""))[:64]
                if not pairing["code"]:
                    new_code()
                nonce = secrets.token_hex(16)            # per connection
                left = attempts_left(peer)
                await send(ws, {"t": "pair_challenge", "nonce": nonce, "attempts_left": left, "locked": left <= 0})
            elif t == "pair_proof" and device and nonce:
                if attempts_left(peer) <= 0:
                    await send(ws, {"t": "pair_error", "error": "locked", "attempts_left": 0}); continue
                want = hmac.new(pairing["code"].encode(), f"dsf-pair-v1|{nonce}|{device}".encode(),
                                hashlib.sha256).hexdigest()
                if not hmac.compare_digest(want.encode(), str(m.get("proof", "")).lower().encode("utf-8", "replace")):
                    rec = misses.setdefault(peer, [0, 0.0]); rec[0] += 1; rec[1] = time.time()
                    pairing["wrong"] += 1
                    if pairing["wrong"] >= TOTAL:
                        pairing["locked_at"] = time.time()
                        log(f"Pairing paused for {LOCK_S // 60} min after {TOTAL} wrong codes in total")
                    elif rec[0] == PER_IP:
                        log(f"{peer}: {PER_IP} wrong codes, that address waits {LOCK_S // 60} min")
                    left = attempts_left(peer)
                    await send(ws, {"t": "pair_error", "error": "locked" if left <= 0 else "wrong_code", "attempts_left": left})
                    continue
                token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
                state["devices"][device] = {"token_sha": token_sha(token), "paired": int(time.time())}
                save_state(state)
                nonce = None
                new_code()                               # the used code is gone; a fresh one is ready for the next Thor
                pin = f"{secrets.randbelow(10000):04d}"
                pairing["pin"] = pin
                pin_file = STATE.parent / "moonlight-pin.txt"
                write_private(pin_file, pin + "\n")
                log(f"Paired device {device[:8]}…")
                await send(ws, {"t": "pair_ok", "device_id": device, "token": token, "host_id": state["host_id"],
                                "pc_name": PC_NAME, "sunshine": {"http_port": SUNSHINE_HTTP, "https_port": SUNSHINE_HTTPS}, "moonlight_pin": pin,
                                **({"fp": FINGERPRINT} if FINGERPRINT else {})})
                spawn(hand_pin(ws, pin, "AYN Thor"))
                await start_session(ws, device)
                spawn(thor_addons(ws, m))
            elif t == "hello":
                device = str(m.get("device_id", ""))[:64]
                d = state["devices"].get(device)
                if not d or not hmac.compare_digest(d["token_sha"], token_sha(str(m.get("token", "")))):
                    await send(ws, {"t": "error", "error": "unauthorized", "detail": "pair again"})
                    await ws.close(4401, "unauthorized"); return
                await start_session(ws, device)
                spawn(thor_addons(ws, m))
            elif not (device and sessions.get(device) is ws):
                await send(ws, {"t": "error", "error": "unauthorized", "detail": "hello first"})
                await ws.close(4401, "unauthorized"); return
            elif t == "focus":
                ok = wow_running()
                if ok:
                    raised = await asyncio.to_thread(wow_linux.focus_window)   # KDE only; elsewhere a no-op
                    await send(ws, {"t": "focus_result", "ok": True, "why": "" if raised else "can't raise windows on this desktop",
                                    **(await asyncio.to_thread(_info))["wow"]})
                else:
                    await send(ws, {"t": "focus_result", "ok": False, "state": "starting", "why": "starting WoW"})
                    spawn(start_wow())
            elif t == "bnet_ready":                  # Desktop types the Thor's saved login into Battle.net; this helper never does
                await send(ws, {"t": "bnet_ready_result", "ok": False, "why": "sign in to Battle.net on the PC (this helper never types your login)"})
            elif t == "login_file":                  # the Thor's saved login: deliberately ignored, never stored
                pass
            elif t == "ping":
                await send(ws, {"t": "pong", "id": m.get("id")})
            elif t == "unpair":
                state["devices"].pop(device, None); save_state(state)
                await send(ws, {"t": "unpaired"}); await ws.close(); return
            elif t == "end_session":
                spawn(end_session(ws, m))
            elif t == "addons_want":
                pc_want["m"] = m
                wanted = [x.get("title") or x.get("id") for x in m.get("managed") or [] if isinstance(x, dict) and x.get("want")]
                log("pc add-ons: the Thor wants " + (", ".join(map(str, wanted)) or "none of the managed ones"))
                spawn(pc_addons_pass(ws))
            elif t == "addons_status":
                await send(ws, {"t": "addons", "result": f"PC set {addons.installed_set(ADDONS_DIR) or 'none'}"})
            elif t == "addons_install":
                await send(ws, {"t": "addons", "result": await addon_pass(force=True, allow_new=True)})
    except websockets.ConnectionClosed:
        pass
    finally:
        guard.cancel()
        if device and sessions.get(device) is ws:
            del sessions[device]
            log(f"Device {device[:8]}… disconnected")

async def thor_addons(ws, m):
    """A connected Thor uses DS Forever: make sure the PC game has its add-ons (new install allowed)."""
    try:
        thor_set = int(m.get("addon_set") or 0)
    except (TypeError, ValueError):
        thor_set = 0
    msg = await addon_pass(allow_new=True, thor_set=thor_set)
    if "up to date" not in msg:
        try:
            await send(ws, {"t": "status", "text": msg})
        except Exception:
            pass

async def start_session(ws, device):
    old = sessions.get(device)
    if old and old is not ws:
        await old.close(4409, "replaced")
    welcome = await asyncio.to_thread(_info)         # fresh, not the 2 s cache
    async with feed_lock:
        sessions[device] = ws
        log(f"Session for {device[:8]}…, backlog {len(backlog)}")
        await send(ws, {"t": "welcome", **welcome, "device_id": device, "backlog": len(backlog)})
        for msg in list(backlog):
            await send(ws, msg)
        await send(ws, {"t": "backlog_end", "count": len(backlog)})


# ---------------------------------------------------------------- loops
async def tail_loop():
    tail = Tailer(LOG)
    size = 0
    while True:
        try:
            msgs = await asyncio.to_thread(tail.poll)
        except Exception as e:                  # MemoryError, odd file errors: log and keep following
            log("log follower:", e); msgs = []; await asyncio.sleep(2)
        if msgs:
          async with feed_lock:                 # backlog and live feed change together: no doubles for a joining Thor
            for m in msgs:
                if m["t"] == "log":
                    backlog.clear(); size = 0
                elif m["t"] == "doc":
                    wow.doc_seen()
                    backlog.append(m); size += len(m["doc"])
                    while backlog and (size > MAX_BACKLOG_BYTES or len(backlog) > MAX_BACKLOG_DOCS):
                        size -= len(backlog.pop(0).get("doc", ""))
            await broadcast(msgs)
        await asyncio.sleep(0.05 if msgs else 0.2)   # quick while docs flow, light when idle

# a WoW the Thor used is closed after this long with no Thor connected (swiping the app away leaves it running); 0 = never
IDLE_CLOSE_S = int(float(os.environ.get("DSF_IDLE_CLOSE_MIN", "10")) * 60)

async def wow_loop():
    last = None
    thor_seen, alone_since = False, None             # idle close: a Thor used this WoW run; since when none is connected
    texts = {"none": "WoW isn't running on your PC", "starting": "Starting WoW on your PC…", "login": "WoW is at its login screen",
             "signing_in": "Signing in…", "charselect": "At character select", "world": "WoW is running on your PC"}
    while True:
        try:
            w = await asyncio.to_thread(wow_now)
        except Exception as e:
            log("WoW check:", e); await asyncio.sleep(5); continue
        now = time.monotonic()
        if not w["running"]:
            thor_seen, alone_since = False, None
        elif sessions:
            thor_seen, alone_since = True, None
        elif thor_seen and alone_since is None:
            alone_since = now
        if wow_linux.idle_close_due(w["running"], thor_seen, alone_since, now, IDLE_CLOSE_S) and STEAM_PREFIX:
            log(f"No Thor for {IDLE_CLOSE_S // 60} min: closing WoW and Battle.net")
            n = await asyncio.to_thread(close_prefix, *STEAM_PREFIX)
            log(f"closed {n} process(es)")
            thor_seen, alone_since = False, None
            await asyncio.sleep(2); continue
        key = (w["state"], w["screen"], w["bnet"], w["login_error"])
        if last is not None and last[0] == "running" and not w["running"]:
            spawn(pc_addons_pass())                   # WoW closed: what waited goes in now
        if key != last:
            if sessions and w["running"] and (last is None or last[0] != "running"):
                await asyncio.to_thread(wow_linux.focus_window)      # its window just appeared: bring it to the stream
            last = key
            log(f"WoW: {w['state']} / {w['screen']}" + (f" ({w['login_error']})" if w["login_error"] else ""))
            await broadcast([{"t": "wow", **w}, {"t": "status", "text": texts.get(w["screen"], "")}])
        await asyncio.sleep(2)

# ---------------------------------------------------------------- TLS (wss) on the same port, as Desktop [S3]
TLS_ON = os.environ.get("DSF_TLS", "1") != "0"
CERT, KEY = STATE.parent / "bridge-cert.pem", STATE.parent / "bridge-key.pem"
FINGERPRINT = None

def ensure_cert():
    """A self-signed RSA-2048 certificate made once and kept; returns its SHA-256 (DER, lower-case hex) or None."""
    if not TLS_ON or not shutil.which("openssl"):
        return None
    if not (CERT.exists() and KEY.exists()):
        r = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
                            "-subj", "/CN=dsf-bridge", "-keyout", str(KEY), "-out", str(CERT)], capture_output=True)
        if r.returncode != 0:
            log("TLS off: openssl could not make a certificate"); return None
        os.chmod(KEY, 0o600)
    der = ssl.PEM_cert_to_DER_cert(CERT.read_text())
    return hashlib.sha256(der).hexdigest()

async def front_door(plain_port, tls_port):
    """Port PORT: a connection whose first byte is a TLS ClientHello (0x16) goes to the wss server, anything else to ws."""
    async def pipe(r, w):
        try:
            while data := await r.read(65536):
                w.write(data); await w.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            try:
                w.close()
            except Exception:
                pass
    async def conn(reader, writer):
        try:
            first = await asyncio.wait_for(reader.read(1), 30)
        except (asyncio.TimeoutError, ConnectionError):
            writer.close(); return
        if not first:
            writer.close(); return
        target = tls_port if first == b"\x16" else plain_port
        try:
            ur, uw = await asyncio.open_connection("127.0.0.1", target)
        except OSError:
            writer.close(); return
        port = (uw.get_extra_info("sockname") or ("", 0))[1]
        PEERS[port] = (writer.get_extra_info("peername") or ("?",))[0]
        uw.write(first)
        try:
            await asyncio.gather(pipe(reader, uw), pipe(ur, writer))
        finally:
            PEERS.pop(port, None)
    return await asyncio.start_server(conn, "0.0.0.0", PORT)

def advertise():
    txt = [f"proto={PROTO}", f"id={state['host_id']}", f"pc={PC_NAME}", f"sunshine={SUNSHINE_HTTP}", f"ver={VERSION}"]
    sid = sunshine_uniqueid()
    if sid:
        txt.append(f"sid={sid}")
    if FINGERPRINT:
        txt += ["tls=1", f"fp={FINGERPRINT}"]
    try:
        return subprocess.Popen(["avahi-publish", "-s", PC_NAME, "_dsforever._tcp", str(PORT), *txt],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        log("mDNS off (avahi-publish missing?):", e); return None

async def http_info(conn, request):
    if request.path == "/v1/info":
        return conn.respond(200, json.dumps(await asyncio.to_thread(info)) + "\n")
    return None

async def main():
    new_code()   # always ready, so `dsf-bridge code` works before the Thor asks
    if state["devices"]:
        log(f"{len(state['devices'])} paired device(s)")
    if addons.installed_set(ADDONS_DIR):
        log(await addon_pass())          # update an existing install at start (never a fresh one)
    global FINGERPRINT
    FINGERPRINT = ensure_cert()
    mdns = None if os.environ.get("DSF_NO_MDNS") else advertise()
    log(f"Bridge on {'ws+wss' if FINGERPRINT else 'ws'}://0.0.0.0:{PORT}/v1/ws, following {LOG}")
    log("WoW start: " + ("DSF_START_CMD" if START_CMD else f"Steam app {STEAM_PREFIX[1]} via {PROTON}" if STEAM_PREFIX and PROTON
                         else "not possible (set DSF_START_CMD)"))
    async def mdns_watch():
        nonlocal mdns
        while mdns:
            await asyncio.sleep(10)
            if mdns.poll() is not None:
                log("mDNS advert stopped (avahi restarted?): publishing again")
                mdns = advertise()
    try:
        kw = dict(process_request=http_info, ping_interval=15, ping_timeout=45)
        async with serve(handle, "127.0.0.1", 0, **kw) as plain:
            plain_port = plain.sockets[0].getsockname()[1]
            tls_port = plain_port
            tls_srv = None
            if FINGERPRINT:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CERT, KEY)
                tls_srv = await serve(handle, "127.0.0.1", 0, ssl=ctx, **kw)
                tls_port = tls_srv.sockets[0].getsockname()[1]
            door = await front_door(plain_port, tls_port)
            async with door:
                await asyncio.gather(tail_loop(), wow_loop(), mdns_watch())
    finally:
        if mdns:
            mdns.terminate()

# ---------------------------------------------------------------- command line
def doctor():
    """Check everything the Thor needs, in plain words. Returns the number of problems."""
    probs = 0
    def line(ok, text, fix=""):
        nonlocal probs
        print(("  OK   " if ok else "  FIX  ") + text + ("" if ok or not fix else f"\n         → {fix}"))
        probs += 0 if ok else 1
    print("DS Forever Linux helper: checks")
    line(GAME_DIR.exists(), f"WoW Forever found: {GAME_DIR}" if GAME_DIR.exists() else "WoW Forever not found",
         "install WoW Forever with Battle.net (Steam: add Battle.net as a non-Steam game, Proton), start it once, "
         "or set DSF_WOW_DIR in ~/.config/dsf-bridge/env")
    line(LOG.exists(), "WoW's log exists (start WoW once if this fails)", "start WoW Forever once and log in")
    can_start = bool(START_CMD or (STEAM_PREFIX and PROTON))
    line(can_start, "WoW can be started for you: " + ("DSF_START_CMD" if START_CMD else f"Steam app {STEAM_PREFIX[1]}, {PROTON.parent.name}" if can_start else "no"),
         "WoW is not in a Steam/Proton prefix: set DSF_START_CMD in ~/.config/dsf-bridge/env to a command that starts it")
    bnet = GAME_DIR.parent.parent / "Battle.net/Battle.net.exe"
    line(START_CMD or bnet.exists(), "Battle.net installed in the same prefix", "install Battle.net in WoW's prefix")
    sun_up = subprocess.run(["pgrep", "-i", "sunshine"], capture_output=True).returncode == 0
    line((SUNSHINE_DIR / "sunshine.conf").exists() and sun_up, f"Sunshine installed and running ({SUNSHINE_DIR})",
         "install Sunshine (Flatpak dev.lizardbyte.app.Sunshine or your distro's package) and start it")
    auto_pin = bool(os.environ.get("SUNSHINE_USER") and os.environ.get("SUNSHINE_PASS"))
    print(("  OK   " if auto_pin else "  NOTE ") + ("Moonlight PIN goes to Sunshine automatically" if auto_pin else
          f"Moonlight PIN: you type it in Sunshine's web UI once (https://localhost:{SUNSHINE_WEB} → PIN).\n"
          "         Optional: SUNSHINE_USER=… / SUNSHINE_PASS=… in ~/.config/dsf-bridge/env makes it automatic"))
    avahi = subprocess.run(["systemctl", "is-active", "avahi-daemon"], capture_output=True, text=True).stdout.strip() == "active"
    line(avahi and shutil.which("avahi-publish"), "avahi (mDNS) running, so the Thor finds this PC",
         "install avahi (avahi-tools / avahi-utils) and: sudo systemctl enable --now avahi-daemon")
    fw = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True) if shutil.which("firewall-cmd") else None
    if fw and fw.returncode == 0:
        q = subprocess.run(["firewall-cmd", "--query-port", f"{PORT}/tcp"], capture_output=True, text=True)
        rng = subprocess.run(["firewall-cmd", "--list-ports"], capture_output=True, text=True).stdout
        ok = q.stdout.strip() == "yes" or any(_in_range(PORT, r) for r in rng.split() if r.endswith("/tcp"))
        line(ok, f"firewall lets the Thor reach port {PORT}",
             f"sudo firewall-cmd --permanent --add-port={PORT}/tcp --add-service=mdns && sudo firewall-cmd --reload")
    elif shutil.which("ufw"):
        print(f"  NOTE ufw: if it is on, allow the Thor in: sudo ufw allow {PORT}/tcp && sudo ufw allow mdns")
    svc = subprocess.run(["systemctl", "--user", "is-active", "dsf-bridge"], capture_output=True, text=True).stdout.strip()
    line(svc == "active", "helper service running (dsf-bridge)", "run ./install.sh, or: systemctl --user enable --now dsf-bridge")
    have = addons.installed_set(ADDONS_DIR)
    print(f"  {'OK  ' if have else 'NOTE'} DS Forever add-ons in the game: " + (f"set {have}" if have else
          "not yet (installed when the Thor first connects, or run: dsf-bridge addons)"))
    print(f"  INFO paired Thors: {len(state['devices'])}")
    print("All good." if not probs else f"{probs} thing(s) to fix.")
    return probs

def _in_range(port, spec):
    a = spec.split("/")[0]
    lo, _, hi = a.partition("-")
    return lo.isdigit() and int(lo) <= port <= int(hi or lo)

def cli():
    ap = argparse.ArgumentParser(prog="dsf-bridge", description="DS Forever helper for Linux (AYN Thor streaming).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("run", help="run the helper (what the service does)")
    sub.add_parser("doctor", help="check the setup")
    sub.add_parser("code", help="show the pairing code to type on the Thor")
    sub.add_parser("forget", help="forget all paired Thors")
    a = sub.add_parser("addons", help="install/update DS Forever's add-ons in the game")
    a.add_argument("--force", action="store_true", help="replace a differing set")
    args = ap.parse_args()
    if args.cmd in (None, "run"):
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass
    elif args.cmd == "doctor":
        sys.exit(1 if doctor() else 0)
    elif args.cmd == "code":
        f = STATE.parent / "pairing-code.txt"
        if f.exists() and subprocess.run(["systemctl", "--user", "is-active", "dsf-bridge"], capture_output=True).returncode == 0:
            c = f.read_text().strip(); print(f"Pairing code: {c[:3]} {c[3:]}")
            net = paircode.encode_tail(lan_addresses(), PORT)
            if net: print(f"Other network (Thor on WireGuard / another subnet): {paircode.groups(net)}")
            pf = STATE.parent / "moonlight-pin.txt"
            if pf.exists() and time.time() - pf.stat().st_mtime < 600:
                print(f"Moonlight PIN for Sunshine (last pairing): {pf.read_text().strip()}  → https://localhost:{SUNSHINE_WEB} → PIN")
        else:
            print("The helper isn't running: systemctl --user start dsf-bridge"); sys.exit(1)
    elif args.cmd == "forget":
        state["devices"] = {}; save_state(state)
        print("Forgotten. Restart the helper: systemctl --user restart dsf-bridge")
    elif args.cmd == "addons":
        print(asyncio.run(addon_pass(force=args.force, allow_new=True)))

if __name__ == "__main__":
    cli()
