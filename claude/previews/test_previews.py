import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from unittest import mock

import choices
import own
import serve
import store


class PreviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(store, "ROOT", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name, text):
        with open(os.path.join(self.tmp.name, name), "w") as f:
            f.write(text)


class SnapshotTest(PreviewTest):
    def test_new_content_gets_new_version(self):
        self.write("a.html", "one")
        self.assertEqual(store.snapshot("a"), 1)
        self.assertEqual(store.snapshot("a"), 1)
        self.write("a.html", "two")
        self.assertEqual(store.snapshot("a"), 2)
        self.assertEqual(store.versions("a"), [1, 2])

    def test_missing_preview(self):
        self.assertIsNone(store.snapshot("nope"))

    def test_preview_being_written_is_not_saved(self):
        self.write("a.html", "half")
        self.assertIsNone(store.snapshot("a", settle=60))
        self.assertEqual(store.versions("a"), [])


class OwnTest(PreviewTest):
    def test_named_and_recent_preview_is_owned(self):
        self.write("mask.html", "x")
        self.write("mcms-mask.html", "x")
        call = {"command": f"cat > {store.ROOT}/mcms-mask.html"}
        topics = own.written(call, time.time())
        self.assertEqual(topics, ["mcms-mask"])

    def test_bare_name_needs_the_folder(self):
        self.write("plan.html", "x")
        self.assertEqual(own.written({"file_path": "/home/u/proj/plan.html"}, time.time()), [])
        call = {"command": f"cd {store.ROOT} && cat > plan.html"}
        self.assertEqual(own.written(call, time.time()), ["plan"])

    def test_old_preview_is_not_owned(self):
        self.write("a.html", "x")
        call = {"file_path": f"{store.ROOT}/a.html"}
        self.assertEqual(own.written(call, time.time() + 120), [])


class ChoicesTest(PreviewTest):
    def run_hook(self, session, transcript=None):
        hook = {"session_id": session, "transcript_path": transcript}
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(json.dumps(hook))), redirect_stdout(out):
            choices.main()
        return out.getvalue()

    def test_owner_receives_choice_once(self):
        self.write("a.html", "v1")
        store.snapshot("a")
        store.set_owner("a", "s1")
        self.write("a.choice.json", json.dumps({"version": 1, "variant": "B"}))
        self.assertEqual(self.run_hook("s2"), "")
        out = self.run_hook("s1")
        self.assertIn("preview `a` (for version 1)", out)
        self.assertIn('"variant": "B"', out)
        self.assertEqual(self.run_hook("s1"), "")
        archived = os.listdir(store.history("a"))
        self.assertTrue(any(n.startswith("1-") and n.endswith(".choice.json") for n in archived))

    def test_forged_version_stays_in_history(self):
        self.write("a.html", "v1")
        store.snapshot("a")
        store.set_owner("a", "s1")
        self.write("a.choice.json", json.dumps({"version": "../../../escape"}))
        self.assertIn("unversioned", self.run_hook("s1"))
        self.assertTrue(any(n.startswith("unversioned-") for n in os.listdir(store.history("a"))))

    def test_outdated_choice_names_current_version(self):
        self.write("a.html", "v1")
        store.snapshot("a")
        self.write("a.html", "v2")
        store.snapshot("a")
        store.set_owner("a", "s1")
        self.write("a.choice.json", json.dumps({"version": 1}))
        self.assertIn("now at version 2", self.run_hook("s1"))

    def test_unowned_choice_falls_back_to_transcript(self):
        self.write("a.html", "v1")
        self.write("a.choice.json", "{}")
        transcript = os.path.join(self.tmp.name, "t.jsonl")
        self.write("t.jsonl", f"wrote {self.tmp.name}/a.html")
        self.assertIn("unversioned", self.run_hook("s1", transcript))


class BarTest(PreviewTest):
    def test_preview_gets_bar_before_body_end(self):
        self.write("a.html", "x")
        page = serve.with_bar(b"<body><p>x</p></body>", "a.html").decode()
        self.assertIn('"topic": "a", "version": null, "versions": [], "current": true', page)
        self.assertTrue(page.endswith("</body>"))
        with mock.patch.object(serve, "SETTLE", 0):
            page = serve.with_bar(b"x", "a.html").decode()
        self.assertIn('"version": 1, "versions": [1], "current": true', page)

    def test_old_version_is_not_current(self):
        self.write("a.html", "one")
        store.snapshot("a")
        self.write("a.html", "two")
        store.snapshot("a")
        page = serve.with_bar(b"x", ".history/a/1.html").decode()
        self.assertIn('"version": 1, "versions": [1, 2], "current": false', page)

    def test_other_pages_are_untouched(self):
        self.assertEqual(serve.with_bar(b"x", "dir/page.html"), b"x")


if __name__ == "__main__":
    unittest.main()
