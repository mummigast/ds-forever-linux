# DS Forever bridge for Linux

Use the DS Forever app on an AYN Thor with a **Linux** PC that streams WoW Forever through Sunshine.
It replaces the bridge part of DS Forever Desktop (Windows only). Protocol: `../desktop/docs/STREAM_BRIDGE_PROTOCOL.md`.

What it does: follows WoW's `General.log`, reassembles the DS add-ons' documents and serves them to the Thor over
`ws://<pc>:48210/v1/ws`, advertised by mDNS (`_dsforever._tcp`, via avahi). Video, audio and the controller stay
Moonlight ↔ your own Sunshine. It never reads, stores or types credentials: sign in on the PC as usual.

## Setup
1. `uv venv .venv && uv pip install -p .venv websockets`
2. `./install-addons.sh` (copies the WowCompanion add-ons into the game; `/reload` in game)
3. Run `./.venv/bin/python dsf_bridge.py`, or install `dsf-bridge.service` as a user unit.
4. On the Thor: DS Forever → Streaming → enter the 6-digit code the bridge prints.
5. Moonlight PIN: the bridge prints a 4-digit PIN; type it in Sunshine's web UI (PIN page), or give the bridge
   `SUNSHINE_USER` / `SUNSHINE_PASS` so it does it itself.

## Not done (vs Desktop)
TLS (wss), bringing the WoW window to the front, starting WoW / Battle.net, Sunshine app "WoW Forever" (the Thor
falls back to "Desktop"), sign-in screen detection (`screen` is reported as `world` while WoW runs).
