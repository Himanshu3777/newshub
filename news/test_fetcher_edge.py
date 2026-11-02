"""Fetcher edge cases: empty/malformed feeds, HTTP errors, retry exhaustion,
ETag storage, inactive sources, hostile feed content, oversized content."""
from types import SimpleNamespace
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from sources.models import NewsSource
from news.models import NewsArticle
from news import fetcher
from airouter import providers_text, providers_image

def entry(title, url, summary="", author=""):
    return SimpleNamespace(link=url, title=title, summary=summary, description="",
                           author=author, media_content=[], links=[],
                           published_parsed=None, updated_parsed=None,
                           published="", updated="")
def parsed(entries, status=200, bozo=False, etag=None):
    return SimpleNamespace(entries=entries, status=status, bozo=bozo,
                           bozo_exception=ValueError("x") if bozo else None,
                           etag=etag, modified=None)

class FetcherEdgeTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="EdgeWire", slug="edgewire",
                                             website="https://example.com",
                                             feed_url="https://example.com/feed.xml")
        # External AI HTTP fails fast in tests: briefs fall back to the local
        # composer and covers to SVG - the full pipeline still runs for real.
        for patcher in (
            mock.patch.object(providers_text.requests, "post", side_effect=Exception("down")),
            mock.patch.object(providers_text.requests, "get", side_effect=Exception("down")),
            mock.patch.object(providers_image.requests, "get", side_effect=Exception("down")),
            mock.patch.object(providers_image.requests, "post", side_effect=Exception("down")),
        ):
            patcher.start(); self.addCleanup(patcher.stop)
    def run_fetch(self, feed, **kw):
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed) as mp, \
             mock.patch.object(fetcher.time, "sleep", return_value=None):
            res = fetcher.fetch_source(self.src)
        return res, mp

    def test_empty_feed_is_success_with_zero(self):
        res, _ = self.run_fetch(parsed([]))
        self.assertEqual(res["created"], 0); self.assertEqual(res["status"], "success")

    def test_malformed_items_skipped_valid_kept(self):
        feed = parsed([entry("", "https://example.com/no-title"),
                       entry("No URL Story Here", ""),
                       entry("Perfectly Valid Story", "https://example.com/ok")])
        res, _ = self.run_fetch(feed)
        self.assertEqual(res["created"], 1)
        self.assertTrue(NewsArticle.objects.filter(source_url="https://example.com/ok").exists())

    def test_missing_date_defaults_to_now(self):
        res, _ = self.run_fetch(parsed([entry("Dateless Story From Wire", "https://example.com/d1")]))
        art = NewsArticle.objects.get(source_url="https://example.com/d1")
        self.assertIsNotNone(art.published_at)
        self.assertLess(abs((timezone.now() - art.published_at).total_seconds()), 3600)

    def test_http_404_feed_fails_after_retry(self):
        res, mp = self.run_fetch(parsed([], status=404, bozo=True))
        self.assertEqual(res["status"], "failed")
        self.assertEqual(mp.call_count, 2)  # initial attempt + exactly one retry

    def test_timeout_retry_exhaustion(self):
        with mock.patch.object(fetcher.feedparser, "parse", side_effect=Exception("timed out")) as mp, \
             mock.patch.object(fetcher.time, "sleep", return_value=None):
            res = fetcher.fetch_source(self.src)
        self.assertEqual(res["status"], "failed")
        self.assertEqual(mp.call_count, 2)

    def test_etag_stored_for_next_conditional_fetch(self):
        self.run_fetch(parsed([entry("Tagged Story For Etag", "https://example.com/e1")], etag="v123"))
        self.src.refresh_from_db()
        self.assertEqual(self.src.feed_etag, "v123")

    def test_inactive_source_never_fetched(self):
        NewsSource.objects.create(name="OffWire", slug="offwire", website="https://example.com",
                                  feed_url="https://example.com/off", is_active=False)
        with mock.patch.object(fetcher, "fetch_source") as spy:
            fetcher.fetch_all_sources()
        fetched_slugs = [c.args[0].slug for c in spy.call_args_list]
        self.assertNotIn("offwire", fetched_slugs)

    def test_malicious_html_stripped_from_title(self):
        feed = parsed([entry("<script>alert(1)</script> Markets Rally Today", "https://example.com/h1")])
        self.run_fetch(feed)
        art = NewsArticle.objects.get(source_url="https://example.com/h1")
        self.assertNotIn("<script>", art.title); self.assertNotIn("<", art.title)

    def test_oversized_summary_truncated(self):
        feed = parsed([entry("Big Content Story Here", "https://example.com/big", summary="word " * 3000)])
        self.run_fetch(feed)
        art = NewsArticle.objects.get(source_url="https://example.com/big")
        self.assertLessEqual(len(art.summary), 1200)

    def test_author_email_masked_rest_intact(self):
        feed = parsed([entry("Author Masking Story", "https://example.com/am",
                             author="editor@newsdaily.com (City Desk)")])
        self.run_fetch(feed)
        art = NewsArticle.objects.get(source_url="https://example.com/am")
        self.assertNotIn("editor@newsdaily.com", art.author)
        self.assertIn("City Desk", art.author)
