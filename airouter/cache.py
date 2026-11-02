"""Hash-based result cache (spec 9). Same prompt+kind+params -> same key ->
cached result, zero provider quota consumed."""
import hashlib, json
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from airouter.models import AICache

def make_key(kind, prompt, params=None):
    raw = json.dumps({"k": kind, "p": prompt, "x": params or {}}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get(kind, prompt, params=None):
    row = AICache.objects.filter(kind=kind, cache_key=make_key(kind, prompt, params)).first()
    if row is None:
        return None
    ttl_h = getattr(settings, "AI_CACHE_TTL_HOURS", {}).get(kind, 24)
    if ttl_h and ttl_h > 0 and row.created_at < timezone.now() - timedelta(hours=ttl_h):
        return None  # expired: caller regenerates and refreshes the row
    return row

def put(kind, prompt, provider, model, params=None, text="", image=None):
    obj, _ = AICache.objects.update_or_create(
        kind=kind, cache_key=make_key(kind, prompt, params),
        defaults={"provider": provider, "model": model, "text_result": text or "", "image_result": image})
    return obj
