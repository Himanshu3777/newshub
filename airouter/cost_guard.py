"""ZERO-BILLING GUARD (spec 8). Checked before EVERY external provider call.

FREE_ONLY=True, ALLOW_PAID_APIS=False, AUTO_UPGRADE=False,
AUTO_PURCHASE_CREDITS=False, MAX_BILLING=0, ALLOW_PAID_FALLBACK=False.

A provider may be called only if the registry marks it free_only_verified
and its free_type is not PAID. OpenRouter is additionally restricted to
models whose id ends with ':free'. If every free provider fails, the router
returns a controlled error - it NEVER falls through to a paid API.
"""
from django.conf import settings
from airouter import registry

FREE_ONLY = getattr(settings, "AI_FREE_ONLY", True)
ALLOW_PAID_APIS = False
AUTO_UPGRADE = False
AUTO_PURCHASE_CREDITS = False
MAX_BILLING = 0
ALLOW_PAID_FALLBACK = False

def provider_allowed(slug, model=""):
    """Return (allowed: bool, reason: str)."""
    entry = registry.get(slug)
    if entry is None:
        return True, ""  # local/in-process slugs not in registry pass
    if entry["free_type"] == "PAID" or not entry.get("free_only_verified"):
        return False, f"blocked by zero-billing guard ({entry['free_type']}, not verified free)"
    if slug == "openrouter" and model and not model.endswith(":free"):
        return False, "blocked by zero-billing guard (OpenRouter model is not a :free model)"
    return True, ""
