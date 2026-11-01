"""Priority engine (spec 4). Ranks eligible providers dynamically.

Score = access-level base (P1 400 / P2 300 / P3 200 / P4 100)
      + capacity points from the CONFIGURED daily cap (log scale, so a
        10,000/day provider outranks a 100/day one without drowning health)
      + remaining-quota ratio bonus (prefer providers with quota left)
      + health bonus (recent success) / penalty (recent failures).
PAID providers are excluded before scoring - they are never ranked.
Quota types are never mixed: ranking only compares providers of the SAME
category+kind, using that kind's own daily cap.
"""
import math
from airouter import quota
from airouter.registry import get as reg_get

LEVEL_BASE = {1: 400, 2: 300, 3: 200, 4: 100, 5: -10000}

def score(slug, kind):
    entry = reg_get(slug)
    level = entry["level"] if entry else 3
    base = LEVEL_BASE.get(level, 0)
    lim = quota.limit_for(slug, kind)
    capacity = 0 if lim <= 0 else min(60, 12 * math.log10(max(10, lim)))
    rem = quota.remaining(slug, kind)
    ratio = 1.0 if lim < 0 else (rem / lim if lim else 0)
    health = 0
    try:
        st = quota.state_of(slug)
        if st.last_success_at: health += 10
        health -= 8 * (st.consecutive_failures or 0)
        if st.status in ("cooldown", "rate_limited"): health -= 40
    except Exception:
        pass
    return base + capacity + 40 * ratio + health

def rank(slugs, kind):
    """Eligible slugs sorted best-first (paid/unverified already filtered by caller/guard)."""
    return sorted(slugs, key=lambda s: score(s, kind), reverse=True)
