"""Contact/feedback/correction form workflows + model basics + command guards."""
import io, os, re, tempfile
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from sources.models import NewsSource
from news.models import NewsArticle, NewsCategory
from feedback_app.models import UserFeedback, CorrectionRequest
from moderation.models import SensitiveContentFinding
from airouter.models import AIGenerationLog

class ContactFormTests(TestCase):
    def setUp(self): self.c = Client()
    def test_valid_feedback_saved_with_reference(self):
        r = self.c.post("/contact/", {"name": "Reader One", "email": "r@example.com",
                                      "category": "general", "subject": "Nice site",
                                      "message": "Loved the coverage today."})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(UserFeedback.objects.count(), 1)

    def test_invalid_feedback_rejected_nothing_saved(self):
        r = self.c.post("/contact/", {"name": "", "email": "not-an-email",
                                      "category": "general", "subject": "", "message": ""})
        self.assertEqual(r.status_code, 200)  # form redisplayed with errors
        self.assertEqual(UserFeedback.objects.count(), 0)

    def test_valid_correction_starts_pending(self):
        src = NewsSource.objects.create(name="CWire", slug="cwire", website="https://e.com",
                                        feed_url="https://e.com/f")
        art = NewsArticle.objects.create(title="Correction Target Story", source=src,
                                         source_url="https://e.com/ct", published_at=timezone.now())
        r = self.c.post("/contact/", {"article": art.id, "name": "Reader", "email": "r@example.com",
                                      "description": "The date in this story is wrong."})
        self.assertEqual(r.status_code, 302)
        req = CorrectionRequest.objects.get()
        self.assertEqual(req.status, "pending")

class ModelBasicsTests(TestCase):
    def test_str_representations(self):
        src = NewsSource.objects.create(name="StrWire", slug="strwire", website="https://e.com",
                                        feed_url="https://e.com/f")
        art = NewsArticle.objects.create(title="A Very Specific Headline For Str", source=src,
                                         source_url="https://e.com/str", published_at=timezone.now())
        self.assertEqual(str(src), "StrWire")
        self.assertIn("Very Specific Headline", str(art))
        self.assertEqual(str(NewsCategory(name="Tech", slug="tech-mb")), "Tech")

    def test_generation_log_newest_first(self):
        AIGenerationLog.objects.create(request_type="text", provider="gemini", success=True)
        AIGenerationLog.objects.create(request_type="text", provider="mistral", success=True)
        self.assertEqual(AIGenerationLog.objects.first().provider, "mistral")

class CommandGuardTests(TestCase):
    def test_backup_json_has_no_secrets_and_timestamped_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            call_command("backup_data", out=tmp, stdout=io.StringIO())
            files = os.listdir(tmp)
            self.assertEqual(len(files), 1)
            self.assertRegex(files[0], r"newshub-backup-\d{8}-\d{6}\.json")
            text = open(os.path.join(tmp, files[0]), encoding="utf-8").read()
            for marker in ("gsk_", "sk-or-", "hf_", "nvapi-", "SECRET_KEY", "AIza"):
                self.assertNotIn(marker, text)

    def test_validate_strict_flags_raw_pii_finding(self):
        src = NewsSource.objects.create(name="VWire", slug="vwire", website="https://e.com",
                                        feed_url="https://e.com/f")
        art = NewsArticle.objects.create(title="Validate Target Story", source=src,
                                         source_url="https://e.com/vt", published_at=timezone.now())
        SensitiveContentFinding.objects.create(article=art, finding_type="phone",
                                               matched_text_masked="call 9876543210 now")
        with self.assertRaises(SystemExit) as cm:
            call_command("validate_data", "--strict", stdout=io.StringIO())
        self.assertEqual(cm.exception.code, 1)
