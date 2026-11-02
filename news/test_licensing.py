"""Licensing gate: technical feed availability != public-display permission.

Articles from sources whose license_status is not "permitted" must be absent
from the public home/list/search pages and the public API, whatever their
verification status. Marking a source permitted makes them appear; marking
it restricted keeps them hidden.
"""
from django.test import TestCase, Client
from django.utils import timezone

from sources.models import NewsSource
from news.models import NewsArticle


def mk_source(name, slug, license_status="unknown"):
    return NewsSource.objects.create(
        name=name, slug=slug, website="https://e.com",
        feed_url="https://e.com/f", license_status=license_status)


def mk_article(title, source, url):
    return NewsArticle.objects.create(
        title=title, summary="s", source=source, source_url=url,
        published_at=timezone.now(), verification_status="unverified")


class LicensingGateTests(TestCase):
    def setUp(self):
        self.unknown_src = mk_source("UnknownWire", "unknownwire")
        self.permitted_src = mk_source("PermittedWire", "permittedwire", "permitted")
        self.restricted_src = mk_source("RestrictedWire", "restrictedwire", "restricted")
        self.unknown_art = mk_article("Zebra Unknown License Story", self.unknown_src, "https://e.com/u1")
        self.permitted_art = mk_article("Zebra Permitted License Story", self.permitted_src, "https://e.com/p1")
        self.restricted_art = mk_article("Zebra Restricted License Story", self.restricted_src, "https://e.com/r1")
        self.client = Client()

    def test_unknown_license_hidden_from_home_and_listing(self):
        home = self.client.get("/").content
        self.assertNotIn(b"Zebra Unknown License Story", home)
        listing = self.client.get("/news/").content
        self.assertNotIn(b"Zebra Unknown License Story", listing)
        search = self.client.get("/search/?q=Zebra").content
        self.assertNotIn(b"Zebra Unknown License Story", search)

    def test_permitted_license_visible_on_home(self):
        self.assertIn(b"Zebra Permitted License Story", self.client.get("/").content)

    def test_restricted_license_hidden_from_home(self):
        self.assertNotIn(b"Zebra Restricted License Story", self.client.get("/").content)

    def test_unknown_license_hidden_from_public_api(self):
        data = self.client.get("/api/articles/").json()
        titles = [r["title"] for r in data["results"]]
        self.assertNotIn("Zebra Unknown License Story", titles)
        self.assertNotIn("Zebra Restricted License Story", titles)
        self.assertIn("Zebra Permitted License Story", titles)

    def test_api_search_respects_license(self):
        data = self.client.get("/api/search/?q=Zebra").json()
        titles = [r["title"] for r in data]
        self.assertNotIn("Zebra Unknown License Story", titles)
        self.assertIn("Zebra Permitted License Story", titles)

    def test_api_detail_404_for_unlicensed_200_for_permitted(self):
        self.assertEqual(self.client.get(f"/api/articles/{self.unknown_art.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/articles/{self.restricted_art.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/articles/{self.permitted_art.id}/").status_code, 200)

    def test_detail_page_shows_warning_not_story_for_unlicensed(self):
        resp = self.client.get(f"/news/{self.unknown_art.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"flagged and removed", resp.content)

    def test_article_appears_after_source_marked_permitted(self):
        self.assertNotIn(b"Zebra Unknown License Story", self.client.get("/").content)
        self.unknown_src.license_status = "permitted"
        self.unknown_src.save()
        self.assertIn(b"Zebra Unknown License Story", self.client.get("/").content)
        data = self.client.get("/api/articles/").json()
        self.assertIn("Zebra Unknown License Story", [r["title"] for r in data["results"]])

    def test_source_displayable_property(self):
        self.assertFalse(self.unknown_src.is_publicly_displayable)
        self.assertTrue(self.permitted_src.is_publicly_displayable)
        self.assertFalse(self.restricted_src.is_publicly_displayable)
