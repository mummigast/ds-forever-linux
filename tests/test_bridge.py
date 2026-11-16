# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end tests: a real bridge process, a fake General.log and a fake Thor.
Run: .venv/bin/python -m unittest discover -s tests"""
import asyncio, hashlib, hmac, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path

import ssl, urllib.request
import websockets

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import wow_linux  # noqa: E402

PORT = 48298


def proof(code, nonce, dev):
    return hmac.new(code.encode(), f"dsf-pair-v1|{nonce}|{dev}".encode(), hashlib.sha256).hexdigest()


class Units(unittest.TestCase):
    def test_proof_vector(self):   # from STREAM_BRIDGE_PROTOCOL.md section 10
        self.assertEqual(proof("123456", "00ff", "thor-1"),
                         "1728773c570e30c5f0032df3751d125403088e2848828f1b49d2a68c808f50f9")

    def test_classify(self):
        L = wow_linux.LoginLog()
        c = wow_linux.classify
        self.assertEqual(c(False, 0, 0, 0, L, None), "none")
        self.assertEqual(c(True, 5, 0, 0, L, None), "starting")
        L.line('[N][Lua] Switching to screen="AccountLogin" (from "none")')
        self.assertEqual(c(True, 60, 0, 0, L, None), "login")
        L.line("[N][Connection] Glue login started")
        self.assertEqual(c(True, 60, 0, 0, L, None), "signing_in")
        L.line('[N][Connection] Fatal login error received result=" (308)"')
        self.assertEqual((c(True, 60, 0, 0, L, None), L.error), ("login", "308"))
        L.line('[N][Lua] Switching to screen="CharacterSelect"')
        self.assertEqual(c(True, 60, 0, 0, L, None), "charselect")
        self.assertEqual(c(True, 60, 2, 0, L, None), "world")
        self.assertEqual(c(True, 60, 0, 0, L, 10.0), "world")

    def test_short_error(self):
        self.assertEqual(wow_linux.short_error("Status has no name. (14400)"), "Status has no name (14400)")


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        (t / "wow/Logs").mkdir(parents=True)
        self.log = t / "wow/Logs/General.log"
        self.log.write_text("")
        env = dict(os.environ, DSF_PORT=str(PORT), DSF_WOW_DIR=str(t / "wow"), DSF_STATE=str(t / "state.json"),
                   DSF_START_CMD="true", DSF_NO_MDNS="1")
        self.proc = subprocess.Popen([sys.executable, str(HERE / "dsf_bridge.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.code_file = t / "pairing-code.txt"
        import socket
        for _ in range(100):                     # until the code exists and the port accepts (cert generation takes a moment)
            try:
                if self.code_file.exists():
                    socket.create_connection(("127.0.0.1", PORT), 0.2).close()
                    break
            except OSError:
                pass
            time.sleep(0.1)

    def tearDown(self):
        self.proc.terminate(); self.proc.wait(5)
        self.tmp.cleanup()

    def append(self, *lines):
        with open(self.log, "a") as f:
            for ln in lines:
                f.write(ln + "\r\n")

    async def recv(self, ws, t=None):
        while True:
            m = json.loads(await asyncio.wait_for(ws.recv(), 5))
            if t is None or m["t"] == t:
                return m

    def test_flow(self):
        asyncio.run(self.flow())

    async def flow(self):
        url = f"ws://127.0.0.1:{PORT}/v1/ws"
        code = self.code_file.read_text().strip()
        # commands before pairing are refused
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"t": "focus"}))
            self.assertEqual((await self.recv(ws))["error"], "unauthorized")
        # wrong code, then the right one
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"t": "pair_hello", "proto": 1, "device_id": "thor-1", "stream": True}))
            ch = await self.recv(ws, "pair_challenge")
            await ws.send(json.dumps({"t": "pair_proof", "proof": proof("000000", ch["nonce"], "thor-1")}))
            err = await self.recv(ws, "pair_error")
            self.assertEqual((err["error"], err["attempts_left"]), ("wrong_code", 4))
            await ws.send(json.dumps({"t": "pair_proof", "proof": proof(code, ch["nonce"], "thor-1")}))
            ok = await self.recv(ws, "pair_ok")
            self.assertRegex(ok["moonlight_pin"], r"^\d{4}$")
            w = await self.recv(ws, "welcome")
            self.assertEqual(w["wow"]["screen"], "none")
            await self.recv(ws, "backlog_end")
            self.append('11/16 15:00:01.250  [N][Lua] WCB1|1|1/1|{"type":"hello"}',
                        "11/16 15:00:01.300  WCB1|pad|xxxx",
                        '11/16 15:00:01.310  WCB1|2|1/2|{"type":"big",',
                        '11/16 15:00:01.320  WCB1|3|2/2|"n":1}',
                        '11/16 15:00:01.330  WCB1|5|1/1|{"type":"after-gap"}')
            d1 = await self.recv(ws, "doc")
            self.assertEqual((d1["seq"], d1["doc"]), (1, '{"type":"hello"}'))
            d2 = await self.recv(ws, "doc")
            self.assertEqual(d2["doc"], '{"type":"big","n":1}')
            g = await self.recv(ws, "gap")
            self.assertEqual((g["seq"], g["expected"]), (5, 4))
        # reconnect with the token: backlog replayed
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"t": "hello", "proto": 1, "device_id": "thor-1", "token": ok["token"]}))
            w = await self.recv(ws, "welcome")
            self.assertEqual(w["backlog"], 3)
            # WoW truncates its log at launch: a restart is announced and the backlog dropped
            self.log.write_text("")
            self.append("11/16 16:00:00.000  restarted")
            self.assertEqual((await self.recv(ws, "log"))["event"], "restart")
        # wss on the same port, certificate pinned by the fingerprint from pair_ok (as the Thor does)
        self.assertRegex(ok.get("fp", ""), r"^[0-9a-f]{64}$")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        async with websockets.connect(f"wss://127.0.0.1:{PORT}/v1/ws", ssl=ctx) as ws:
            der = ws.transport.get_extra_info("ssl_object").getpeercert(binary_form=True)
            self.assertEqual(hashlib.sha256(der).hexdigest(), ok["fp"])
            await ws.send(json.dumps({"t": "hello", "proto": 1, "device_id": "thor-1", "token": ok["token"]}))
            self.assertEqual((await self.recv(ws, "welcome"))["fp"], ok["fp"])
        # plain HTTP /v1/info through the same port
        info = json.loads(await asyncio.to_thread(lambda: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/info", timeout=5).read()))
        self.assertEqual(info["proto"], 1)
        # bad token
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"t": "hello", "proto": 1, "device_id": "thor-1", "token": "bad"}))
            self.assertEqual((await self.recv(ws))["error"], "unauthorized")


if __name__ == "__main__":
    unittest.main()
