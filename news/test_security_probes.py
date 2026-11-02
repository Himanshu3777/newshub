"""Security probes: hostile-input tests against the running application.
These simulate attacker behaviour (SQLi strings, XSS payloads, CSRF-less
form posts, unauthenticated admin actions, request flooding) and assert the
application's defences respond correctly."""
from django.test import TestCase, Client
from django.utils import timezone
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory

class SecurityProbes(TestCase):
    def setUp(self):
        self.src = NewsSource.objects.create(name="ProbeWire", slug="probewire",
                                             website="https://example.com",
                                             feed_url="https://example.com/f")
        self.cat = NewsCategory.objects.create(name="India", slug="india-probe")
        self.art = NewsArticle.objects.create(
            title="Normal Headline For Probes", summary="s", source=self.src,
            source_url="https://example.com/p1", category=self.cat,
            published_at=timezone.now(), ai_brief="Brief text for probes.")

    def test_sqli_strings_do_not_error_or_leak(self):
        c = Client()
        for q in ["' OR '1'='1", "'; DROP TABLE news_newsarticle; --", "\" OR 1=1 --"]:
            r = c.get("/api/search/", {"q": q})
            self.assertEqual(r.status_code, 200)
            r2 = c.get("/api/articles/", {"search": q})
            self.assertEqual(r2.status_code, 200)
        self.assertTrue(NewsArticle.objects.filter(id=self.art.id).exists())  # table intact

    def test_xss_payload_is_escaped_on_pages(self):
        evil = NewsArticle.objects.create(
            title="<script>alert(1)</script> Breaking", summary="s", source=self.src,
            source_url="https://example.com/evil", category=self.cat,
            published_at=timezone.now(), ai_brief="brief")
        r = Client().get(f"/news/{evil.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"<script>alert(1)</script>", r.content)
        self.assertIn(b"&lt;script&gt;", r.content)

    def test_csrf_required_on_web_forms(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post("/check-claim/", {"claim_text": "Some claim text that is long enough.",
                                     "platform": "other", "source_url": ""})
        self.assertEqual(r.status_code, 403)

    def test_admin_actions_require_authentication(self):
        c = Client()
        self.assertIn(c.post("/api/fetch/run/").status_code, (401, 403))
        self.assertIn(c.post(f"/api/verify/{self.art.id}/").status_code, (401, 403))
        self.assertIn(c.get("/api/sensitive/").status_code, (401, 403))

    def test_post_rate_limit_blocks_flood(self):
        # A dedicated source IP keeps this flood in its own rate-limit bucket:
        # it must not throttle the other tests that share the default test IP.
        c = Client()
        codes = []
        for i in range(32):
            codes.append(c.post("/api/feedback/", {"name": "Flood", "email": "f@e.in",
                              "message": f"msg {i}"}, content_type="application/json",
                              REMOTE_ADDR="10.9.9.9").status_code)
        self.assertIn(429, codes)               # middleware limit (30/min/IP) kicked in
        self.assertTrue(all(code == 201 for code in codes[:5]))  # normal use unaffected
