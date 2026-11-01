"""The AI Traffic Controller (spec 16).

Every request flows: classify -> check cache -> for each candidate in the
class order: check quota + health -> attempt ONCE -> log -> on success cache
and return. A failed provider is never retried in the same request; repeated
failures across requests push it into cooldown (quota.py). The local text
composer and the SVG generator sit inside every chain as the final guarantee,
so a NewsHub story can never end up with content-but-no-cover or vice versa.
"""
import time
from airouter import quota, cache as aicache, cost_guard, priority
from airouter.models import AIGenerationLog
from airouter.providers_text import TEXT_PROVIDERS
from airouter.providers_image import IMAGE_PROVIDERS

# Candidate cloud providers per request class. The FINAL order is produced
# dynamically by the priority engine (access level + configured capacity +
# remaining quota + health) - never a fixed blind sequence (spec 4/16).
# "local" is not ranked: first for simple requests, last-resort guarantee
# for everything else. Paid providers (deepseek) are absent by design; the
# zero-billing cost guard is a second, independent layer of protection.
TEXT_CLOUD = ["gemini", "groq", "openrouter", "cloudflare", "mistral",
              "huggingface", "pollinations", "qwen", "nvidia"]
TEXT_ORDERS = {
    "simple":  ["local"] + TEXT_CLOUD,
    "normal":  TEXT_CLOUD + ["local"],
    "premium": TEXT_CLOUD + ["local"],
    "complex": TEXT_CLOUD + ["local"],
}

def _ranked_text_order(request_class):
    base = TEXT_ORDERS.get(request_class, TEXT_ORDERS["normal"])
    cloud = [s for s in base if s != "local"]
    ranked = priority.rank(cloud, "text")
    return (["local"] + ranked) if base[0] == "local" else (ranked + ["local"])
SVG_TYPES = {"icon", "chart", "graph", "diagram", "logo", "decorative",
             "simple_illustration", "infographic", "news_card"}
IMAGE_ORDERS = {
    "svg": ["svg"],
    "realistic": ["pollinations", "gemini", "huggingface", "svg"],
    "text_in_image": ["pollinations", "gemini", "huggingface", "svg"],
}

def classify_image(image_type):
    t = (image_type or "news_photo").lower()
    if t in SVG_TYPES: return "svg"
    if t in ("poster", "text_in_image", "logo_text"): return "text_in_image"
    return "realistic"

def _log(**kw):
    try: AIGenerationLog.objects.create(**kw)
    except Exception: pass

def _status_map(kind, slugs):
    return {s: quota.provider_status(s, kind) for s in slugs}

def generate_text(prompt, request_class="normal", local_fn=None, use_cache=True):
    order = _ranked_text_order(request_class)
    params = {"class": request_class}
    if use_cache:
        hit = aicache.get("text", prompt, params)
        if hit:
            _log(request_type="text", request_class=request_class, provider=hit.provider,
                 model=hit.model, success=True, cached=True)
            return {"success": True, "provider": hit.provider, "model": hit.model,
                    "fallback_used": False, "cached": True, "content": hit.text_result}
    tried = []
    for i, slug in enumerate(order):
        if slug == "local":
            if local_fn is None: continue
            t0 = time.time()
            try:
                content, model = local_fn(prompt)
                ok = bool(content)
            except Exception as e:
                content, model, ok = None, "local", False
            ms = int((time.time() - t0) * 1000)
            _log(request_type="text", request_class=request_class, provider="local", model=model or "local",
                 success=ok, response_ms=ms, fallback_used=i > 0, failure_reason="" if ok else "local failed")
            if ok:
                if use_cache: aicache.put("text", prompt, "local", model or "local", params, text=content)
                return {"success": True, "provider": "local", "model": model or "local",
                        "fallback_used": i > 0, "cached": False, "content": content}
            tried.append("local"); continue
        allowed, why = cost_guard.provider_allowed(slug)
        if not allowed:
            _log(request_type="text", request_class=request_class, provider=slug,
                 success=False, failure_reason=why, fallback_used=i > 0)
            tried.append(slug); continue
        if not quota.is_available(slug, "text"):
            tried.append(slug); continue
        fn = TEXT_PROVIDERS[slug]
        t0 = time.time()
        res = fn(prompt)
        ms = int((time.time() - t0) * 1000)
        reached = res["reason"] != "no api key configured"
        rem = quota.increment_use(slug, "text") if reached else quota.remaining(slug, "text")
        if res["ok"]:
            quota.mark_success(slug)
            _log(request_type="text", request_class=request_class, provider=slug, model=res["model"],
                 success=True, response_ms=ms, tokens_used=res.get("tokens", 0),
                 quota_remaining=rem, fallback_used=i > 0)
            if use_cache: aicache.put("text", prompt, slug, res["model"], params, text=res["content"])
            return {"success": True, "provider": slug, "model": res["model"],
                    "fallback_used": i > 0, "cached": False, "content": res["content"]}
        if res["reason"] != "no api key configured":
            quota.record_failure(slug, "text", res["reason"])
        _log(request_type="text", request_class=request_class, provider=slug, model=res["model"],
             success=False, response_ms=ms, quota_remaining=rem, fallback_used=i > 0,
             failure_reason=res["reason"])
        tried.append(slug)
    return {"success": False,
            "error": "All configured AI providers are currently unavailable.",
            "provider_status": _status_map("text", order)}

