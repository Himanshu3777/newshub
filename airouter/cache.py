"""Hash-based result cache (spec 9). Same prompt+kind+params -> same key ->
cached result, zero provider quota consumed."""
import hashlib, json
from airouter.models import AICache

def make_key(kind, prompt, params=None):
    raw = json.dumps({"k": kind, "p": prompt, "x": params or {}}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get(kind, prompt, params=None):
    return AICache.objects.filter(kind=kind, cache_key=make_key(kind, prompt, params)).first()

def put(kind, prompt, provider, model, params=None, text="", image=None):
    obj, _ = AICache.objects.update_or_create(
        kind=kind, cache_key=make_key(kind, prompt, params),
        defaults={"provider": provider, "model": model, "text_result": text or "", "image_result": image})
    return obj
