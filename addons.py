# SPDX-License-Identifier: GPL-3.0-or-later
# dsf-linux-helper: unofficial Linux helper for DS Forever (GPL-3.0). See README.md.
"""DS Forever's add-on set on a Linux PC: same rules as Desktop's AddonInstaller.
- source: upstream DS Forever's latest release source zip (checked against SHA256SUMS), or a local folder (DSF_ADDONS_SRC);
- install when missing (only when asked), update when the game's set stamp is older;
- backup first, every copied file checked against manifest.txt's md5, old set restored on any failure;
- leave no trace: only Interface/AddOns/<the set's own folders> is ever written."""
import hashlib, io, json, re, shutil, tempfile, urllib.request, zipfile
from pathlib import Path

UPSTREAM = "Jreese702/DS-Forever"
ASSET_PREFIX = "companion/app/src/main/assets/companion/"
CACHE = Path.home() / ".cache/dsf-bridge"


def parse_manifest(text):
    """('set N' line, {rel_path: md5})"""
    set_no, files = 0, {}
    for line in text.splitlines():
        if line.startswith("set "):
            set_no = int(line[4:].strip() or 0)
        elif len(line) > 34 and re.match(r"^[0-9a-f]{32}  ", line):
            files[line[34:].strip()] = line[:32]
    return set_no, files


def installed_set(addons_dir):
    """The set stamp of the installed WowCompanion add-on (its .toc '## Version: Set N'), 0 = none."""
    toc = Path(addons_dir) / "WowCompanion/WowCompanion.toc"
    try:
        m = re.search(r"^## Version:\s*Set\s+(\d+)", toc.read_text(errors="replace"), re.M)
        return int(m.group(1)) if m else 0
    except OSError:
        return 0


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "dsf-linux-bridge"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_upstream(log=print):
    """Download (once per version) and verify upstream's latest source zip; return a folder with manifest.txt + addons/."""
    import time
    meta = CACHE / "latest.json"
    try:
        cached = json.loads(meta.read_text())
        fresh = time.time() - cached.get("_at", 0) < 3 * 3600      # ask GitHub at most every 3 hours
    except (OSError, ValueError):
        cached, fresh = None, False
    if fresh:
        rel = cached
    else:
        try:
            rel = json.loads(_get(f"https://api.github.com/repos/{UPSTREAM}/releases/latest", 20))
            rel["_at"] = time.time()
            CACHE.mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps({k: rel[k] for k in ("tag_name", "assets", "_at")}))
        except Exception:
            if not cached:
                raise
            rel = cached                                            # offline: use what we know
    assets = {a["name"]: a["browser_download_url"] for a in rel["assets"]}
    name = next((n for n in assets if n.endswith("-source.zip") and n.startswith("DS-Forever-")), None)
    if not name or "SHA256SUMS" not in assets:
        raise RuntimeError("upstream release has no source zip / SHA256SUMS")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", rel["tag_name"]) or rel["tag_name"] in (".", ".."):
        raise RuntimeError("odd upstream tag name")
    out = CACHE / rel["tag_name"]
    if (out / "manifest.txt").exists():
        return out
    sums = _get(assets["SHA256SUMS"], 20).decode()
    want = next((l.split()[0].lower() for l in sums.splitlines() if l.strip().endswith(name)), None)
    if not want:
        raise RuntimeError(f"{name} is not in SHA256SUMS")
    log(f"Downloading {name} from {UPSTREAM} …")
    data = _get(assets[name], 600)
    if hashlib.sha256(data).hexdigest() != want:
        raise RuntimeError(f"{name}: SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if ASSET_PREFIX in n and not n.endswith("/")]
        if not names:
            raise RuntimeError("no add-ons in the source zip")
        root = names[0][:names[0].index(ASSET_PREFIX) + len(ASSET_PREFIX)]
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(dir=CACHE))        # same filesystem as `out`, so the rename below works
        for n in names:
            if not n.startswith(root):
                continue
            rel_path = n[len(root):]
            if not (rel_path == "manifest.txt" or rel_path.startswith("addons/")) or ".." in rel_path:
                continue
            dst = tmp / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(n))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    return out


def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def install(src, addons_dir, force=False, allow_new=False, log=print):
    """Install/update the set from src into addons_dir. Returns a one-line status."""
    src, addons_dir = Path(src), Path(addons_dir)
    if not addons_dir.is_dir():
        return f"no AddOns folder at {addons_dir}"
    set_no, files = parse_manifest((src / "manifest.txt").read_text())
    if not files:
        return "the add-on source has an empty manifest"
    bad = [rel for rel in files if rel.startswith("/") or "\\" in rel or ".." in rel.split("/")
           or not rel.split("/", 1)[0].startswith("WowCompanion") or "/" not in rel]
    if bad:                                   # we promise to write only Interface/AddOns/WowCompanion*
        return f"add-on source refused: unexpected path {bad[0]!r}"
    folders = sorted({rel.split("/", 1)[0] for rel in files})
    have = installed_set(addons_dir)
    missing = [f for f in folders if not (addons_dir / f).is_dir()]
    differs = [rel for rel, md5 in files.items()
               if not (addons_dir / rel).is_file() or _md5(addons_dir / rel) != md5]
    if not differs:
        return f"add-ons up to date (set {set_no})"
    if not force:
        if have == 0 and not allow_new:
            return f"add-ons not installed (set {set_no} available)"
        if have and have >= set_no and not missing:
            return f"installed set {have} differs from {set_no}; left alone (install with force)"
    backup = CACHE / "addons-backup"                  # outside the game: only our own add-on folders are written there
    shutil.rmtree(backup, ignore_errors=True)
    backup.mkdir(parents=True)
    for f in folders:
        if (addons_dir / f).is_dir():
            shutil.copytree(addons_dir / f, backup / f)
    try:
        for rel, md5 in files.items():
            s, d = src / "addons" / rel, addons_dir / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, d)
            if _md5(d) != md5:
                raise RuntimeError(f"{rel}: checksum mismatch after copy")
        for f in folders:                       # files the set no longer has go, inside our own folders only
            for p in (addons_dir / f).rglob("*"):
                if p.is_file() and str(p.relative_to(addons_dir)) not in files:
                    p.unlink()
    except Exception as e:
        for f in folders:
            shutil.rmtree(addons_dir / f, ignore_errors=True)
            if (backup / f).is_dir():
                shutil.copytree(backup / f, addons_dir / f)
        return f"add-on install failed, old set restored: {e}"
    shutil.rmtree(backup, ignore_errors=True)
    msg = f"add-ons {'updated' if have else 'installed'}: set {have or '-'} → {set_no} (/reload in game)"
    log(msg)
    return msg
