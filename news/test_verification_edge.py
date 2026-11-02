"""Verification engine edge cases: Fact Check API failures, scoring rules,
quarantine + restoration, duplicate verification, source-note lifecycle."""
from unittest import mock
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory
from verification import engine, services
from verification.models import VerificationReport
from verification.providers import EvidenceItem

class StubProvider:
    """Provider-layer test double: returns canned (items, status) per search."""
    legacy = False
    def __init__(self, name, result):
        self.name = name; self._result = result
    def is_enabled(self): return True
    def search(self, query): return self._result

def fc_result(ratings):
    """Canned provider result mimicking FactCheckProvider output."""
    items = [EvidenceItem(title="FC", url="https://fc.in/1", publisher="FC",
                          snippet="", rating=r, kind="factcheck") for r in ratings]
    return (items, "ok")

def mk(title, source, status="unverified", **kw):
    return NewsArticle.objects.create(title=title, summary=kw.pop("summary", "s"),
                                      source=source, published_at=timezone.now(),
                                      verification_status=status, **kw)

class FactCheckApiTests(TestCase):
    def test_no_key_returns_empty_safely(self):
        out, status = services.google_factcheck("any claim")
        self.assertEqual(out, []); self.assertEqual(status, "no_api_key")

    @override_settings(GOOGLE_FACTCHECK_API_KEY="test-key")
    def test_api_429_handled(self):
        resp = mock.Mock(status_code=429)
        with mock.patch.object(services.requests, "get", return_value=resp):
            out, status = services.google_factcheck("claim")
        self.assertEqual(out, []); self.assertEqual(status, "api_429")

    @override_settings(GOOGLE_FACTCHECK_API_KEY="test-key")
    def test_api_timeout_handled(self):
        with mock.patch.object(services.requests, "get", side_effect=Exception("timed out")):
            out, status = services.google_factcheck("claim")
        self.assertEqual(out, []); self.assertTrue(status.startswith("error"))

    @override_settings(GOOGLE_FACTCHECK_API_KEY="test-key")
    def test_malformed_json_handled(self):
        resp = mock.Mock(status_code=200); resp.json.side_effect = ValueError("bad json")
        with mock.patch.object(services.requests, "get", return_value=resp):
            out, status = services.google_factcheck("claim")
        self.assertEqual(out, []); self.assertTrue(status.startswith("error"))

class ScoringRuleTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="ScoreWire", slug="scorewire",
                                             website="https://e.com", feed_url="https://e.com/f")
        self.art = mk("Scoring Test Headline", self.src, source_url="https://e.com/s1")
    def test_factcheck_false_wins(self):
        status, conf, _ = services.score_verification(self.art, [{"rating": "False"}], 0)
        self.assertEqual(status, "false"); self.assertEqual(conf, 85.0)
    def test_repetition_alone_never_verified(self):
        status, conf, _ = services.score_verification(self.art, [], related_count=5)
        self.assertEqual(status, "partially_verified")  # coverage supports, never proves
    def test_single_source_is_unverified(self):
        status, _, _ = services.score_verification(self.art, [], related_count=1)
        self.assertEqual(status, "unverified")
    def test_no_evidence_needs_review(self):
        status, _, _ = services.score_verification(self.art, [], related_count=0)
        self.assertEqual(status, "needs_review")

class QuarantineLifecycleTests(TestCase):
    def setUp(self):
        # license_status="permitted": these tests exercise *verification*
        # quarantine visibility, so licensing must not be the hidden variable.
        self.src = NewsSource.objects.create(name="QWire", slug="qwire", license_status="permitted",
                                             website="https://e.com", feed_url="https://e.com/f")
        self.other = NewsSource.objects.create(name="QWire2", slug="qwire2", license_status="permitted",
                                               website="https://e2.com", feed_url="https://e2.com/f")
        self.cat = NewsCategory.objects.create(name="India", slug="india-q")

    def test_false_verdict_quarantines_everywhere(self):
        art = mk("Miracle Cure Cures All Diseases Instantly", self.src,
                 source_url="https://e.com/fake", category=self.cat)
        with mock.patch.object(engine, "get_search_providers",
                               return_value=[StubProvider("factcheck", fc_result(["False"]))]):
            engine.verify_article(art)
        art.refresh_from_db()
        self.assertEqual(art.verification_status, "false")
        c = Client()
        self.assertNotIn(b"Miracle Cure", c.get("/").content)
        self.assertNotIn(b"Miracle Cure", c.get("/search/?q=Miracle").content)
        data = c.get("/api/articles/").json()
        self.assertEqual(data["count"], 0)
        detail = c.get(f"/news/{art.slug}/")
        self.assertIn(b"flagged and removed", detail.content)  # warning page only

    def test_restoration_from_quarantine(self):
        art = mk("Restorable Story About City Metro", self.src, status="false",
                 source_url="https://e.com/restore", category=self.cat)
        self.assertNotIn(b"Restorable Story", Client().get("/").content)
        art.verification_status = "unverified"; art.save()  # staff restores after review
        self.assertIn(b"Restorable Story", Client().get("/").content)

    def test_duplicate_verification_keeps_audit_trail(self):
        art = mk("Duplicate Verification Story", self.src, source_url="https://e.com/dup")
        with mock.patch.object(engine, "get_search_providers", return_value=[StubProvider("factcheck", ([], "no_api_key"))]):
            engine.verify_article(art)
            n1 = VerificationReport.objects.filter(article=art).count()
            engine.verify_article(art)
            n2 = VerificationReport.objects.filter(article=art).count()
        self.assertGreaterEqual(n1, 1); self.assertGreater(n2, n1)  # history kept, no crash
        art.refresh_from_db()
        self.assertIn(art.verification_status, ("unverified", "needs_review", "partially_verified"))

    def test_confirmation_removes_source_note(self):
        art = mk("Comet Visible Over India Tonight", self.src, source_url="https://e.com/c1",
                 is_unconfirmed=True, source_note="According to a viral post, but this has not been confirmed")
        mk("Comet Visible Over India Tonight", self.other, source_url="https://e2.com/c1")
        with mock.patch.object(engine, "get_search_providers", return_value=[StubProvider("factcheck", ([], "no_api_key"))]):
            engine.verify_article(art)
        art.refresh_from_db()
        self.assertFalse(art.is_unconfirmed); self.assertEqual(art.source_note, "")

    def test_no_confirmation_keeps_source_note(self):
        art = mk("Unique Unconfirmed Comet Claim XYZ", self.src, source_url="https://e.com/c2",
                 is_unconfirmed=True, source_note="Viral claim, not confirmed")
        with mock.patch.object(engine, "get_search_providers", return_value=[StubProvider("factcheck", ([], "no_api_key"))]):
            engine.verify_article(art)
        art.refresh_from_db()
        self.assertTrue(art.is_unconfirmed); self.assertTrue(art.source_note)
