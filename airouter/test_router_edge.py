"""Router edge cases: quota reset semantics, disabled providers, malformed
responses, cache expiry/separation/call-counting, zero-billing under every
temptation (key configured, top rank, free providers down)."""
from datetime import timedelta
from unittest import mock
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from airouter import router, quota, cost_guard, providers_text, cache as aicache
from airouter.models import ProviderUsage, AICache

def ok_text(prompt):
    return {"ok": True, "content": "Generated content that is comfortably longer than forty characters for validation.", "model": "mock", "reason": "", "tokens": 10}
def fail_text(prompt):
    return {"ok": False, "content": None, "model": "mock", "reason": "http 500", "tokens": 0}

OTHERS_FAIL = {s: fail_text for s in ("groq", "openrouter", "cloudflare", "mistral", "huggingface", "pollinations", "qwen", "nvidia")}

class QuotaResetTests(TestCase):
    def test_yesterdays_usage_does_not_count_today(self):
        yesterday = quota.today_ist() - timedelta(days=1)
        ProviderUsage.objects.create(date=yesterday, provider="gemini", kind="text",
                                     used=quota.limit_for("gemini", "text"))
        self.assertEqual(quota.used_today("gemini", "text"), 0)
        self.assertEqual(quota.provider_status("gemini", "text"), "available")

    def test_last_months_usage_does_not_count_this_month(self):
        t = quota.today_ist()
        last_month = (t.replace(day=1) - timedelta(days=1)).replace(day=15)
        lim = quota.month_limit_for("huggingface", "text")
        ProviderUsage.objects.create(date=last_month, provider="huggingface", kind="text", used=lim + 50)
        self.assertEqual(quota.month_used("huggingface", "text"), 0)
        self.assertGreater(quota.month_remaining("huggingface", "text"), 0)

    def test_cache_hit_consumes_no_quota(self):
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": ok_text, **OTHERS_FAIL}, clear=False):
            router.generate_text("Quota cache prompt about rivers", request_class="normal")
            used1 = quota.used_today("gemini", "text")
            router.generate_text("Quota cache prompt about rivers", request_class="normal")
        self.assertEqual(quota.used_today("gemini", "text"), used1)

class DisabledAndKeyTests(TestCase):
    def test_zero_limit_provider_is_disabled_and_skipped(self):
        limits = dict(settings.AI_DAILY_LIMITS); limits["qwen_text"] = 0
        spy = mock.Mock(side_effect=ok_text)
        with override_settings(AI_DAILY_LIMITS=limits):
            self.assertEqual(quota.provider_status("qwen", "text"), "disabled")
            with mock.patch.dict(router.TEXT_PROVIDERS, {"qwen": spy, "mistral": ok_text}, clear=False):
                with mock.patch.dict(router.TEXT_PROVIDERS, {s: fail_text for s in ("gemini", "groq", "openrouter", "cloudflare", "huggingface", "pollinations", "nvidia")}, clear=False):
                    res = router.generate_text("Disabled provider prompt about oceans", request_class="normal", use_cache=False)
        self.assertEqual(res["provider"], "mistral")
        spy.assert_not_called()

    def test_missing_key_consumes_no_quota_and_others_still_work(self):
        # Real gemini function, no key configured anywhere (test env): it must
        # bow out silently while the chain still delivers via another provider.
        with mock.patch.dict(router.TEXT_PROVIDERS, {"mistral": ok_text}, clear=False):
            with mock.patch.dict(router.TEXT_PROVIDERS, {s: fail_text for s in ("groq", "openrouter", "cloudflare", "huggingface", "pollinations", "qwen", "nvidia")}, clear=False):
                res = router.generate_text("Missing key prompt about deserts", request_class="normal", use_cache=False)
        self.assertTrue(res["success"]); self.assertEqual(res["provider"], "mistral")
        self.assertEqual(quota.used_today("gemini", "text"), 0)

