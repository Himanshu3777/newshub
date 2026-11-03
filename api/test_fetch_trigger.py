"""Fetch trigger endpoint: token gate + async start, scheduler-facing."""
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(FETCH_TRIGGER_TOKEN="tok-abc-123")
class FetchTriggerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_token_is_forbidden(self):
        with mock.patch("api.views.trigger_fetch_async") as trig:
            r = self.client.get("/api/fetch/trigger/")
        self.assertEqual(r.status_code, 403)
        trig.assert_not_called()

    def test_wrong_token_is_forbidden(self):
        with mock.patch("api.views.trigger_fetch_async") as trig:
            r = self.client.get("/api/fetch/trigger/?token=nope")
        self.assertEqual(r.status_code, 403)
        trig.assert_not_called()

    def test_correct_token_triggers_scan(self):
        with mock.patch("api.views.trigger_fetch_async") as trig:
            r = self.client.get("/api/fetch/trigger/?token=tok-abc-123")
        self.assertEqual(r.status_code, 202)
        trig.assert_called_once_with()

    @override_settings(FETCH_TRIGGER_TOKEN="")
    def test_disabled_when_token_not_configured(self):
        with mock.patch("api.views.trigger_fetch_async") as trig:
            r = self.client.get("/api/fetch/trigger/?token=anything")
        self.assertEqual(r.status_code, 404)
        trig.assert_not_called()
