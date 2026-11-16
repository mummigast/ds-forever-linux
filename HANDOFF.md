# Handoff (fork)
Goal: Linux alternative to DS Forever Desktop: official APK on the Thor + `linux-bridge/` helper on the PC (Steam/Proton WoW).
Private now, public later. Read README.md and SAFETY.md. Moved here from the private DS Forever fork (~/ds-forever, kept as reference) on 2026-11-16.

State 2026-11-16 (helper 0.2): installed here with install.sh (user service `dsf-bridge`, command `dsf-bridge`), ws+wss on
48210 (LAN only, not forwarded), doctor all green. Tests: `.venv/bin/python -m unittest discover -s tests` (fake Thor).

Untested until the owner has the Thor:
1. Real Thor pairing + Moonlight PIN in Sunshine (manual PIN: `dsf-bridge code`).
2. WoW auto-start: `proton run Battle.net.exe --exec=launch_uid wowf` while Steam's Proton (container) already runs Battle.net.
   If it fails, fallback idea: set Battle.net's shortcut launch options, or DSF_START_CMD.
3. Process names under Wine (`pid_of` matches comm "Wow.exe", falls back to command line).
4. KDE focus with a real WoW window; taps alignment on the streamed monitor.
5. DS add-ons auto-install on first Thor connect (game not touched yet).

Before going public: Thor test, final privacy/history check, first release (tag + notes). Never ship an APK.
Commit as mummigast noreply only; nothing personal in files.

Checked 2026-11-16: no other Linux helper exists (upstream issues, the 5 GitHub forks: none ahead of upstream, web search).
Thor compatibility read from upstream's app code: the app picks Sunshine's ports from our welcome ("Desktop" path), has no
version gate, and falls back to plain Sunshine without a bridge. So the official APK + this helper should be a drop-in.
