"""Database-focused tests: unit (constraints/defaults/cascades/transactions)
and integration (cross-table consistency, backup -> restore roundtrip)."""
import io, os, tempfile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory
from core.models import SystemLock
from airouter.models import ProviderUsage
from airouter import quota

def make_source(name="DBWire", slug="dbwire"):
    return NewsSource.objects.create(name=name, slug=slug, website="https://example.com",
                                     feed_url="https://example.com/f")

def make_article(src, url="https://example.com/1", **kw):
    kw.setdefault("title", "Database Test Headline")
    kw.setdefault("published_at", timezone.now())
    return NewsArticle.objects.create(source=src, source_url=url, **kw)

class DatabaseUnitTests(TestCase):
    def test_unique_source_url_enforced(self):
        src = make_source()
        make_article(src)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_article(src)  # same URL again

    def test_unique_source_name_enforced(self):
        make_source()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_source(slug="other-slug")

    def test_cascade_delete_source_removes_articles(self):
        src = make_source()
        make_article(src)
        src.delete()
        self.assertEqual(NewsArticle.objects.count(), 0)

    def test_category_delete_sets_null_not_cascade(self):
        src = make_source()
        cat = NewsCategory.objects.create(name="Tech", slug="tech")
        art = make_article(src, category=cat)
        cat.delete()
        art.refresh_from_db()
        self.assertIsNone(art.category)

    def test_defaults_applied(self):
        art = make_article(make_source())
        self.assertEqual(art.verification_status, "unverified")
        self.assertEqual(art.view_count, 0)
        self.assertFalse(art.is_unconfirmed)

    def test_system_lock_name_unique(self):
        SystemLock.objects.create(name="rss_fetch", acquired_at=timezone.now())
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SystemLock.objects.create(name="rss_fetch", acquired_at=timezone.now())

    def test_provider_usage_unique_per_day(self):
        ProviderUsage.objects.create(date=quota.today_ist(), provider="gemini", kind="text", used=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProviderUsage.objects.create(date=quota.today_ist(), provider="gemini", kind="text", used=2)

    def test_transaction_rollback_leaves_no_partial_rows(self):
        src = make_source()
        try:
            with transaction.atomic():
                make_article(src)
                raise RuntimeError("simulated mid-write failure")
        except RuntimeError:
            pass
        self.assertEqual(NewsArticle.objects.count(), 0)

class DatabaseIntegrationTests(TransactionTestCase):
    def test_backup_restore_roundtrip(self):
        """Data written -> backup_data dump -> wipe -> loaddata -> same data back."""
        src = make_source()
        make_article(src, url="https://example.com/rt1")
        make_article(src, url="https://example.com/rt2")
        with tempfile.TemporaryDirectory() as tmp:
            call_command("backup_data", out=tmp, stdout=io.StringIO())
            files = [f for f in os.listdir(tmp) if f.endswith(".json")]
            self.assertEqual(len(files), 1)
            path = os.path.join(tmp, files[0])
            size = os.path.getsize(path)
            self.assertGreater(size, 200)
            NewsArticle.objects.all().delete()
            NewsSource.objects.all().delete()
            self.assertEqual(NewsArticle.objects.count(), 0)
            call_command("loaddata", path, verbosity=0)
            self.assertEqual(NewsArticle.objects.count(), 2)
            self.assertEqual(NewsSource.objects.count(), 1)

    def test_validate_data_reports_counts(self):
        make_article(make_source())
        out = io.StringIO()
        call_command("validate_data", stdout=out)
        self.assertIn("articles=1", out.getvalue())
