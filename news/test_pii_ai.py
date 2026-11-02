"""PII pipeline tests: RSS -> masking -> storage -> AI provider payload.
The raw PII must exist at NO stage beyond the incoming feed itself."""
import urllib.parse
from types import SimpleNamespace
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from moderation.services import mask_pii_in_text
from sources.models import NewsSource
from news.models import NewsArticle
from news import fetcher, ai_content
from airouter import providers_text

RAW_PHONE = "9876543210"; RAW_EMAIL = "rahul.sharma@example.com"; RAW_PAN = "ABCDE1234F"

class MaskInTextTests(TestCase):
    def test_all_pii_types_masked_text_intact(self):
        text = f"Helpline {RAW_PHONE} or mail {RAW_EMAIL}, PAN {RAW_PAN} required. Office opens Monday."
        out = mask_pii_in_text(text)
        for raw in (RAW_PHONE, RAW_EMAIL, RAW_PAN):
            self.assertNotIn(raw, out)
        self.assertIn("Helpline", out); self.assertIn("Office opens Monday", out)

    def test_aadhaar_like_masked(self):
        out = mask_pii_in_text("Carry ID 1234 5678 9012 for entry")
        self.assertNotIn("1234 5678 9012", out); self.assertIn("for entry", out)

class PiiToAiTests(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="PiiWire", slug="piiwire",
                                             website="https://e.com", feed_url="https://e.com/f")
    def test_raw_pii_never_sent_to_ai_provider(self):
        # Article created directly (admin-style) WITH raw PII still present -
        # the brief generator is the last wall before external AI calls.
        art = NewsArticle.objects.create(
            title="Citizen Helpline Story", source=self.src, source_url="https://e.com/pii",
            summary=f"Citizens may call {RAW_PHONE} or write to {RAW_EMAIL} for assistance.",
            published_at=timezone.now())
        captured = {}
        ok = mock.Mock(status_code=200, text="A perfectly original brief about the citizen helpline that is long enough to pass validation checks.")
        def fake_get(url, **kw):
            captured["url"] = url
            return ok
        with mock.patch.object(providers_text.requests, "get", side_effect=fake_get), \
             mock.patch.object(providers_text.requests, "post", side_effect=Exception("down")):
            brief, provider = ai_content.generate_brief(art)
        sent = urllib.parse.unquote(captured.get("url", ""))
        self.assertNotIn(RAW_PHONE, sent); self.assertNotIn(RAW_EMAIL, sent)
        self.assertNotIn(RAW_PHONE, brief); self.assertNotIn(RAW_EMAIL, brief)

    def test_fetcher_to_brief_pipeline_clean(self):
        e = SimpleNamespace(link="https://e.com/pipe", title="Pipeline Helpline Story",
                            summary=f"Call {RAW_PHONE} for help.", description="", author="",
                            media_content=[], links=[], published_parsed=None,
                            updated_parsed=None, published="", updated="")
        feed = SimpleNamespace(entries=[e], status=200, bozo=False, bozo_exception=None, etag=None, modified=None)
        from airouter import providers_image
        with mock.patch.object(fetcher.feedparser, "parse", return_value=feed), \
             mock.patch.object(providers_text.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(providers_text.requests, "post", side_effect=Exception("down")), \
             mock.patch.object(providers_image.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(providers_image.requests, "post", side_effect=Exception("down")):
            fetcher.fetch_source(self.src)
        art = NewsArticle.objects.get(source_url="https://e.com/pipe")
        self.assertNotIn(RAW_PHONE, art.summary)
        self.assertNotIn(RAW_PHONE, art.ai_brief)
