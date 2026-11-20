# SPDX-License-Identifier: GPL-3.0-or-later
# dsf-linux-helper: unofficial Linux helper for DS Forever (GPL-3.0). See README.md.
"""The Thor's add-ons on the PC (Linux Edition, 2026-11-20; the user: "let the helper install add-ons on PC").

The Thor sends "addons_want" after every welcome (desktop/docs/STREAM_BRIDGE_PROTOCOL.md, "The Thor's add-ons on the PC"). This is
the Linux helper's side, the same rules as DS Forever Desktop's PcAddons, kept small:
- only the MANAGED packages (Settings > Add-ons: Polestar, Spoken, Manners, QuestTrail), each ONLY from its own source and pin:
  polestar / spoken from that repository's GitHub release by the pinned tag, manners / questtrail from forgecdn's file CDN; any
  other id or host is refused; size and sha256 checked before anything is unpacked;
- a folder this helper did not put in ("yours": the player's own copy, e.g. a Questie installed by hand) is never touched;
- nothing is deleted: a replaced or no longer wanted copy of ours goes to Interface/AddOns-backup-dsforever;
- unpacked into Interface/AddOns-staging-dsforever first, moved in folder by folder, the zip's licence files into every folder;
- never while WoW runs (deferred: the bridge runs it again before it starts WoW and when WoW closes);
- the Thor's on / off for OUR folders goes into the PC's AddOns.txt files.
Not here (Desktop only): QuestieDB updates, the Thor's imported add-ons (they need a pinned file transfer)."""
import hashlib, json, re, shutil, time, urllib.request, zipfile
from pathlib import Path

REPOS = {"polestar": "fitzforge/polestar", "spoken": "rusty-key/spoken-wow"}
CDN = "https://mediafilez.forgecdn.net/files/"
CDN_IDS = {"manners", "questtrail"}
STAGING, BACKUP = "AddOns-staging-dsforever", "AddOns-backup-dsforever"
NOTICE = re.compile(r"^(LICEN[CS]E|COPYING|THIRD[_-]?PARTY|NOTICES?|CREDITS)([._-].*)?$", re.I)
SAFE = re.compile(r"^[A-Za-z0-9_.\- ]{1,64}$")
MAX_BYTES = 4 * 1024 ** 3


def source_url(m):
    """The one URL a managed package may come from, or None (refused)."""
    pid, tag, asset, url = m.get("id"), m.get("tag") or "", m.get("asset") or "", m.get("url") or ""
    if not SAFE.match(asset):
        return None
    if pid in REPOS and not url:
        if not re.match(r"^[A-Za-z0-9_.\-/]{1,80}$", tag) or any(s in ("", ".", "..") for s in tag.split("/")):
            return None
        return f"https://github.com/{REPOS[pid]}/releases/download/{tag}/{asset}"
    if pid in CDN_IDS and url.startswith(CDN) and url.endswith("/" + asset) and re.match(r"^[0-9/]+$", url[len(CDN):-len(asset) - 1]):
        return url
    return None


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(m, cache, log=print, opener=None):
    """The package's zip in [cache], downloaded (resumed) from its own source, its size and sha256 as pinned; returns the path."""
    url = source_url(m)
    if not url:
        raise ValueError("refused: not its own source")
    size, sha = int(m.get("bytes") or 0), str(m.get("sha256") or "").lower()
    if not (0 < size <= MAX_BYTES) or not re.match(r"^[0-9a-f]{64}$", sha):
        raise ValueError("refused: no pin")
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{sha}.zip"
    if dest.is_file() and dest.stat().st_size == size and _sha256(dest) == sha:
        return dest
    part = cache / f"{sha}.part"
    have = part.stat().st_size if part.is_file() else 0
    if have > size:
        part.unlink(); have = 0
    if have < size:
        req = urllib.request.Request(url, headers={"User-Agent": "dsf-linux-bridge", **({"Range": f"bytes={have}-"} if have else {})})
        with (opener or urllib.request.urlopen)(req, timeout=120) as r:
            if have and getattr(r, "status", 200) != 206:
                have = 0                                  # no resume: start over
            with open(part, "ab" if have else "wb") as f:
                got = have
                for b in iter(lambda: r.read(1 << 20), b""):
                    got += len(b)
                    if got > size:
                        raise ValueError("bigger than its pin")
                    f.write(b)
    if part.stat().st_size != size or _sha256(part) != sha:
        part.unlink(missing_ok=True)
        raise ValueError("size or sha256 differs from its pin")
    part.rename(dest)
    log(f"pc add-ons: {m.get('title') or m.get('id')} downloaded")
    return dest