def generate_image(prompt, image_type="news_photo", seed=7, svg_fn=None, use_cache=True):
    group = classify_image(image_type)
    order = list(IMAGE_ORDERS[group])
    if group != "svg":
        external = [s for s in order if s != "svg"]
        order = priority.rank(external, "image") + ["svg"]
    params = {"type": image_type, "seed": seed}
    if use_cache:
        hit = aicache.get("image", prompt, params)
        if hit and hit.image_result:
            _log(request_type="image", request_class=image_type, provider=hit.provider,
                 model=hit.model, success=True, cached=True)
            return {"success": True, "provider": hit.provider, "model": hit.model,
                    "fallback_used": False, "cached": True, "content": bytes(hit.image_result)}
    for i, slug in enumerate(order):
        if slug == "svg":
            if svg_fn is None: continue
            t0 = time.time()
            try:
                data = svg_fn(prompt)
                ok = bool(data)
            except Exception:
                data, ok = None, False
            ms = int((time.time() - t0) * 1000)
            _log(request_type="image", request_class=image_type, provider="svg", model="local-svg",
                 success=ok, response_ms=ms, fallback_used=i > 0, failure_reason="" if ok else "svg failed")
            if ok:
                return {"success": True, "provider": "svg", "model": "local-svg",
                        "fallback_used": i > 0, "cached": False, "content": data}
            continue
        allowed, why = cost_guard.provider_allowed(slug)
        if not allowed:
            _log(request_type="image", request_class=image_type, provider=slug,
                 success=False, failure_reason=why, fallback_used=i > 0)
            continue
        if not quota.is_available(slug, "image"):
            continue
        fn = IMAGE_PROVIDERS[slug]
        t0 = time.time()
        res = fn(prompt, seed)
        ms = int((time.time() - t0) * 1000)
        reached = res["reason"] != "no api key configured"
        rem = quota.increment_use(slug, "image") if reached else quota.remaining(slug, "image")
        if res["ok"]:
            quota.mark_success(slug)
            _log(request_type="image", request_class=image_type, provider=slug, model=res["model"],
                 success=True, response_ms=ms, quota_remaining=rem, fallback_used=i > 0)
            if use_cache: aicache.put("image", prompt, slug, res["model"], params, image=res["content"])
            return {"success": True, "provider": slug, "model": res["model"],
                    "fallback_used": i > 0, "cached": False, "content": res["content"]}
        if res["reason"] != "no api key configured":
            quota.record_failure(slug, "image", res["reason"])
        _log(request_type="image", request_class=image_type, provider=slug, model=res["model"],
             success=False, response_ms=ms, quota_remaining=rem, fallback_used=i > 0,
             failure_reason=res["reason"])
    return {"success": False,
            "error": "All configured AI providers are currently unavailable.",
            "provider_status": _status_map("image", order)}

def provider_snapshot():
    """Rows for the /ai/ dashboard: status, used today, remaining - per spec 13."""
    rows = []
    for kind, slugs in (("text", ["local", "pollinations", "groq", "openrouter", "cloudflare", "gemini", "mistral", "huggingface", "qwen", "nvidia", "deepseek"]),
                        ("image", ["svg", "pollinations", "gemini", "huggingface", "ideogram"])):
        for slug in slugs:
            lim = quota.limit_for(slug, kind)
            from airouter import registry as _reg, cost_guard as _cg
            entry = _reg.get(slug)
            allowed, _why = _cg.provider_allowed(slug)
            status = quota.provider_status(slug, kind)
            if not allowed: status = "disabled_paid"
            rows.append({"kind": kind, "provider": slug,
                         "name": entry["name"] if entry else slug,
                         "level": entry["level"] if entry else "-",
                         "free_type": entry["free_type"] if entry else "-",
                         "key_env": entry["key_env"] if entry else "",
                         "status": status,
                         "used": quota.used_today(slug, kind),
                         "month_used": quota.month_used(slug, kind),
                         "limit": "unlimited" if lim < 0 else lim,
                         "remaining": "—" if lim < 0 else quota.remaining(slug, kind)})
    return rows

def today_totals():
    from django.utils import timezone
    start = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    qs = AIGenerationLog.objects.filter(created_at__gte=start)
    from django.db.models import Count
    most = (qs.filter(success=True).values("provider").annotate(n=Count("id")).order_by("-n").first())
    return {
        "text_today": qs.filter(request_type="text", success=True, cached=False).count(),
        "images_today": qs.filter(request_type="image", success=True, cached=False).count(),
        "success": qs.filter(success=True).count(),
        "failed": qs.filter(success=False).count(),
        "fallbacks": qs.filter(success=True, fallback_used=True).count(),
        "cached_hits": qs.filter(cached=True).count(),
        "most_used": (most or {}).get("provider", "—"),
    }
