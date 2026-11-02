from django.test import TestCase
from rest_framework.test import APIClient
from feedback_app.models import UserFeedback, CorrectionRequest

class MassAssignmentTests(TestCase):
    """Public create endpoints must never accept staff-controlled fields."""
    def setUp(self):
        self.client = APIClient()

    def test_feedback_cannot_self_resolve(self):
        r = self.client.post("/api/feedback/", {"name": "Asha", "email": "a@b.in",
                             "message": "hello", "is_resolved": True}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(UserFeedback.objects.get().is_resolved)

    def test_correction_cannot_pre_accept(self):
        r = self.client.post("/api/corrections/", {"name": "Asha", "email": "a@b.in",
                             "description": "wrong date", "status": "accepted"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(CorrectionRequest.objects.get().status, "pending")

    def test_sensitive_findings_are_admin_only(self):
        r = self.client.get("/api/sensitive/")
        self.assertIn(r.status_code, (401, 403))
