"""The log follower (dsf_bridge.Tailer), off-device. beta 2026-11-20: the poll is a steady 25 ms, and a poll with nothing new must
return at once (one stat, no open), while growth, a truncation and a new file are still seen. Run: .venv/bin/python -m unittest
discover -s tests"""
import os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import dsf_bridge  # noqa: E402


def doc_line(seq, body):
    return f"11/20 21:00:00.000  [N][Lua] WCB1|{seq}|1/1|{body}\n"


class TailerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "General.log"
        self.path.write_text(doc_line(1, '{"type":"hello"}'))
        self.t = dsf_bridge.Tailer(self.path)
        self.t.poll()                                   # the first look: the backlog

    def tearDown(self):
        self.dir.cleanup()

    def docs(self, out):
        return [m for m in out if m.get("t") == "doc"]

    def test_unchanged_log_is_not_opened(self):
        with mock.patch("builtins.open", side_effect=AssertionError("opened")):
            self.assertEqual(self.t.poll(), [])

    def test_growth_is_read(self):
        with open(self.path, "a") as f:
            f.write(doc_line(2, '{"type":"pos","x":1}'))
        out = self.docs(self.t.poll())
        self.assertEqual(len(out), 1)
        self.assertIn('"pos"', out[0]["doc"])

    def test_truncation_restarts(self):
        self.path.write_text("")
        self.path.write_text(doc_line(1, '{"type":"hello"}')[:20])
        with mock.patch.object(dsf_bridge.wow, "restart"):
            out = self.t.poll()
        self.assertTrue(any(m.get("t") == "log" and m.get("event") == "restart" for m in out), out)


if __name__ == "__main__":
    unittest.main()
