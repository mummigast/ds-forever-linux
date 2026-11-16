#!/usr/bin/env python3
"""DS Forever bridge for Linux: lets the DS Forever app on an AYN Thor use a Linux PC that already
streams WoW Forever with Sunshine. Replaces the bridge part of DS Forever Desktop (Windows only).

Speaks desktop/docs/STREAM_BRIDGE_PROTOCOL.md v1:
  - follows WoW's General.log, reassembles the add-on's WCB1 documents (port of WcbAssembler.cs)
  - WebSocket server ws://<pc>:48210/v1/ws (plain ws; the Thor uses ws when tls is not advertised)
  - pairing: 6-digit code shown here, HMAC proof from the Thor, token stored in the state file
  - mDNS advert _dsforever._tcp via avahi-publish
  - Moonlight PIN to Sunshine: automatic via Sunshine's API when SUNSHINE_USER/SUNSHINE_PASS are set,
    otherwise printed for you to type into Sunshine's web UI (https://localhost:47990 → PIN)

Never touches credentials, bindings, macros or CVars. Video/audio/controller stay Moonlight <-> Sunshine.
"""
import asyncio, base64, hashlib, hmac, json, os, secrets, socket, ssl, subprocess, sys, time, urllib.request
from pathlib import Path

import websockets
from websockets.asyncio.server import serve

PROTO = 1
VERSION = "linux-0.1"
PORT = int(os.environ.get("DSF_PORT", "48210"))
GAME_DIR = Path(os.environ.get("DSF_WOW_DIR", Path.home() /
    ".local/share/Steam/steamapps/compatdata/3809046808/pfx/drive_c/Program Files (x86)/World of Warcraft/_forever_"))
LOG = GAME_DIR / "Logs" / "General.log"
STATE = Path(os.environ.get("DSF_STATE", Path.home() / ".config/dsf-bridge/state.json"))
SUNSHINE_HTTP, SUNSHINE_HTTPS, SUNSHINE_WEB = 47989, 47984, 47990
SUNSHINE_STATE = Path.home() / ".var/app/dev.lizardbyte.app.Sunshine/config/sunshine/sunshine_state.json"
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

def save_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    os.chmod(tmp, 0o600)
    tmp.replace(STATE)

state = load_state()
state.setdefault("host_id", secrets.token_hex(16))
state.setdefault("devices", {})          # device_id -> {"token_sha": ..., "name": ...}
save_state(state)

def sunshine_uniqueid():
    try:
        return json.loads(SUNSHINE_STATE.read_text()).get("uniqueid")
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
        if len(parts) < 3 or not parts[0].isdigit():
            return
        seq, spec, payload = int(parts[0]), parts[1], parts[2]
        if self.last >= 0 and seq != self.last + 1:
            out.append({"t": "gap", "seq": seq, "expected": self.last + 1})
        self.last = seq
        a, _, b = spec.partition("/")
        if not (a.isdigit() and b.isdigit()):
            return
        idx, total = int(a), int(b)
        if total < 1 or idx < 1 or idx > total:
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
            self.asm.line(ln.decode("utf-8", "replace"), out)
        return out


# ---------------------------------------------------------------- sessions
sessions = {}          # device_id -> websocket
backlog = []           # messages since the current log began
pairing = {"code": None, "attempts": 5}

def new_code():
    pairing["code"] = f"{secrets.randbelow(1_000_000):06d}"
    pairing["attempts"] = 5
    log(f"*** Pairing code for the Thor: {pairing['code'][:3]} {pairing['code'][3:]} ***")

def wow_running():
    return subprocess.run(["pgrep", "-if", r"wow\.exe"], capture_output=True).returncode == 0

def info():
    running = wow_running()
    return {"proto": PROTO, "bridge_port": PORT, "host_id": state["host_id"], "pc_name": PC_NAME, "ver": VERSION,
            "sunshine": {"http_port": SUNSHINE_HTTP, "https_port": SUNSHINE_HTTPS},
            "wow": {"found": GAME_DIR.exists(), "flavor": "forever", "running": running,
                    "state": "running" if running else "stopped", "focused": running,
                    "screen": "world" if running else "none", "bnet": "unknown", "needs_you": False},
            "stream": "unknown", "pairing_open": True}

def token_sha(tok):
    return hashlib.sha256(tok.encode()).hexdigest()

async def send(ws, msg):
    await ws.send(json.dumps(msg, separators=(",", ":")))

async def broadcast(msgs):
    for ws in list(sessions.values()):
        try:
            for m in msgs:
                await send(ws, m)
        except Exception:
            pass

