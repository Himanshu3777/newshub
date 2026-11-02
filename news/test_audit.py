"""Final-audit tests: RSS ingestion, conditional fetch, retry, locking,
PII-at-storage, API contract, pagination cap, error pages, data validation."""
import io
from types import SimpleNamespace
from unittest import mock
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from sources.models import NewsSource, FetchingLog
from news.models import NewsArticle
from news import fetcher
from core.locks import acquire_lock, release_lock
from core.models import SystemLock

def entry(title, url, summary=""):
    return SimpleNamespace(link=url, title=title, summary=summary, description="",
                           author="", media_content=[], links=[],
                           published_parsed=None, updated_parsed=None,
                           published="", updated="")

def parsed(entries, status=200, bozo=False):
    return SimpleNamespace(entries=entries, status=status, bozo=bozo,
                           bozo_exception=None, etag=None, modified=None)

class FetcherAuditTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="AuditWire", slug="auditwire",
                                             website="https://example.com",
                                             feed_url="https://example.com/feed.xml")

    def test_rss_ingestion_creates_article(self):
        feed = parsed([entry("Monsoon Session Begins In Parliament", "https://example.com/a1", "Debate on bills.")])
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed):
            res = fetcher.fetch_source(self.src)
        self.assertEqual(res["created"], 1)
        self.assertTrue(NewsArticle.objects.filter(source_url="https://example.com/a1").exists())
        self.assertEqual(FetchingLog.objects.get(source=self.src).status, "success")

    def test_second_run_dedupes_by_url(self):
        feed = parsed([entry("Same Story Again Today", "https://example.com/a1")])
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed):
            fetcher.fetch_source(self.src)
            res2 = fetcher.fetch_source(self.src)
        self.assertEqual(res2["created"], 0); self.assertEqual(res2["duplicates"], 1)

    def test_invalid_feed_is_logged_not_crash(self):
        bad = parsed([], bozo=True); bad.bozo_exception = ValueError("bad xml")
        with mock.patch.object(fetcher.feedparser, "parse", return_value=bad), \
             mock.patch.object(fetcher.time, "sleep", return_value=None):
            res = fetcher.fetch_source(self.src)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(FetchingLog.objects.filter(source=self.src, status="failed").exists())

    def test_conditional_fetch_304_skips_work(self):
        feed = parsed([], status=304)
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed):
            res = fetcher.fetch_source(self.src)
        self.assertEqual(res["status"], "not_modified")
        self.assertEqual(NewsArticle.objects.count(), 0)

    def test_retry_recovers_after_first_failure(self):
        good = parsed([entry("Recovered Feed Story Here", "https://example.com/r1")])
        bad = parsed([], bozo=True); bad.bozo_exception = ValueError("boom")
        with mock.patch.object(fetcher.feedparser, "parse", side_effect=[bad, good]), \
             mock.patch.object(fetcher.time, "sleep", return_value=None):
            res = fetcher.fetch_source(self.src)
        self.assertEqual(res["created"], 1)

    def test_pii_masked_before_storage(self):
        feed = parsed([entry("Helpline Story For Citizens", "https://example.com/p1",
                             "Citizens can call 9876543210 for help.")])
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed):
            fetcher.fetch_source(self.src)
        art = NewsArticle.objects.get(source_url="https://example.com/p1")
        self.assertNotIn("9876543210", art.summary)
        self.assertNotIn("9876543210", art.ai_brief)
        # Regression (whole-text masking bug): the rest of the summary must
        # survive masking - only the PII token itself is hidden.
        self.assertIn("Citizens can call", art.summary)
        self.assertIn("for help", art.summary)

    def test_fetch_lock_blocks_second_run(self):
        self.assertTrue(acquire_lock("rss_fetch"))
        try:
            self.assertEqual(fetcher.fetch_all_sources(), [])
        finally:
            release_lock("rss_fetch")
        self.assertFalse(SystemLock.objects.filter(name="rss_fetch").exists())

    def test_stale_lock_can_be_taken_over(self):
        SystemLock.objects.create(name="rss_fetch", acquired_at=timezone.now() - timezone.timedelta(hours=2))
        self.assertTrue(acquire_lock("rss_fetch"))
        release_lock("rss_fetch")

class ApiAuditTests(TestCase):
    def setUp(self):
        src = NewsSource.objects.create(name="ApiWire", slug="apiwire", license_status="permitted",
                                        website="https://example.com", feed_url="https://example.com/f")
        from news.models import NewsCategory
        cat = NewsCategory.objects.create(name="India", slug="india")
        for i in range(5):
            NewsArticle.objects.create(title=f"Story Number {i} For Testing", summary="internal secret summary",
                                       source=src, source_url=f"https://example.com/s{i}", category=cat,
                                       published_at=timezone.now(), ai_brief="Public brief text.")

    def test_api_does_not_expose_internal_summary(self):
        data = Client().get("/api/articles/").json()
        self.assertNotIn("summary", data["results"][0])
        self.assertIn("ai_brief", data["results"][0])

    def test_pagination_page_size_capped_at_100(self):
        data = Client().get("/api/articles/?page_size=500").json()
        self.assertLessEqual(len(data["results"]), 100)

class PagesAndDataAuditTests(TestCase):
    def test_custom_404_page(self):
        r = Client().get("/this-page-does-not-exist/")
        self.assertEqual(r.status_code, 404)
        self.assertIn(b"404", r.content)

    def test_validate_data_command_runs(self):
        out = io.StringIO()
        call_command("validate_data", stdout=out)
        self.assertIn("articles=", out.getvalue())
