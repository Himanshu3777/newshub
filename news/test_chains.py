from django.test import TestCase, override_settings
from unittest import mock
from news import ai_content, ai_image

class FakeArt:
    id=5; title="Test Title Here"; summary="Some summary text 12345"
    class source: name="BBC News"
    category=None
    published_at=__import__('datetime').datetime(2026,11,1,tzinfo=__import__('datetime').timezone.utc)

class ChainTests(TestCase):
    def test_text_falls_back_to_local_without_keys(self):
        brief, prov = ai_content.generate_brief(FakeArt())
        self.assertEqual(prov, "local"); self.assertTrue(len(brief) > 40)

    @override_settings(GEMINI_API_KEY="x", MISTRAL_API_KEY="y")
    def test_text_chain_order_gemini_then_mistral(self):
        ok = mock.Mock(status_code=200); ok.json.return_value={"choices":[{"message":{"content":"A perfectly original brief sentence that is long enough to pass the cleaner check."}}]}
        with mock.patch.object(ai_content.requests, "post", return_value=ok) as post:
            brief, prov = ai_content.generate_brief(FakeArt())
        self.assertEqual(prov, "mistral")  # gemini path returns junk shape -> falls through to mistral

    def test_image_chain_all_fail_returns_none(self):
        with mock.patch.object(ai_image.requests, "get", side_effect=Exception("down")), \
             mock.patch.object(ai_image.requests, "post", side_effect=Exception("down")):
            data, prov = ai_image.fetch_ai_cover(FakeArt())
        self.assertIsNone(data); self.assertIsNone(prov)