def sunshine_pin(pin, name):
    """Give the Moonlight PIN to Sunshine. True if sent automatically."""
    user, pw = os.environ.get("SUNSHINE_USER"), os.environ.get("SUNSHINE_PASS")
    if not (user and pw):
        return False
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(f"https://localhost:{SUNSHINE_WEB}/api/pin", method="POST",
                                 data=json.dumps({"pin": pin, "name": name}).encode(),
                                 headers={"Authorization": auth, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            return json.loads(r.read() or b"{}").get("status") in (True, "true")
    except Exception as e:
        log("Sunshine PIN API:", e)
        return False

async def hand_pin(ws, pin, name):
    # Sunshine accepts the PIN only while the Thor's pairing request is waiting: retry for 90 s.
    if not (os.environ.get("SUNSHINE_USER") and os.environ.get("SUNSHINE_PASS")):
        log(f"*** Enter Moonlight PIN {pin} in Sunshine's web UI (https://localhost:{SUNSHINE_WEB} → PIN) ***")
        await send(ws, {"t": "status", "text": f"Enter PIN {pin} in Sunshine on the PC"})
        return
    for _ in range(45):
        await asyncio.sleep(2)
        if await asyncio.to_thread(sunshine_pin, pin, name):
            await send(ws, {"t": "pair_stream", "ok": True}); log("Sunshine took the PIN"); return
    await send(ws, {"t": "pair_stream", "ok": False, "error": "the stream pairing timed out"})

async def handle(ws):
    path = ws.request.path
    if path != "/v1/ws":
        await ws.close(1008, "not found"); return
    device = None
    try:
        async for raw in ws:
            try:
                m = json.loads(raw)
            except ValueError:
                continue
            t = m.get("t")
            if t == "pair_hello":
                device = m.get("device_id", "")
                if not pairing["code"]:
                    new_code()
                pairing["nonce"] = secrets.token_hex(16)
                await send(ws, {"t": "pair_challenge", "nonce": pairing["nonce"],
                                "attempts_left": pairing["attempts"], "locked": pairing["attempts"] <= 0})
            elif t == "pair_proof" and device:
                if pairing["attempts"] <= 0:
                    await send(ws, {"t": "pair_error", "error": "locked", "attempts_left": 0}); continue
                want = hmac.new(pairing["code"].encode(), f"dsf-pair-v1|{pairing['nonce']}|{device}".encode(),
                                hashlib.sha256).hexdigest()
                if not hmac.compare_digest(want, str(m.get("proof", "")).lower()):
                    pairing["attempts"] -= 1
                    await send(ws, {"t": "pair_error", "error": "wrong_code", "attempts_left": pairing["attempts"]})
                    continue
                token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
                state["devices"][device] = {"token_sha": token_sha(token), "paired": int(time.time())}
                save_state(state)
                pairing["code"] = None
                pin = f"{secrets.randbelow(10000):04d}"
                log(f"Paired device {device[:8]}…")
                await send(ws, {"t": "pair_ok", "device_id": device, "token": token, "host_id": state["host_id"],
                                "pc_name": PC_NAME, "sunshine": info()["sunshine"], "moonlight_pin": pin})
                asyncio.create_task(hand_pin(ws, pin, "AYN Thor"))
                await start_session(ws, device)
            elif t == "hello":
                device = m.get("device_id", "")
                d = state["devices"].get(device)
                if not d or not hmac.compare_digest(d["token_sha"], token_sha(str(m.get("token", "")))):
                    await send(ws, {"t": "error", "error": "unauthorized", "detail": "pair again"})
                    await ws.close(4401, "unauthorized"); return
                await start_session(ws, device)
            elif t == "focus":
                ok = wow_running()   # Linux/Wayland: no window raising; Sunshine streams the desktop as is
                await send(ws, {"t": "focus_result", "ok": ok, "why": "" if ok else "WoW is not running on the PC"})
            elif t == "ping":
                await send(ws, {"t": "pong", "id": m.get("id")})
            elif t == "unpair" and device:
                state["devices"].pop(device, None); save_state(state)
                await send(ws, {"t": "unpaired"}); await ws.close(); return
            elif t in ("addons_status", "addons_install"):
                await send(ws, {"t": "addons", "ok": False, "why": "install add-ons by hand on Linux (see README)"})
    except websockets.ConnectionClosed:
        pass
    finally:
        if device and sessions.get(device) is ws:
            del sessions[device]
            log(f"Device {device[:8]}… disconnected")

async def start_session(ws, device):
    old = sessions.get(device)
    if old and old is not ws:
        await old.close(4409, "replaced")
    sessions[device] = ws
    log(f"Session for {device[:8]}…, backlog {len(backlog)}")
    await send(ws, {"t": "welcome", **info(), "device_id": device, "backlog": len(backlog)})
    for msg in list(backlog):
        await send(ws, msg)
    await send(ws, {"t": "backlog_end", "count": len(backlog)})


# ---------------------------------------------------------------- loops
async def tail_loop():
    tail = Tailer(LOG)
    size = 0
    while True:
        msgs = tail.poll()
        if msgs:
            for m in msgs:
                if m["t"] == "log":
                    backlog.clear(); size = 0
                elif m["t"] == "doc":
                    backlog.append(m); size += len(m["doc"])
                    while backlog and (size > MAX_BACKLOG_BYTES or len(backlog) > MAX_BACKLOG_DOCS):
                        size -= len(backlog.pop(0).get("doc", ""))
            await broadcast(msgs)
        await asyncio.sleep(0.05)

async def wow_loop():
    last = None
    while True:
        r = wow_running()
        if r != last:
            last = r
            w = info()["wow"]
            await broadcast([{"t": "wow", **w}, {"t": "status", "text": "WoW is running on your PC" if r else "WoW isn't running on your PC"}])
        await asyncio.sleep(3)

def advertise():
    txt = [f"proto={PROTO}", f"id={state['host_id']}", f"pc={PC_NAME}", f"sunshine={SUNSHINE_HTTP}", f"ver={VERSION}"]
    sid = sunshine_uniqueid()
    if sid:
        txt.append(f"sid={sid}")
    return subprocess.Popen(["avahi-publish", "-s", PC_NAME, "_dsforever._tcp", str(PORT), *txt],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def http_info(conn, request):
    if request.path == "/v1/info":
        return conn.respond(200, json.dumps(info()) + "\n")
    return None

async def main():
    if not state["devices"]:
        new_code()
    else:
        log(f"{len(state['devices'])} paired device(s). New Thor? Start pairing on it and a code shows here.")
    mdns = advertise()
    log(f"Bridge on ws://0.0.0.0:{PORT}/v1/ws, following {LOG}")
    try:
        async with serve(handle, "0.0.0.0", PORT, process_request=http_info, ping_interval=15, ping_timeout=45):
            await asyncio.gather(tail_loop(), wow_loop())
    finally:
        mdns.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
