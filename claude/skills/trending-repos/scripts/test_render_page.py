"""Tests for render_page.py: merging, validation, rendering, opening and marking seen."""

import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import render_page
import trending

TODAY = "2026-11-03"
SUMMARY = {"what": "Faz algo. Muito bem.", "who": "Devs.", "alternatives": None,
           "maturity": "beta", "translated_from": None}


def repo(name, stars=100, description="A tool"):
    return {"name": name, "url": f"https://github.com/{name}", "source": "github", "rank": 1,
            "gained": stars, "description": description, "homepage": None,
            "stars": stars, "forks": 1, "issues": 0, "language": "Go", "license": "MIT",
            "created": "2026-11-01", "pushed": "2026-11-03", "image": None, "readme": "# R"}


def public(name):
    entry = repo(name)
    del entry["readme"]
    return {**entry, "summary": None}


class MergeTest(unittest.TestCase):
    def test_merge_sorts_by_stars_and_drops_readme(self):
        page = render_page.merge([repo("a/a", stars=10), repo("b/b", stars=900),
                                  repo("c/c", stars=None)], {}, TODAY, None)
        self.assertEqual([r["name"] for r in page["repos"]], ["b/b", "a/a", "c/c"])
        self.assertNotIn("readme", page["repos"][0])

    def test_merge_keeps_repo_without_summary(self):
        page = render_page.merge([repo("a/a")], {}, TODAY, None)
        self.assertIsNone(page["repos"][0]["summary"])

    def test_merge_attaches_summary(self):
        page = render_page.merge([repo("a/a")], {"a/a": SUMMARY}, TODAY, None)
        self.assertEqual(page["repos"][0]["summary"], SUMMARY)

    def test_merge_adds_to_todays_page_and_drops_yesterdays(self):
        today = {"date": TODAY, "repos": [public("old/one")]}
        yesterday = {"date": "2026-11-02", "repos": [public("old/one")]}

        def names(page):
            return {r["name"] for r in page["repos"]}

        self.assertEqual(names(render_page.merge([repo("n/n")], {}, TODAY, today)),
                         {"old/one", "n/n"})
        self.assertEqual(names(render_page.merge([repo("n/n")], {}, TODAY, yesterday)), {"n/n"})

    def test_rejects_unknown_repo_and_bad_maturity(self):
        for summaries in ({"x/x": SUMMARY}, {"a/a": {**SUMMARY, "maturity": "alpha"}},
                          {"a/a": {**SUMMARY, "what": ""}}, {"a/a": "texto"}, ["a/a"]):
            with self.subTest(summaries=summaries), self.assertRaises(SystemExit):
                render_page.merge([repo("a/a")], summaries, TODAY, None)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        state = root / "state"
        self.seen = state / "seen.json"
        # trending.py resolves its state paths at import, so they are patched on the module.
        for patcher in (mock.patch.dict(os.environ, {"TRENDING_WORKDIR": str(root / "work")}),
                        mock.patch.object(trending, "STATE", state),
                        mock.patch.object(trending, "SEEN", self.seen)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.page = root / "work" / "today.html"
        self.repos_file = root / "repos.json"
        self.summaries_file = root / "summaries.json"
        self.write([repo("a/a"), repo("b/b")], {"a/a": SUMMARY})

    def write(self, repos, summaries):
        self.repos_file.write_text(json.dumps({"repos": repos}))
        self.summaries_file.write_text(json.dumps(summaries))

    def run_main(self, opened=True):
        with (mock.patch("render_page.open_page", return_value=opened),
              contextlib.redirect_stdout(io.StringIO())):
            render_page.main([str(self.repos_file), str(self.summaries_file)])

    def test_hostile_text_cannot_close_the_script(self):
        self.write([repo("a/a", description="</script><img src=x onerror=alert(1)>")], {})
        self.run_main()
        html = self.page.read_text()
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn('"\\u003c/script>\\u003cimg', html)

    def test_comment_opener_cannot_swallow_the_script_end(self):
        self.write([repo("a/a", description="<!--<script> parser")], {})
        self.run_main()
        html = self.page.read_text()
        self.assertNotIn("<!--", html)
        self.assertNotIn("<script> parser", html)

    def test_chrome_failure_writes_page_but_marks_nothing(self):
        with self.assertRaises(SystemExit):
            self.run_main(opened=False)
        self.assertTrue(self.page.exists())
        self.assertFalse(self.seen.exists())

    def test_success_marks_every_repo_on_the_page(self):
        self.run_main()
        self.assertEqual(set(json.loads(self.seen.read_text())), {"a/a", "b/b"})

    def test_open_without_todays_page_fails(self):
        with self.assertRaises(SystemExit):
            render_page.main(["--open"])


if __name__ == "__main__":
    unittest.main()
