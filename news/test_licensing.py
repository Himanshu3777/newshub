"""Public visibility during the testing phase (owner decision 2026-11-03).

The site is in a ~1-month testing phase: everything stored in the database
is shown publicly and auto-publishes as scans land, whatever a source's
license_status says. The license_status field and the NewsSource
.is_publicly_displayable property stay in place so the permitted-only gate
can be switched back on when testing ends. The quarantine rule is NOT part
of this change: false/misleading/disputed stories stay hidden and their
direct links keep showing the warning page, never the story.
"""
from django.test import TestCase, Client
from django.utils import timezone

from sources.models import NewsSource
from news.models import NewsArticle


def mk_source(name, slug, license_status="unknown"):
    return NewsSource.objects.create(
        name=name, slug=slug, website="https://e.com",
        feed_url="https://e.com/f", license_status=license_status)


def mk_article(title, source, url, status="unverified"):
    return NewsArticle.objects.create(
        title=title, summary="s", source=source, source_url=url,
        published_at=timezone.now(), verification_status=status)


class TestingPhaseVisibilityTests(TestCase):
    def setUp(self):
        self.unknown_src = mk_source("UnknownWire", "unknownwire")
        self.permitted_src = mk_source("PermittedWire", "permittedwire", "permitted")
        self.restricted_src = mk_source("RestrictedWire", "restrictedwire", "restricted")
        self.unknown_art = mk_article("Zebra Unknown License Story", self.unknown_src, "https://e.com/u1")
        self.permitted_art = mk_article("Zebra Permitted License Story", self.permitted_src, "https://e.com/p1")
        self.restricted_art = mk_article("Zebra Restricted License Story", self.restricted_src, "https://e.com/r1")
        self.client = Client()

    def test_all_license_states_visible_on_home_and_listing(self):
        home = self.client.get("/").content
        self.assertIn(b"Zebra Unknown License Story", home)
        self.assertIn(b"Zebra Restricted License Story", home)
        listing = self.client.get("/news/").content
        self.assertIn(b"Zebra Unknown License Story", listing)
        search = self.client.get("/search/?q=Zebra").content
        self.assertIn(b"Zebra Unknown License Story", search)

    def test_permitted_license_visible_on_home(self):
        self.assertIn(b"Zebra Permitted License Story", self.client.get("/").content)

    def test_all_license_states_visible_in_public_api(self):
        data = self.client.get("/api/articles/").json()
        titles = [r["title"] for r in data["results"]]
        self.assertIn("Zebra Unknown License Story", titles)
        self.assertIn("Zebra Restricted License Story", titles)
        self.assertIn("Zebra Permitted License Story", titles)

    def test_api_search_includes_all_sources(self):
        data = self.client.get("/api/search/?q=Zebra").json()
        titles = [r["title"] for r in data]
        self.assertIn("Zebra Unknown License Story", titles)
        self.assertIn("Zebra Permitted License Story", titles)

    def test_api_detail_200_for_all_license_states(self):
        self.assertEqual(self.client.get(f"/api/articles/{self.unknown_art.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/articles/{self.restricted_art.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/articles/{self.permitted_art.id}/").status_code, 200)

    def test_detail_page_shows_story_for_any_license_state(self):
        resp = self.client.get(f"/news/{self.unknown_art.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Zebra Unknown License Story", resp.content)
        self.assertNotIn(b"flagged and removed", resp.content)

    def test_quarantined_story_still_hidden_with_warning_page(self):
        bad = mk_article("Zebra Fabricated Story", self.permitted_src,
                         "https://e.com/bad1", status="false")
        home = self.client.get("/").content
        self.assertNotIn(b"Zebra Fabricated Story", home)
        resp = self.client.get(f"/news/{bad.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"flagged and removed", resp.content)

    def test_source_displayable_property_unchanged(self):
        # The field/property remain for the post-testing gate; only the
        # public querysets ignore them during the testing phase.
        self.assertFalse(self.unknown_src.is_publicly_displayable)
        self.assertTrue(self.permitted_src.is_publicly_displayable)
        self.assertFalse(self.restricted_src.is_publicly_displayable)