def _record(path):
    try:
        d = json.loads(Path(path).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _backup(src, iface):
    b = iface / BACKUP
    b.mkdir(exist_ok=True)
    dst = b / f"{src.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.move(str(src), str(dst))


def _install(zp, m, addons, iface, ours):
    """Unpack [zp] into staging, check its top folders are exactly the pinned ones, then move them in (our old copies to backup)."""
    folders = [f for f in m.get("folders") or [] if SAFE.match(str(f))]
    if not folders:
        raise ValueError("no folders pinned")
    stage = iface / STAGING / f"{m.get('id')}-{m.get('key')}"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    try:
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            for n in names:
                p = Path(n)
                if p.is_absolute() or ".." in p.parts:
                    raise ValueError("unsafe path in the zip")
            tops = {Path(n).parts[0] for n in names if Path(n).parts and (len(Path(n).parts) > 1 or n.endswith("/"))}
            missing = [f for f in folders if f not in tops]
            if missing:
                raise ValueError("the zip lacks " + ", ".join(missing))
            z.extractall(stage)
        notices = [p for p in stage.iterdir() if p.is_file() and NOTICE.match(p.name)]
        for f in folders:
            for n in notices:
                if not (stage / f / n.name).exists():
                    shutil.copy2(n, stage / f / n.name)
        for f in folders:
            target = addons / f
            if target.exists():
                _backup(target, iface)
            shutil.move(str(stage / f), str(target))
            ours[f] = {"id": m.get("id"), "key": m.get("key"), "in": m.get("tag"), "at": int(time.time())}
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        try:
            (iface / STAGING).rmdir()
        except OSError:
            pass


def addons_txt(game_dir, enabled, ours, log=print):
    """The Thor's on / off for OUR folders into every account's AddOns.txt (lines "Folder: enabled|disabled"); nothing else changes."""
    n = 0
    for f in (Path(game_dir) / "WTF" / "Account").glob("*/AddOns.txt"):
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        seen, out, changed = set(), [], False
        for ln in lines:
            name = ln.split(":", 1)[0].strip()
            if name in ours and name in enabled:
                want = f"{name}: {'enabled' if enabled[name] else 'disabled'}"
                seen.add(name)
                if ln.strip() != want:
                    ln, changed = want, True
            out.append(ln)
        for name in sorted(set(enabled) & set(ours) - seen):
            out.append(f"{name}: {'enabled' if enabled[name] else 'disabled'}"); changed = True
        if changed:
            f.write_text("\n".join(out) + "\n"); n += 1
    if n:
        log(f"pc add-ons: AddOns.txt updated in {n} account(s)")


def run(want, game_dir, record_path, cache, wow_running, log=print, opener=None):
    """One pass over the Thor's "addons_want". Returns the "addons_pc" done message."""
    game_dir = Path(game_dir)
    iface, addons = game_dir / "Interface", game_dir / "Interface" / "AddOns"
    items = []
    if wow_running:
        return {"t": "addons_pc", "state": "done", "ok": True, "line": "Add-ons wait until WoW is closed on your PC",
                "items": [{"name": m.get("title") or m.get("id"), "state": "deferred", "why": "WoW is running"}
                          for m in want.get("managed") or [] if isinstance(m, dict) and m.get("want")]}
    rec = _record(record_path)
    ours = rec.setdefault("ours", {})
    for m in want.get("managed") or []:
        if not isinstance(m, dict):
            continue
        name = m.get("title") or m.get("id") or "?"
        folders = [f for f in m.get("folders") or [] if SAFE.match(str(f))]
        mine = [f for f in folders if f in ours and ours[f].get("id") == m.get("id")]
        try:
            if not m.get("want"):
                for f in mine:
                    if (addons / f).exists():
                        _backup(addons / f, iface)
                    ours.pop(f, None)
                if mine:
                    items.append({"name": name, "state": "removed"})
                continue
            theirs = [f for f in folders if (addons / f).exists() and f not in mine]
            if theirs:
                items.append({"name": name, "state": "yours", "why": f"{theirs[0]} of yours is there: left as it is"}); continue
            if mine and len(mine) == len(folders) and all(ours[f].get("in") == m.get("tag") and (addons / f).is_dir() for f in mine):
                items.append({"name": name, "state": "ok"}); continue
            if not source_url(m):
                items.append({"name": name, "state": "refused", "why": "not from its own source"}); continue
            zp = fetch(m, Path(cache), log, opener)
            _install(zp, m, addons, iface, ours)
            items.append({"name": name, "state": "updated" if mine else "installed"})
            log(f"pc add-ons: {name} {m.get('tag')} {'updated' if mine else 'installed'}")
        except Exception as e:
            items.append({"name": name, "state": "failed", "why": str(e)[:120]})
            log(f"pc add-ons: {name}: {e}")
    if want.get("imported"):
        items.append({"name": "Imported add-ons", "state": "skipped", "why": "only with DS Forever Desktop"})
    enabled = {k: bool(v) for k, v in (want.get("enabled") or {}).items() if isinstance(k, str) and not k.lower().startswith("wowcompanion")}
    if enabled and ours:
        addons_txt(game_dir, enabled, ours, log)
    Path(record_path).parent.mkdir(parents=True, exist_ok=True)
    Path(record_path).write_text(json.dumps(rec, indent=1))
    bad = [i for i in items if i["state"] in ("failed", "refused", "yours")]
    line = "Add-ons on your PC up to date" if not bad else f"{bad[0]['name']}: {bad[0].get('why') or bad[0]['state']}"
    return {"t": "addons_pc", "state": "done", "ok": not any(i["state"] in ("failed", "refused") for i in items), "line": line,
            "items": items}
