"""Integration tests: full user/system journeys across apps.
External HTTP (AI providers, feeds) is mocked at the boundary; everything
inside the project - fetcher, router, composer, verification, pages, API -
runs for real."""
from types import SimpleNamespace
from unittest import mock
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from sources.models import NewsSource
from news.models import NewsArticle
from news import fetcher
from airouter import providers_text, providers_image
from verification.models import VerificationReport, ClaimSubmission

def entry(title, url, summary=""):
    return SimpleNamespace(link=url, title=title, summary=summary, description="",
                           author="", media_content=[], links=[],
                           published_parsed=None, updated_parsed=None,
                           published="", updated="")

def feed_of(entries):
    return SimpleNamespace(entries=entries, status=200, bozo=False,
                           bozo_exception=None, etag=None, modified=None)

@override_settings(AUTO_COVERS_PER_SOURCE=3)
class FullPipelineJourney(TestCase):
    """RSS -> article -> AI brief -> auto-verify -> cover -> pages -> API."""
    def setUp(self):
        self.src = NewsSource.objects.create(name="JourneyWire", slug="journeywire",
                                             website="https://example.com",
                                             feed_url="https://example.com/feed.xml")
        feed = feed_of([entry("ISRO Announces New Lunar Mission For 2027",
                              "https://example.com/j1",
                              "The space agency confirmed the mission timeline.")])
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed), \
             mock.patch.object(providers_text.requests, "post", side_effect=Exception("down")), \
             mock.patch.object(providers_text.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(providers_image.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(providers_image.requests, "post", side_effect=Exception("down")):
            self.result = fetcher.fetch_source(self.src)
        self.art = NewsArticle.objects.get(source_url="https://example.com/j1")

    def test_pipeline_created_verified_article_with_brief(self):
        self.assertEqual(self.result["created"], 1)
        self.assertTrue(len(self.art.ai_brief) > 40)                       # brief generated (local fallback)
        self.assertTrue(VerificationReport.objects.filter(article=self.art).exists())  # auto-verified

    def test_cover_endpoint_serves_image(self):
        r = Client().get(f"/cover/{self.art.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(r["Content-Type"], ("image/svg+xml", "image/jpeg"))  # SVG fallback when AI is down

    def test_reader_journey_home_detail_search(self):
        c = Client()
        home = c.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Lunar Mission", home.content)
        detail = c.get(f"/news/{self.art.slug}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(self.art.ai_brief[:30].encode(), detail.content)
        search = c.get("/search/?q=Lunar")
        self.assertEqual(search.status_code, 200)
        self.assertIn(b"Lunar Mission", search.content)

    def test_api_contract_for_live_js(self):
        data = Client().get("/api/articles/").json()
        row = data["results"][0]
        for field in ("ai_brief", "is_unconfirmed", "source_note", "source_name", "source_url"):
            self.assertIn(field, row)
        self.assertNotIn("summary", row)

class ClaimJourney(TestCase):
    def test_claim_checked_but_never_becomes_news(self):
        before = NewsArticle.objects.count()
        r = Client().post("/check-claim/", {"claim_text": "A viral message claims the moon landing was filmed in a studio in 1969.",
                                            "platform": "whatsapp", "source_url": ""})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(ClaimSubmission.objects.exists())
        self.assertEqual(NewsArticle.objects.count(), before)

class CorrectionJourney(TestCase):
    def test_public_correction_stays_pending(self):
        r = Client().post("/api/corrections/", {"name": "Reader", "email": "r@e.in",
                          "description": "Date galat hai", "status": "accepted"},
                          content_type="application/json")
        self.assertEqual(r.status_code, 201)
        from feedback_app.models import CorrectionRequest
        self.assertEqual(CorrectionRequest.objects.get().status, "pending")

class StaffJourney(TestCase):
    def test_staff_can_open_ai_dashboard_and_admin(self):
        U = get_user_model()
        U.objects.create_superuser("journeyadmin", password="x")
        c = Client(); c.force_login(U.objects.get(username="journeyadmin"))
        self.assertEqual(c.get("/ai/").status_code, 200)
        self.assertEqual(c.get("/admin/").status_code, 200)
        anon = Client()
        self.assertIn(anon.get("/ai/").status_code, (301, 302))  # redirected to login
