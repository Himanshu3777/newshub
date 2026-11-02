"""Pluggable SearchProvider architecture: registry rules, the legacy CSE
provider's enable-gate and result mapping, the multi-signal scoring rule,
and engine evidence collection across multiple providers (no network)."""
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from sources.models import NewsSource
from news.models import NewsArticle
from verification import engine, providers, services
from verification.models import VerificationReport
from verification.providers import (
    EvidenceItem, FactCheckProvider, GoogleCSEProvider, get_search_providers,
)


def names(provider_list):
    return [p.name for p in provider_list]


class ProviderRegistryTests(TestCase):
    def test_factcheck_enabled_by_default(self):
        self.assertEqual(names(get_search_providers()), ["factcheck"])

    def test_cse_absent_by_default(self):
        self.assertNotIn("google_cse", names(get_search_providers()))

    @override_settings(SEARCH_PROVIDERS=["factcheck", "google_cse"],
                       SEARCH_GOOGLE_CSE_ENABLED=False,
                       GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx1")
    def test_cse_disabled_when_flag_off_even_with_keys(self):
        self.assertEqual(names(get_search_providers()), ["factcheck"])

    @override_settings(SEARCH_PROVIDERS=["factcheck", "google_cse"],
                       SEARCH_GOOGLE_CSE_ENABLED=True,
                       GOOGLE_CSE_API_KEY="", GOOGLE_CSE_ID="")
    def test_cse_disabled_without_keys(self):
        self.assertEqual(names(get_search_providers()), ["factcheck"])

    @override_settings(SEARCH_PROVIDERS=["factcheck", "google_cse"],
                       SEARCH_GOOGLE_CSE_ENABLED=True,
                       GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx1")
    def test_cse_enabled_when_flag_on_and_keys_set(self):
        found = get_search_providers()
        self.assertEqual(names(found), ["factcheck", "google_cse"])
        cse = [p for p in found if p.name == "google_cse"][0]
        self.assertTrue(cse.legacy)  # CSE is legacy-only, never a dependency

    @override_settings(SEARCH_PROVIDERS=["bogus", "factcheck"])
    def test_unknown_provider_names_ignored(self):
        self.assertEqual(names(get_search_providers()), ["factcheck"])


class FactCheckProviderTests(TestCase):
    def test_wraps_services_and_maps_items(self):
        raw = ([{"title": "FC title", "url": "https://fc.in/1", "publisher": "FC",
                 "rating": "False", "snippet": "claim text"}], "ok")
        with mock.patch.object(services, "google_factcheck", return_value=raw):
            items, status = FactCheckProvider().search("a claim")
        self.assertEqual(status, "ok")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, "factcheck")
        self.assertEqual(items[0].rating, "False")
        self.assertEqual(items[0].publisher, "FC")


@override_settings(SEARCH_GOOGLE_CSE_ENABLED=True, GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx1")
class GoogleCSEProviderTests(TestCase):
    def test_search_maps_items_as_neutral_evidence(self):
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"items": [
            {"title": "Result", "link": "https://web.in/1",
             "displayLink": "web.in", "snippet": "some snippet"}]}
        with mock.patch.object(providers.requests, "get", return_value=resp):
            items, status = GoogleCSEProvider().search("a claim")
        self.assertEqual(status, "ok")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, "neutral")
        self.assertEqual(items[0].rating, "")  # web results carry no rating
        self.assertEqual(items[0].url, "https://web.in/1")

    def test_search_api_error_status(self):
        resp = mock.Mock(status_code=403)
        with mock.patch.object(providers.requests, "get", return_value=resp):
            items, status = GoogleCSEProvider().search("a claim")
        self.assertEqual(items, []); self.assertEqual(status, "api_403")

    @override_settings(SEARCH_GOOGLE_CSE_ENABLED=False)
    def test_search_reports_disabled_when_flag_off(self):
        items, status = GoogleCSEProvider().search("a claim")
        self.assertEqual(items, []); self.assertEqual(status, "disabled")


class MultiSignalScoringTests(TestCase):
    """Fact-check alone is one signal - never a truth engine."""
    def setUp(self):
        self.src = NewsSource.objects.create(name="SigWire", slug="sigwire",
                                             website="https://e.com", feed_url="https://e.com/f")
        self.art = NewsArticle.objects.create(
            title="Multi Signal Scoring Story", summary="s", source=self.src,
            published_at=timezone.now(), source_url="https://e.com/ms1")

    def test_factcheck_true_alone_is_only_partial(self):
        status, conf, summary = services.score_verification(
            self.art, [{"rating": "True"}], related_count=0)
        self.assertEqual(status, "partially_verified")
        self.assertEqual(conf, 70.0)
        self.assertIn("corroboration", summary)

    def test_factcheck_true_plus_corroboration_verifies(self):
        status, conf, _ = services.score_verification(
            self.art, [{"rating": "True"}], related_count=1)
        self.assertEqual(status, "verified")
        self.assertEqual(conf, 90.0)

    def test_factcheck_false_still_wins_without_corroboration(self):
        status, conf, _ = services.score_verification(
            self.art, [{"rating": "False"}], related_count=0)
        self.assertEqual(status, "false")
        self.assertEqual(conf, 85.0)


class FakeProvider:
    legacy = False
    def __init__(self, name, result):
        self.name = name; self._result = result
    def is_enabled(self): return True
    def search(self, query): return self._result


class EngineMultiProviderTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="EngWire", slug="engwire",
                                             website="https://e.com", feed_url="https://e.com/f")
        self.other = NewsSource.objects.create(name="EngWire2", slug="engwire2",
                                               website="https://e2.com", feed_url="https://e2.com/f")

    def test_engine_collects_evidence_from_all_providers(self):
        art = NewsArticle.objects.create(
            title="Comet Visible Over India Tonight", summary="s", source=self.src,
            published_at=timezone.now(), source_url="https://e.com/c1")
        # Independent coverage from another publisher (corroboration signal).
        NewsArticle.objects.create(
            title="Comet Visible Over India Tonight", summary="s", source=self.other,
            published_at=timezone.now(), source_url="https://e2.com/c1")
        fc = FakeProvider("factcheck", ([EvidenceItem(
            title="FC", url="https://fc.in/1", publisher="FC",
            rating="True", kind="factcheck")], "ok"))
        cse = FakeProvider("google_cse", ([EvidenceItem(
            title="Web result", url="https://web.in/1", publisher="web.in",
            kind="neutral")], "ok"))
        with mock.patch.object(engine, "get_search_providers", return_value=[fc, cse]):
            engine.verify_article(art)
        report = VerificationReport.objects.filter(article=art).first()
        self.assertIsNotNone(report)
        kinds = set(report.evidence.values_list("kind", flat=True))
        self.assertEqual(kinds, {"factcheck", "neutral"})
        self.assertIn("[Providers: factcheck=ok, google_cse=ok]", report.summary)
        art.refresh_from_db()
        # Fact-check True + independent corroboration -> verified (multi-signal).
        self.assertEqual(art.verification_status, "verified")
