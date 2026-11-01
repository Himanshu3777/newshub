"""Quota + health manager for the AI Router.

- Daily usage lives in ProviderUsage rows keyed by the Asia/Kolkata date, so a
  new day automatically means a fresh quota (spec 4). Nothing to reset by hand.
- Limits come from settings.AI_DAILY_LIMITS (env-driven, spec 14); -1 = no cap.
- Repeated failures push a provider into COOLDOWN (spec 5); a 429 marks it
  RATE_LIMITED with a short cooldown; hitting the daily cap marks QUOTA_EXHAUSTED.
"""
import datetime
from django.conf import settings
from django.utils import timezone
from airouter.models import ProviderUsage, ProviderState

def today_ist():
    return timezone.localtime(timezone.now()).date()

def limit_for(provider, kind):
    return settings.AI_DAILY_LIMITS.get(f"{provider}_{kind}", 0)

def used_today(provider, kind):
    row = ProviderUsage.objects.filter(date=today_ist(), provider=provider, kind=kind).first()
    return row.used if row else 0

def remaining(provider, kind):
    lim = limit_for(provider, kind)
    if lim < 0: return -1  # unlimited (local/svg)
    return max(0, lim - used_today(provider, kind))

def state_of(provider):
    st, _ = ProviderState.objects.get_or_create(provider=provider)
    if st.cooldown_until and st.cooldown_until <= timezone.now() and st.status in ("cooldown", "rate_limited"):
        st.status = "available"; st.cooldown_until = None; st.consecutive_failures = 0; st.save()
    return st

def provider_status(provider, kind):
    """One of: available / exhausted / cooldown / rate_limited / disabled / error"""
    if limit_for(provider, kind) == 0:
        return "disabled"
    st = state_of(provider)
    if st.status == "disabled":
        return "disabled"
    if remaining(provider, kind) == 0:
        return "quota_exhausted"
    if month_remaining(provider, kind) == 0:
        return "quota_exhausted"
    if st.status in ("cooldown", "rate_limited") and st.cooldown_until and st.cooldown_until > timezone.now():
        return st.status
    if st.status == "error" and st.consecutive_failures >= getattr(settings, "AI_FAILURE_THRESHOLD", 3):
        return "error"
    return "available"

def is_available(provider, kind):
    return provider_status(provider, kind) == "available"

def record_use(provider, kind):
    row, _ = ProviderUsage.objects.get_or_create(date=today_ist(), provider=provider, kind=kind)
    row.used += 1; row.save(update_fields=["used"])
    st = state_of(provider)
    st.consecutive_failures = 0; st.status = "available"; st.last_success_at = timezone.now(); st.save()
    return remaining(provider, kind)

def record_failure(provider, kind, reason):
    st = state_of(provider)
    st.consecutive_failures += 1
    st.last_error = (reason or "")[:300]
    mins = getattr(settings, "AI_COOLDOWN_MINUTES", 10)
    low = (reason or "").lower()
    if "429" in low or "rate" in low:
        st.status = "rate_limited"
        st.cooldown_until = timezone.now() + datetime.timedelta(minutes=mins)
    elif st.consecutive_failures >= getattr(settings, "AI_FAILURE_THRESHOLD", 3):
        st.status = "cooldown"
        st.cooldown_until = timezone.now() + datetime.timedelta(minutes=mins)
    else:
        st.status = "error"
    st.save()
    return st.status

def increment_use(provider, kind):
    """Count one real attempt that reached the provider (no state change)."""
    row, _ = ProviderUsage.objects.get_or_create(date=today_ist(), provider=provider, kind=kind)
    row.used += 1; row.save(update_fields=["used"])
    return remaining(provider, kind)

def mark_success(provider):
    st = state_of(provider)
    st.consecutive_failures = 0; st.status = "available"; st.last_success_at = timezone.now(); st.save()

def month_used(provider, kind):
    """Sum of this month's daily rows (Asia/Kolkata month) - monthly tracking
    without a separate counter that could drift out of sync."""
    t = today_ist()
    total = 0
    for row in ProviderUsage.objects.filter(provider=provider, kind=kind,
                                            date__year=t.year, date__month=t.month):
        total += row.used
    return total

def month_limit_for(provider, kind):
    return getattr(settings, "AI_MONTHLY_LIMITS", {}).get(f"{provider}_{kind}", 0)

def month_remaining(provider, kind):
    lim = month_limit_for(provider, kind)
    if lim <= 0: return -1
    return max(0, lim - month_used(provider, kind))
