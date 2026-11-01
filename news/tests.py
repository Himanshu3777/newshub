from django.test import TestCase, Client
from django.utils import timezone
from news.services import clean_html, normalize_title, detect_language, classify_category, title_similarity, is_duplicate_candidate, extract_keywords
from moderation.services import detect_sensitive, mask
from verification.services import extract_claims, score_verification
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory

class CleaningTests(TestCase):
    def test_clean_html(self): self.assertEqual(clean_html("<p>Hello <b>World</b></p>"), "Hello World")
    def test_normalize_title(self): self.assertEqual(normalize_title("India Wins! Match."), "india wins match")
    def test_hindi_detect(self): self.assertEqual(detect_language("भारत ने मैच जीता"), "hi")
    def test_category(self): self.assertEqual(classify_category("Sensex rises as market gains", "stock trade"), "Business")
    def test_similarity_dup(self):
        dup,_=is_duplicate_candidate("India wins cricket match", ["India wins cricket match today"])
        self.assertTrue(title_similarity("India wins match","India wins match")>0.9)
    def test_keywords(self): self.assertIn("cricket", extract_keywords("cricket cricket match india cricket"))

class SensitiveTests(TestCase):
    def test_phone(self): self.assertTrue(any(f["type"]=="phone" for f in detect_sensitive("Call 9876543210 now")))
    def test_email(self): self.assertTrue(any(f["type"]=="email" for f in detect_sensitive("mail a@b.com")))
    def test_mask_no_raw(self): self.assertNotIn("9876543210", mask("9876543210")); self.assertIn("*", mask("9876543210"))
    def test_pan(self): self.assertTrue(any(f["type"]=="pan" for f in detect_sensitive("PAN ABCDE1234F")))

class VerificationTests(TestCase):
    def test_claims(self): self.assertTrue(len(extract_claims("India launches mission in 2026 with ISRO scientists", ""))>=1)
    def test_no_fake_verified(self):
        status,conf,_=score_verification(None, [], related_count=0); self.assertIn(status,["needs_review","unverified"])
        status2,_,_=score_verification(None, [], related_count=3); self.assertEqual(status2,"partially_verified")  # repetition alone != verified
    def test_factcheck_false(self):
        status,_,_=score_verification(None, [{"rating":"False"}], related_count=0); self.assertEqual(status,"false")

class ApiTests(TestCase):
    def setUp(self):
        self.src=NewsSource.objects.create(name="Test News",slug="test-news",website="https://example.com",feed_url="https://example.com/rss")
        cat=NewsCategory.objects.create(name="National",slug="national")
        self.art=NewsArticle.objects.create(title="Test headline for India",summary="summary",source=self.src,source_url="https://example.com/1",category=cat,published_at=timezone.now())
    def test_home(self): self.assertEqual(Client().get("/").status_code,200)
    def test_health(self): self.assertEqual(Client().get("/health/").status_code,200)
    def test_api_articles(self):
        r=Client().get("/api/articles/"); self.assertEqual(r.status_code,200); self.assertTrue(r.json()["count"]>=1)
    def test_api_stats(self): self.assertIn("total", Client().get("/api/stats/").json())
    def test_api_search(self): self.assertEqual(Client().get("/api/search/?q=India").status_code,200)
    def test_detail(self): self.assertEqual(Client().get(f"/news/{self.art.slug}/").status_code,200)
    def test_feedback_post(self):
        r=Client().post("/api/feedback/",{"name":"A","email":"a@b.com","message":"hi"},content_type="application/json"); self.assertIn(r.status_code,[200,201])
    def test_sensitive_admin_only(self): self.assertIn(Client().get("/api/sensitive/").status_code,[401,403])

