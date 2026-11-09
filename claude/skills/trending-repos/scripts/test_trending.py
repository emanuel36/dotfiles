"""Tests for the enrichment of fetched repositories in trending.py."""

import io
import json
import unittest
import urllib.error
from unittest import mock

import trending

REPO_JSON = {
    "stargazers_count": 1200,
    "forks_count": 30,
    "open_issues_count": 4,
    "language": "Rust",
    "license": {"spdx_id": "MIT"},
    "created_at": "2026-10-30T12:00:00Z",
    "pushed_at": "2026-11-03T08:00:00Z",
    "homepage": "https://example.org",
    "description": "A tool",
}


def fake_get(url, headers=None):
    if url.endswith("/readme"):
        return "x" * (trending.README_CHARS + 500)
    return json.dumps(REPO_JSON)


def rate_limited(url, headers=None):
    raise urllib.error.HTTPError(url, 403, "rate limit exceeded", {}, io.BytesIO())


class FirstImageTest(unittest.TestCase):
    def test_first_image_skips_badges(self):
        readme = ("[![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)](x)\n"
                  "![stars](https://img.shields.io/github/stars/o/r)\n"
                  "![demo](docs/demo.gif)")
        self.assertEqual(trending.first_image(readme, "o/r"),
                         "https://raw.githubusercontent.com/o/r/HEAD/docs/demo.gif")

    def test_first_image_reads_html_and_absolute_urls(self):
        readme = '<p><img width="600" src="https://user-images.githubusercontent.com/1/a.png"></p>'
        self.assertEqual(trending.first_image(readme, "o/r"),
                         "https://user-images.githubusercontent.com/1/a.png")

    def test_first_image_rewrites_blob_urls(self):
        readme = "![shot](https://github.com/o/r/blob/main/shot.png)"
        self.assertEqual(trending.first_image(readme, "o/r"),
                         "https://raw.githubusercontent.com/o/r/main/shot.png")

    def test_first_image_skips_star_history_charts(self):
        readme = ("![chart](https://api.star-history.com/chart?repos=o/r)\n"
                  "![shot](shot.png)")
        self.assertEqual(trending.first_image(readme, "o/r"),
                         "https://raw.githubusercontent.com/o/r/HEAD/shot.png")

    def test_first_image_keeps_repos_named_like_badges(self):
        url = "https://raw.githubusercontent.com/dgraph-io/badger/main/shot.png"
        self.assertEqual(trending.first_image(f"![shot]({url})", "dgraph-io/badger"), url)

    def test_first_image_completes_protocol_relative_urls(self):
        self.assertEqual(trending.first_image('<img src="//cdn.example.com/shot.png">', "o/r"),
                         "https://cdn.example.com/shot.png")

    def test_first_image_none_without_images(self):
        self.assertIsNone(trending.first_image("# Title\nText only.", "o/r"))


class EnrichTest(unittest.TestCase):
    @mock.patch("trending.github_token", return_value=None)
    @mock.patch("trending.get", side_effect=fake_get)
    def test_enrich_fills_numbers_and_truncates_readme(self, _get, _token):
        repo = trending.enrich({"name": "o/r"})
        self.assertEqual((repo["stars"], repo["forks"], repo["issues"]), (1200, 30, 4))
        self.assertEqual((repo["language"], repo["license"]), ("Rust", "MIT"))
        self.assertEqual((repo["created"], repo["pushed"]), ("2026-10-30", "2026-11-03"))
        self.assertEqual(repo["homepage"], "https://example.org")
        self.assertEqual(len(repo["readme"]), trending.README_CHARS)

    @mock.patch("trending.github_token", return_value=None)
    @mock.patch("trending.get", side_effect=rate_limited)
    def test_enrich_keeps_repo_when_api_fails(self, _get, _token):
        repo = trending.enrich({"name": "o/r", "description": None})
        self.assertEqual(repo["name"], "o/r")
        self.assertIsNone(repo["stars"])
        self.assertIsNone(repo["image"])
        self.assertEqual(repo["readme"], "")


class GithubTokenTest(unittest.TestCase):
    @mock.patch.dict("os.environ", {}, clear=True)
    @mock.patch("subprocess.run")
    def test_gh_runs_once_per_fetch(self, run):
        trending.github_token.cache_clear()
        self.addCleanup(trending.github_token.cache_clear)
        run.return_value.stdout = "token\n"
        for _ in range(3):
            trending.github_headers()
        self.assertEqual(run.call_count, 1)


# A row of github.com/trending as served, with the markup the parser must skip over.
TRENDING_ROW = """<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{{&quot;event_type&quot;:&quot;explore.click&quot;}}" href="/{name}"
       data-view-component="true" class="Link"><svg aria-hidden="true" class="octicon">
    <path d="M2 2.5A2.5"></path></svg><span class="text-normal">{owner} /</span> {repo}</a>
  </h2>
  <span class="d-inline-block float-sm-right">{gained}</span>
</article>"""


def trending_row(name, gained):
    owner, repo = name.split("/")
    return TRENDING_ROW.format(name=name, owner=owner, repo=repo, gained=gained)


class GithubTrendingTest(unittest.TestCase):
    def test_reads_names_ranks_and_stars_gained(self):
        page = "<html>" + "".join(trending_row(name, gained) for name, gained in (
            ("a/one", "1,234 stars today"), ("b/two", "1 star today"), ("c/three", "")))
        with mock.patch("trending.get", return_value=page):
            self.assertEqual(trending.github_trending(), [
                {"name": "a/one", "source": "github", "rank": 1, "gained": 1234},
                {"name": "b/two", "source": "github", "rank": 2, "gained": 1},
                {"name": "c/three", "source": "github", "rank": 3, "gained": None},
            ])

    def test_ranks_skip_rows_without_a_repository(self):
        page = '<article class="Box-row"><p>ad</p></article>' + trending_row("a/one", "")
        with mock.patch("trending.get", return_value=page):
            self.assertEqual(trending.github_trending()[0]["rank"], 1)

    def test_fails_when_page_format_changes(self):
        with mock.patch("trending.get", return_value="<html></html>"), \
                self.assertRaises(ValueError):
            trending.github_trending()


class FetchTest(unittest.TestCase):
    @mock.patch("trending.load_seen", return_value={})
    @mock.patch("trending.enrich", side_effect=lambda repo: {**repo, "readme": "生成高清短视频"})
    @mock.patch("trending.github_trending", return_value=[])
    @mock.patch("trending.trendshift", return_value=[{"name": "o/r", "source": "trendshift"}])
    def test_fetch_keeps_non_ascii_readable(self, *_):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            trending.fetch()
        self.assertIn("生成高清短视频", out.getvalue())


if __name__ == "__main__":
    unittest.main()
