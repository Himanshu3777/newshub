"""Chain tests updated for the AI Router architecture (airouter app).
External HTTP is mocked at the provider-module level; the local composer and
the SVG fallback are the guaranteed final layers."""
from django.test import TestCase
from unittest import mock
from airouter import providers_text, providers_image
from news import ai_content, ai_image

class FakeArt:
    id = 5; title = "Test Title Here"; summary = "Some summary text 12345"
    class source: name = "BBC News"
    category = None
    published_at = __import__('datetime').datetime(2026, 11, 1, tzinfo=__import__('datetime').timezone.utc)

class ChainTests(TestCase):
    def test_text_falls_back_to_local_when_all_providers_down(self):
        with mock.patch.object(providers_text.requests, "post", side_effect=Exception("down")), \
             mock.patch.object(providers_text.requests, "get", side_effect=Exception("down")):
            brief, prov = ai_content.generate_brief(FakeArt())
        self.assertEqual(prov, "local")
        self.assertTrue(len(brief) > 40)

    def test_image_chain_all_fail_returns_none(self):
        with mock.patch.object(providers_image.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(providers_image.requests, "post", side_effect=Exception("down")):
            data, prov = ai_image.fetch_ai_cover(FakeArt())
        self.assertIsNone(data); self.assertIsNone(prov)