class NewsHubHandlingTests(TestCase):
    def setUp(self):
        self.src=NewsSource.objects.create(name="Hub Test",slug="hub-test",website="https://example.com",feed_url="https://example.com/rss")
        self.cat=NewsCategory.objects.create(name="National",slug="national-hub")
    def _art(self,title,status="unverified",**kw):
        return NewsArticle.objects.create(title=title,summary=kw.pop("summary","s"),source=self.src,source_url=f"https://example.com/{abs(hash(title))%99999}",category=self.cat,published_at=timezone.now(),verification_status=status,**kw)
    def test_social_detection(self):
        from news.services import detect_social_origin
        desc,note=detect_social_origin("Big claim spreads","According to a viral Instagram video, the bridge collapsed")
        self.assertIsNotNone(desc); self.assertIn("not been confirmed",note)
        desc2,_=detect_social_origin("Parliament passes bill","The Lok Sabha passed the bill on Tuesday")
        self.assertIsNone(desc2)
    def test_no_verification_badges_on_home(self):
        self._art("Normal publisher story from Delhi")
        html=Client().get("/").content.decode()
        self.assertNotIn("Needs Human Review",html); self.assertNotIn(">Unverified<",html)
    def test_source_note_shown_for_unconfirmed(self):
        self._art("Viral claim story",is_unconfirmed=True,source_note="According to a viral social media post, but this has not been confirmed.")
        html=Client().get("/").content.decode()
        self.assertIn("not been confirmed",html)
    def test_quarantine_hidden_from_feed_and_api(self):
        self._art("Fake cure story",status="false")
        self._art("Real story from Delhi")
        html=Client().get("/").content.decode()
        self.assertNotIn("Fake cure story",html); self.assertIn("Real story from Delhi",html)
        data=Client().get("/api/articles/").json()
        titles=[r["title"] for r in data["results"]]
        self.assertNotIn("Fake cure story",titles)
    def test_quarantined_detail_shows_warning(self):
        a=self._art("Misleading claim story",status="misleading")
        html=Client().get(f"/news/{a.slug}/").content.decode()
        self.assertIn("flagged and removed",html)
    def test_claim_check_not_confirmed_and_never_published(self):
        before=NewsArticle.objects.count()
        r=Client().post("/check-claim/",{"platform":"whatsapp","claim_text":"Forward this: drinking hot water cures all diseases instantly, doctors hide this secret"})
        self.assertEqual(r.status_code,200)
        self.assertIn("Not confirmed",r.content.decode())
        self.assertEqual(NewsArticle.objects.count(),before)  # submission never becomes news
        from verification.models import ClaimSubmission
        self.assertEqual(ClaimSubmission.objects.count(),1)

class AIContentAndThemeTests(TestCase):
    def setUp(self):
        self.src=NewsSource.objects.create(name="AI Test",slug="ai-test",website="https://example.com",feed_url="https://example.com/rss")
        self.cat=NewsCategory.objects.create(name="Technology",slug="technology-ai")
        self.art=NewsArticle.objects.create(title="ISRO launches new satellite mission for farmers",summary="Internal feed text that must not be displayed publicly on the site.",source=self.src,source_url="https://example.com/ai1",category=self.cat,published_at=timezone.now())
    def test_brief_is_original(self):
        from news.ai_content import generate_brief
        brief,prov=generate_brief(self.art)
        self.assertNotIn("Internal feed text",brief)
        self.assertIn("AI Test",brief); self.assertTrue(len(brief)>60)
    def test_cover_is_svg_original(self):
        r=Client().get(f"/cover/{self.art.id}/")
        self.assertEqual(r.status_code,200); self.assertIn("image/svg+xml",r["Content-Type"])
        self.assertIn("AI ILLUSTRATION",r.content.decode())
    def test_detail_shows_brief_not_publisher_text(self):
        self.art.ai_brief="Our own original brief about the satellite mission."; self.art.save()
        html=Client().get(f"/news/{self.art.slug}/").content.decode()
        self.assertIn("Our own original brief",html)
        self.assertNotIn("Internal feed text",html)
    def test_theme_toggle_present(self):
        html=Client().get("/").content.decode()
        self.assertIn("theme-toggle",html); self.assertIn("theme.js",html)
    def test_sources_expanded(self):
        from sources.models import NewsSource as NS
        from django.core.management import call_command
        call_command("seed_sources")
        self.assertGreaterEqual(NS.objects.count(),17)
