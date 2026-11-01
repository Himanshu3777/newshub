"""AI cover photos for NewsHub - a provider CHAIN, ordered by free headroom.

1. pollinations : Pollinations FLUX - free, no key at all.
2. huggingface  : FLUX.1-schnell via HF Inference API - free token (HF_TOKEN).
3. gemini       : Gemini image generation - free tier of the Gemini key.
Final fallback is NOT in this module: when every provider fails, the caller
keeps the code-drawn SVG illustration, so a story NEVER ends up without a
cover - the same guarantee the text chain gives for briefs.

Images are generated from headline topic + category only (never from a
publisher photo), so every cover is an original NewsHub asset. Generated
bytes are stored on the article (cover_jpeg): generated exactly once.
"""
import base64, logging, re, urllib.parse
import requests
from django.conf import settings

log = logging.getLogger("newshub.ai_image")
STOP = {"the", "and", "for", "with", "from", "that", "this", "will", "over", "after", "before", "says", "said", "news", "live", "update", "updates"}


def build_prompt(article):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", article.title or "") if w.lower() not in STOP][:8]
    topic = " ".join(words) or "current events"
    cat = article.category.name if article.category else "News"
    return ("editorial news photograph style illustration, " + cat.lower() + " story: " + topic +
            ", realistic, dramatic natural lighting, indian context where relevant, "
            "no text, no words, no letters, no watermark, no logo")


def _valid_jpeg(data):
    return bool(data) and len(data) > 8000 and data[:2] == b"\xff\xd8"


def _pollinations(article, prompt):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           "?width=1200&height=630&nologo=true&model=flux&seed=" + str(article.id or 7))
    r = requests.get(url, timeout=75, headers={"User-Agent": "NewsHub/1.0 (cover generator)"})
    if r.status_code == 200 and _valid_jpeg(r.content):
        return r.content
    return None


def _huggingface(article, prompt):
    token = getattr(settings, "HF_TOKEN", "")
    if not token:
        return None
    r = requests.post("https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json={"inputs": prompt}, timeout=90)
    if r.status_code == 200 and _valid_jpeg(r.content):
        return r.content
    return None


def _gemini_image(article, prompt):
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        return None
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent",
                      params={"key": key},
                      json={"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"responseModalities": ["IMAGE"]}}, timeout=90)
    if r.status_code == 200:
        parts = r.json()["candidates"][0]["content"]["parts"]
        for p in parts:
            inline = p.get("inlineData") or {}
            if inline.get("data"):
                data = base64.b64decode(inline["data"])
                if _valid_jpeg(data):
                    return data
    return None


# Photo provider chain, ordered by free-request headroom (most generous first).
IMAGE_PROVIDERS = [("pollinations", _pollinations), ("huggingface", _huggingface), ("gemini", _gemini_image)]


def fetch_ai_cover(article):
    """Try each provider in order. Return (jpeg_bytes, provider_name) or (None, None)."""
    prompt = build_prompt(article)
    for name, fn in IMAGE_PROVIDERS:
        try:
            data = fn(article, prompt)
            if data:
                return data, name
        except Exception as e:
            log.warning("AI cover provider %s failed for article %s: %s", name, article.id, e)
    return None, None
