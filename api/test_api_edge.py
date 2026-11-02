"""API + serializer edge cases: 404s, filters, malformed params, exact
public field surface, unknown fields, invalid input handling."""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory
from api.serializers import ArticleSerializer, FeedbackSerializer

PUBLIC_FIELDS = {"id", "title", "slug", "ai_brief", "is_unconfirmed", "source_note",
                 "source", "source_name", "source_url", "author", "category",
                 "category_name", "tags_list", "image_url", "language", "published_at",
                 "verification_status", "confidence_score", "has_sensitive_content",
                 "view_count", "is_breaking"}

class ApiEdgeTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="ApiWire", slug="apiwire", license_status="permitted",
                                             website="https://e.com", feed_url="https://e.com/f")
        self.cat = NewsCategory.objects.create(name="Sports", slug="sports-edge")
        self.a1 = NewsArticle.objects.create(title="Edge API Story One", source=self.src,
                                             source_url="https://e.com/1", category=self.cat,
                                             published_at=timezone.now(), ai_brief="Brief one text.")
        self.a2 = NewsArticle.objects.create(title="Edge API Story Two", source=self.src,
                                             source_url="https://e.com/2",
                                             published_at=timezone.now(), ai_brief="Brief two text.")
        self.c = APIClient()

    def test_detail_404_for_missing_article(self):
        self.assertEqual(self.c.get("/api/articles/999999/").status_code, 404)

    def test_public_field_surface_is_exact(self):
        data = self.c.get("/api/articles/").json()["results"][0]
        self.assertEqual(set(data.keys()), PUBLIC_FIELDS)
        self.assertNotIn("summary", data)       # internal RSS text stays internal
        self.assertNotIn("cover_jpeg", data)

    def test_category_filter(self):
        data = self.c.get("/api/articles/?category__slug=sports-edge").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["title"], "Edge API Story One")

    def test_invalid_page_size_does_not_500(self):
        r = self.c.get("/api/articles/?page_size=abc")
        self.assertIn(r.status_code, (200, 400))

    def test_serializer_rejects_internal_field_writes(self):
        s = FeedbackSerializer(data={"name": "A", "email": "a@b.co", "category": "general",
                                     "subject": "Hi", "message": "Hello there world",
                                     "is_resolved": True})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertFalse(s.save().is_resolved)

    def test_serializer_invalid_email_rejected(self):
        s = FeedbackSerializer(data={"name": "A", "email": "not-an-email", "category": "general",
                                     "subject": "Hi", "message": "Hello there world"})
        self.assertFalse(s.is_valid())
        self.assertIn("email", s.errors)

    def test_unknown_extra_field_ignored_not_500(self):
        r = self.c.post("/api/feedback/", {"name": "A", "email": "a@b.co", "category": "general",
                                           "subject": "Hi", "message": "Hello there world",
                                           "is_admin": True, "evil_field": "x"}, format="json")
        self.assertEqual(r.status_code, 201)
