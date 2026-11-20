# SPDX-License-Identifier: GPL-3.0-or-later
"""pc_addons.py: the Thor's managed add-ons on the PC (Linux Edition). Run: .venv/bin/python -m unittest discover -s tests"""
import hashlib, io, json, sys, tempfile, unittest, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import pc_addons  # noqa: E402


def make_zip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
    return b.getvalue()


class FakeResp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class PcAddons(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.game = self.tmp / "game"
        (self.game / "Interface/AddOns").mkdir(parents=True)
        acct = self.game / "WTF/Account/ACC"
        acct.mkdir(parents=True)
        (acct / "AddOns.txt").write_text("Questie: enabled\nManners: disabled\n")
        self.zip = make_zip({"Manners/Manners.toc": "## Title: Manners\n", "Manners/core.lua": "x=1\n", "LICENSE": "MIT\n"})
        self.urls = []
        self.m = {"id": "manners", "key": "core", "title": "Manners", "tag": "1.11.0", "asset": "Manners-v1.11.0.zip",
                  "bytes": len(self.zip), "sha256": hashlib.sha256(self.zip).hexdigest(), "folders": ["Manners"],
                  "url": "https://mediafilez.forgecdn.net/files/9408/996/Manners-v1.11.0.zip", "license": "MIT", "want": True}

    def opener(self, req, timeout=0):
        self.urls.append(req.full_url)
        return FakeResp(self.zip)

    def go(self, want, running=False):
        return pc_addons.run(want, self.game, self.tmp / "rec.json", self.tmp / "cache", running, lambda *a: None, self.opener)

    def test_sources(self):
        self.assertEqual(pc_addons.source_url({"id": "polestar", "tag": "v0.2.5", "asset": "Polestar.zip"}),
                         "https://github.com/fitzforge/polestar/releases/download/v0.2.5/Polestar.zip")
        self.assertIsNone(pc_addons.source_url({"id": "manners", "asset": "a.zip", "url": "https://evil.example/files/1/a.zip"}))
        self.assertIsNone(pc_addons.source_url({"id": "other", "tag": "1", "asset": "a.zip"}))
        self.assertIsNone(pc_addons.source_url({"id": "polestar", "tag": "../x", "asset": "a.zip"}))

    def test_install_enable_and_ok_then_remove(self):
        r = self.go({"managed": [self.m], "enabled": {"Manners": True, "Questie": False}})
        self.assertEqual([i["state"] for i in r["items"]], ["installed"])
        a = self.game / "Interface/AddOns/Manners"
        self.assertTrue((a / "core.lua").is_file() and (a / "LICENSE").is_file())
        txt = (self.game / "WTF/Account/ACC/AddOns.txt").read_text()
        self.assertIn("Manners: enabled", txt)
        self.assertIn("Questie: enabled", txt)          # not ours: never changed
        self.assertFalse((self.game / "Interface" / pc_addons.STAGING).exists())
        r = self.go({"managed": [self.m]})
        self.assertEqual(r["items"][0]["state"], "ok")
        self.assertEqual(len(self.urls), 1)              # cached, not fetched again
        r = self.go({"managed": [dict(self.m, want=False)]})
        self.assertEqual(r["items"][0]["state"], "removed")
        self.assertFalse(a.exists())
        self.assertEqual(len(list((self.game / "Interface" / pc_addons.BACKUP).iterdir())), 1)   # moved, not deleted

    def test_yours_is_left_alone(self):
        (self.game / "Interface/AddOns/Manners").mkdir()
        (self.game / "Interface/AddOns/Manners/mine.lua").write_text("mine")
        r = self.go({"managed": [self.m]})
        self.assertEqual(r["items"][0]["state"], "yours")
        self.assertTrue((self.game / "Interface/AddOns/Manners/mine.lua").is_file())
        self.assertEqual(self.urls, [])

    def test_bad_hash_refused_and_running_deferred(self):
        r = self.go({"managed": [dict(self.m, sha256="0" * 64)]})
        self.assertEqual(r["items"][0]["state"], "failed")
        self.assertFalse((self.game / "Interface/AddOns/Manners").exists())
        r = self.go({"managed": [self.m]}, running=True)
        self.assertEqual(r["items"][0]["state"], "deferred")
        self.assertFalse((self.game / "Interface/AddOns/Manners").exists())

    def test_zip_must_hold_the_pinned_folders(self):
        bad = make_zip({"Other/x.lua": "x"})
        self.zip = bad
        r = self.go({"managed": [dict(self.m, bytes=len(bad), sha256=hashlib.sha256(bad).hexdigest())]})
        self.assertEqual(r["items"][0]["state"], "failed")
        self.assertFalse((self.game / "Interface/AddOns/Other").exists())


if __name__ == "__main__":
    unittest.main()
