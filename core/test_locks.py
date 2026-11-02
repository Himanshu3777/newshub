"""SystemLock behaviour beyond the basics: exception safety."""
from unittest import mock
from django.test import TestCase
from core.models import SystemLock
from core.locks import acquire_lock, release_lock
from news import fetcher
from sources.models import NewsSource

class LockEdgeTests(TestCase):
    def test_exception_inside_fetch_releases_lock(self):
        NewsSource.objects.create(name="LockWire", slug="lockwire", website="https://e.com",
                                  feed_url="https://e.com/f")
        with mock.patch.object(fetcher, "fetch_source", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                fetcher.fetch_all_sources()
        self.assertFalse(SystemLock.objects.filter(name="rss_fetch").exists())

    def test_second_acquire_blocked_until_release(self):
        self.assertTrue(acquire_lock("rss_fetch"))
        self.assertFalse(acquire_lock("rss_fetch"))
        release_lock("rss_fetch")
        self.assertTrue(acquire_lock("rss_fetch"))
        release_lock("rss_fetch")
