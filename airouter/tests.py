from unittest import mock
from django.test import TestCase, override_settings
from airouter import router, quota
from airouter.models import ProviderUsage, AIGenerationLog, AICache

def ok_text(prompt):
    return {"ok": True, "content": "A valid generated brief that is comfortably longer than forty characters for the test.", "model": "mock-model", "reason": "", "tokens": 42}
def fail_text(prompt):
    return {"ok": False, "content": None, "model": "mock-model", "reason": "429 rate limited", "tokens": 0}

class RouterTextTests(TestCase):
    def test_fallback_order_and_success(self):
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": fail_text, "mistral": ok_text}, clear=False):
            with mock.patch.dict(router.TEXT_PROVIDERS, {"qwen": fail_text, "deepseek": fail_text, "pollinations": fail_text}, clear=False):
                res = router.generate_text("Write a brief about monsoon rains", request_class="normal", use_cache=False)
        self.assertTrue(res["success"]); self.assertEqual(res["provider"], "mistral"); self.assertTrue(res["fallback_used"])
        self.assertTrue(AIGenerationLog.objects.filter(provider="mistral", success=True).exists())

    def test_cache_hit_uses_no_quota(self):
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": ok_text}, clear=False):
            r1 = router.generate_text("Unique prompt about space mission", request_class="normal")
            used_after_first = quota.used_today("gemini", "text")
            r2 = router.generate_text("Unique prompt about space mission", request_class="normal")
        self.assertTrue(r1["success"]); self.assertTrue(r2.get("cached"))
        self.assertEqual(quota.used_today("gemini", "text"), used_after_first)

    def test_quota_exhausted_skips_provider(self):
        row = ProviderUsage.objects.create(date=quota.today_ist(), provider="gemini", kind="text",
                                           used=quota.limit_for("gemini", "text"))
        self.assertEqual(quota.provider_status("gemini", "text"), "quota_exhausted")
        others = {slug: fail_text for slug in ("groq", "openrouter", "cloudflare", "huggingface", "pollinations", "qwen", "nvidia")}
        with mock.patch.dict(router.TEXT_PROVIDERS, {**others, "gemini": ok_text, "mistral": ok_text}, clear=False):
            res = router.generate_text("Another unique prompt about cricket", request_class="normal", use_cache=False)
        self.assertEqual(res["provider"], "mistral")

    def test_cooldown_after_repeated_failures(self):
        for _ in range(3):
            quota.record_failure("qwen", "text", "http 500")
        self.assertIn(quota.provider_status("qwen", "text"), ("cooldown", "error"))

    def test_simple_request_prefers_local(self):
        def local_fn(prompt):
            return ("Local composed content that is long enough to count as a valid brief output.", "local-composer")
        res = router.generate_text("Generate 5 news titles", request_class="simple", local_fn=local_fn, use_cache=False)
        self.assertTrue(res["success"]); self.assertEqual(res["provider"], "local")

    def test_all_fail_returns_spec_error_shape(self):
        with mock.patch.dict(router.TEXT_PROVIDERS, {"gemini": fail_text, "mistral": fail_text, "qwen": fail_text,
                                                     "deepseek": fail_text, "pollinations": fail_text}, clear=False):
            res = router.generate_text("Prompt that will fail everywhere in this test", request_class="normal", use_cache=False)
        self.assertFalse(res["success"]); self.assertIn("provider_status", res); self.assertIn("error", res)

class RouterImageTests(TestCase):
    def test_svg_classification(self):
        self.assertEqual(router.classify_image("icon"), "svg")
        self.assertEqual(router.classify_image("chart"), "svg")
        self.assertEqual(router.classify_image("news_photo"), "realistic")
        self.assertEqual(router.classify_image("poster"), "text_in_image")

    def test_svg_type_uses_local_svg_only(self):
        res = router.generate_image("draw a simple chart", image_type="chart",
                                    svg_fn=lambda p: "<svg>ok</svg>", use_cache=False)
        self.assertTrue(res["success"]); self.assertEqual(res["provider"], "svg")

from airouter import cost_guard, priority, registry

class EcosystemTests(TestCase):
    def test_cost_guard_blocks_paid_providers(self):
        ok, why = cost_guard.provider_allowed("deepseek")
        self.assertFalse(ok); self.assertIn("zero-billing", why)
        ok2, _ = cost_guard.provider_allowed("ideogram")
        self.assertFalse(ok2)
        ok3, _ = cost_guard.provider_allowed("gemini")
        self.assertTrue(ok3)

    def test_openrouter_paid_model_blocked_free_allowed(self):
        bad, _ = cost_guard.provider_allowed("openrouter", "openai/gpt-4o")
        self.assertFalse(bad)
        good, _ = cost_guard.provider_allowed("openrouter", "meta-llama/llama-3.3-70b-instruct:free")
        self.assertTrue(good)

    def test_deepseek_never_called_when_all_free_fail(self):
        spy = mock.Mock(return_value={"ok": True, "content": "paid content must never be used in this project at all.", "model": "deepseek-chat", "reason": "", "tokens": 1})
        failing = {slug: fail_text for slug in ("gemini", "groq", "openrouter", "cloudflare", "mistral", "huggingface", "pollinations", "qwen", "nvidia")}
        with mock.patch.dict(router.TEXT_PROVIDERS, {**failing, "deepseek": spy}, clear=False):
            res = router.generate_text("Prompt where every free provider is down", request_class="normal", use_cache=False)
        self.assertFalse(res["success"])
        spy.assert_not_called()

    def test_ranking_free_high_quota_above_trial(self):
        ranked = priority.rank(["qwen", "groq", "gemini"], "text")
        self.assertEqual(ranked[0], "groq")       # P2 high-quota beats P3/P4
        self.assertEqual(ranked[-1], "qwen")      # trial credits last

    def test_monthly_quota_exhaustion(self):
        from django.conf import settings
        lim = quota.month_limit_for("huggingface", "text")
        self.assertGreater(lim, 0)
        ProviderUsage.objects.create(date=quota.today_ist(), provider="huggingface", kind="text", used=lim)
        self.assertEqual(quota.month_remaining("huggingface", "text"), 0)
        self.assertEqual(quota.provider_status("huggingface", "text"), "quota_exhausted")

    def test_registry_paid_entries_are_unverified(self):
        for entry in registry.REGISTRY:
            if entry["free_type"] == "PAID":
                self.assertFalse(entry["free_only_verified"])
                self.assertEqual(entry["level"], 5)