class MalformedResponseTests(TestCase):
    def test_malformed_json_from_providers_falls_back_to_local(self):
        bad = mock.Mock(status_code=200); bad.json.side_effect = ValueError("not json")
        with override_settings(GEMINI_API_KEY="k", MISTRAL_API_KEY="k"):
            with mock.patch.object(providers_text.requests, "post", return_value=bad), \
                 mock.patch.object(providers_text.requests, "get", side_effect=Exception("down")):
                res = router.generate_text("Malformed response prompt about forests",
                                           request_class="normal", use_cache=False,
                                           local_fn=lambda p: ("Local safe content generated without any external provider at all.", "local-composer"))
        self.assertTrue(res["success"]); self.assertEqual(res["provider"], "local")

class CacheBehaviourTests(TestCase):
    def test_same_request_twice_calls_provider_once(self):
        spy = mock.Mock(side_effect=ok_text)
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": spy, **OTHERS_FAIL}, clear=False):
            r1 = router.generate_text("Counted cache prompt about lakes", request_class="normal")
            r2 = router.generate_text("Counted cache prompt about lakes", request_class="normal")
        self.assertEqual(spy.call_count, 1)          # API calls = 1
        self.assertTrue(r1["success"] and r2["success"])  # responses = 2
        self.assertTrue(r2.get("cached"))

    def test_expired_cache_regenerates(self):
        spy = mock.Mock(side_effect=ok_text)
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": spy, **OTHERS_FAIL}, clear=False):
            router.generate_text("Expiring cache prompt about hills", request_class="normal")
            AICache.objects.all().update(created_at=timezone.now() - timedelta(hours=72))
            r2 = router.generate_text("Expiring cache prompt about hills", request_class="normal")
        self.assertEqual(spy.call_count, 2)
        self.assertFalse(r2.get("cached", False))

    def test_cache_keys_separate_by_request_class(self):
        k1 = aicache.make_key("text", "same prompt", {"class": "normal"})
        k2 = aicache.make_key("text", "same prompt", {"class": "simple"})
        k3 = aicache.make_key("text", "other prompt", {"class": "normal"})
        self.assertNotEqual(k1, k2); self.assertNotEqual(k1, k3)
        self.assertEqual(k1, aicache.make_key("text", "same prompt", {"class": "normal"}))

class ZeroBillingTemptationTests(TestCase):
    def test_guard_constants_are_hard_off(self):
        self.assertTrue(cost_guard.FREE_ONLY)
        self.assertFalse(cost_guard.ALLOW_PAID_APIS)
        self.assertFalse(cost_guard.AUTO_UPGRADE)
        self.assertFalse(cost_guard.AUTO_PURCHASE_CREDITS)
        self.assertEqual(cost_guard.MAX_BILLING, 0)
        self.assertFalse(cost_guard.ALLOW_PAID_FALLBACK)

    @override_settings(DEEPSEEK_API_KEY="sk-configured-anyway")
    def test_paid_provider_with_key_still_never_called(self):
        allowed, _ = cost_guard.provider_allowed("deepseek")
        self.assertFalse(allowed)
        spy = mock.Mock(side_effect=ok_text)
        failing = {s: fail_text for s in ("gemini", "groq", "openrouter", "cloudflare", "mistral", "huggingface", "pollinations", "qwen", "nvidia")}
        with mock.patch.dict(router.TEXT_PROVIDERS, {**failing, "deepseek": spy}, clear=False):
            res = router.generate_text("Temptation prompt with every free provider down",
                                       request_class="normal", use_cache=False)
        self.assertFalse(res["success"])
        spy.assert_not_called()

    def test_paid_slugs_never_in_ranked_order(self):
        for cls in ("simple", "normal", "premium", "complex"):
            order = router._ranked_text_order(cls)
            self.assertNotIn("deepseek", order)
            self.assertNotIn("ideogram", order)
