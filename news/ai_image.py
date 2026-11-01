"""AI cover photos for NewsHub - now routed through the AI Router.

The router (airouter app) runs the quota-aware image chain for realistic
news photos: Pollinations FLUX -> Gemini Image -> HuggingFace FLUX ->
Ideogram, with per-provider daily limits, health/cooldown and caching.
When every external provider is unavailable it returns (None, None) and the
caller keeps the code-drawn SVG illustration - a story NEVER has no cover.

build_prompt is kept here because airouter.providers_image reuses it.
"""
import logging, re
log = logging.getLogger("newshub.ai_image")
STOP = {"the", "and", "for", "with", "from", "that", "this", "will", "over", "after", "before", "says", "said", "news", "live", "update", "updates"}

def build_prompt(article):
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", article.title or "") if w.lower() not in STOP][:8]
    topic = " ".join(words) or "current events"
    cat = article.category.name if article.category else "News"
    return ("editorial news photograph style illustration, " + cat.lower() + " story: " + topic +
            ", realistic, dramatic natural lighting, indian context where relevant, "
            "no text, no words, no letters, no watermark, no logo")

def fetch_ai_cover(article):
    """Return (jpeg_bytes, provider_name) via the AI Router, or (None, None)."""
    try:
        from airouter.router import generate_image
        res = generate_image(build_prompt(article), image_type="news_photo", seed=article.id or 7)
        if res.get("success") and res.get("provider") != "svg" and isinstance(res.get("content"), (bytes, bytearray)):
            return bytes(res["content"]), res["provider"]
    except Exception as e:
        log.warning("AI router cover failed for article %s: %s", article.id, e)
    return None, None
