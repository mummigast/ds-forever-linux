# Handoff (the Linux helper, DS Forever Linux Streaming Edition)

Goal: stream WoW Forever from a Linux PC (Steam/Proton + Sunshine) to an AYN Thor running this repository's Streaming
Edition app; this helper replaces DS Forever Desktop. Read ../FORK.md (what the app changes and why), README.md, SAFETY.md.

State 2026-11-17: works end to end on a real Thor, at home and over WireGuard: pairing (also by **PC address…**), automatic
Sunshine PIN when SUNSHINE_USER/PASS are set, WoW start from the Thor, add-ons installed from this repository, HUD
switches and bottom-screen buttons in the game world, Reload UI. NOT yet: clicks while a WoW window is open (vendor, game
menu, settings): WoW's controller cursor takes them to the screen centre (padstray). Tests: `.venv/bin/python -m unittest discover -s tests`.

What made clicks work on Linux (app side, StreamKeys/GameUi; details in FORK.md):
- WoW in controller mode only gives its cursor to the mouse on real motion: a 4 px relative nudge (out, wait, back) before
  each click. +1/-1 at once sums to nothing within one frame.
- The pointer lands ~1 px up-left of the aim through Sunshine -> uinput -> KWin -> XWayland -> Wine; the tap pad's rows are
  ~2 px, so the click hit the row above. +1 px fixes it. Measured with a `/run` probe logging GetCursorPosition and
  GetMouseFoci through C_Log.LogMessage (close the app while typing: its taps close the chat box).
- A Thor that joins a running game only gets replayed documents: the character came from a replayed one (else no
  per-character switch was ever sent).

Helper side (this folder): WoW start = Battle.net via its Steam shortcut, then `Battle.net.exe --exec="launch WoWF"` in the
same prefix, resent every 40 s while waiting; an old Battle.net that ignores it is closed (by PID, matched on the env Proton
sets) and started fresh once.

Known open points: camera drift right after connecting (the nudge or the virtual pad's first state; not settled); the add-on
data rate is about 10-20 KB/s (most of General.log is `WCB1|pad|` filler, skipped).

Rules: never hand out an APK; commit as mummigast's noreply address only; nothing personal in files.
