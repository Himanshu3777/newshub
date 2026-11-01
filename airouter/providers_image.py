"""Image providers for the AI Router. Contract: fn(prompt, seed) ->
{"ok": bool, "content": jpeg bytes|None, "model": str, "reason": str}
"""
import base64
import requests
from django.conf import settings
from news.ai_image import build_prompt  # noqa: F401  (shared prompt builder, reused)

def _ok(data, model): return {"ok": True, "content": data, "model": model, "reason": ""}
def _fail(model, reason): return {"ok": False, "content": None, "model": model, "reason": str(reason)[:300]}
def _valid_jpeg(data): return bool(data) and len(data) > 8000 and data[:2] == b"\xff\xd8"

def pollinations(prompt, seed=7):
    import urllib.parse
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           "?width=1200&height=630&nologo=true&model=flux&seed=" + str(seed))
    try:
        r = requests.get(url, timeout=75, headers={"User-Agent": "NewsHub-AIRouter/1.0"})
        if r.status_code == 429: return _fail("flux", "429 rate limited")
        if r.status_code == 200 and _valid_jpeg(r.content): return _ok(r.content, "flux")
        return _fail("flux", f"http {r.status_code} bytes {len(r.content or b'')}")
    except Exception as e:
        return _fail("flux", e)

def gemini_image(prompt, seed=7):
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key: return _fail("gemini-image", "no api key configured")
    try:
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent",
                          params={"key": key},
                          json={"contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"responseModalities": ["IMAGE"]}}, timeout=90)
        if r.status_code == 429: return _fail("gemini-image", "429 rate limited")
        if r.status_code != 200: return _fail("gemini-image", f"http {r.status_code}")
        for p in r.json()["candidates"][0]["content"]["parts"]:
            inline = p.get("inlineData") or {}
            if inline.get("data"):
                data = base64.b64decode(inline["data"])
                if _valid_jpeg(data): return _ok(data, "gemini-image")
        return _fail("gemini-image", "no image in response")
    except Exception as e:
        return _fail("gemini-image", e)

def huggingface(prompt, seed=7):
    token = getattr(settings, "HUGGINGFACE_API_KEY", "") or getattr(settings, "HF_TOKEN", "")
    if not token: return _fail("FLUX.1-schnell", "no api key configured")
    try:
        r = requests.post("https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json={"inputs": prompt}, timeout=90)
        if r.status_code == 429: return _fail("FLUX.1-schnell", "429 rate limited")
        if r.status_code == 200 and _valid_jpeg(r.content): return _ok(r.content, "FLUX.1-schnell")
        return _fail("FLUX.1-schnell", f"http {r.status_code}")
    except Exception as e:
        return _fail("FLUX.1-schnell", e)

def ideogram(prompt, seed=7):
    key = getattr(settings, "IDEOGRAM_API_KEY", "")
    if not key: return _fail("ideogram-v2", "no api key configured")
    try:
        r = requests.post("https://api.ideogram.ai/generate",
                          headers={"Api-Key": key, "Content-Type": "application/json"},
                          json={"image_request": {"prompt": prompt, "aspect_ratio": "ASPECT_16_9",
                                                   "model": "V_2", "magic_prompt_option": "AUTO"}}, timeout=90)
        if r.status_code == 429: return _fail("ideogram-v2", "429 rate limited")
        if r.status_code != 200: return _fail("ideogram-v2", f"http {r.status_code}")
        url = r.json()["data"][0]["url"]
        img = requests.get(url, timeout=60)
        if img.status_code == 200 and _valid_jpeg(img.content): return _ok(img.content, "ideogram-v2")
        return _fail("ideogram-v2", "image download failed")
    except Exception as e:
        return _fail("ideogram-v2", e)

IMAGE_PROVIDERS = {
    "pollinations": pollinations, "gemini": gemini_image,
    "huggingface": huggingface, "ideogram": ideogram,
}
