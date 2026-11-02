"""Text providers for the AI Router. Contract: fn(prompt) ->
{"ok": bool, "content": str|None, "model": str, "reason": str, "tokens": int}
Server-side only; keys come from settings (env) and never reach the frontend.
"""
import urllib.parse
import requests
from django.conf import settings

def _ok(content, model, tokens=0):
    return {"ok": True, "content": content, "model": model, "reason": "", "tokens": tokens}
def _fail(model, reason):
    return {"ok": False, "content": None, "model": model, "reason": str(reason)[:300], "tokens": 0}
def _valid(txt):
    return bool(txt) and 40 < len(txt.strip()) < 4000

def gemini(prompt):
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key: return _fail("gemini-2.0-flash", "no api key configured")
    try:
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                          params={"key": key}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if r.status_code == 429: return _fail("gemini-2.0-flash", "429 rate limited")
        if r.status_code != 200: return _fail("gemini-2.0-flash", f"http {r.status_code}")
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _ok(txt.strip(), "gemini-2.0-flash") if _valid(txt) else _fail("gemini-2.0-flash", "empty/short reply")
    except Exception as e:
        return _fail("gemini-2.0-flash", e)

def _openai_style(base, model, key, prompt):
    if not key: return _fail(model, "no api key configured")
    try:
        r = requests.post(base.rstrip("/") + "/chat/completions",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": model, "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 400, "temperature": 0.5}, timeout=35)
        if r.status_code == 429: return _fail(model, "429 rate limited")
        if r.status_code != 200: return _fail(model, f"http {r.status_code}")
        d = r.json(); txt = d["choices"][0]["message"]["content"]
        tokens = (d.get("usage") or {}).get("total_tokens", 0)
        return _ok(txt.strip(), model, tokens) if _valid(txt) else _fail(model, "empty/short reply")
    except Exception as e:
        return _fail(model, e)

def mistral(prompt):
    return _openai_style("https://api.mistral.ai/v1", "mistral-small-latest", getattr(settings, "MISTRAL_API_KEY", ""), prompt)

def qwen(prompt):
    return _openai_style("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "qwen-plus", getattr(settings, "QWEN_API_KEY", ""), prompt)

def deepseek(prompt):
    return _openai_style("https://api.deepseek.com/v1", "deepseek-chat", getattr(settings, "DEEPSEEK_API_KEY", ""), prompt)

def pollinations_text(prompt):
    try:
        url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt)
        r = requests.get(url, timeout=30, headers={"User-Agent": "NewsHub-AIRouter/1.0"})
        if r.status_code == 429: return _fail("pollinations-text", "429 rate limited")
        if r.status_code != 200: return _fail("pollinations-text", f"http {r.status_code}")
        txt = (r.text or "").strip()
        return _ok(txt, "pollinations-text") if _valid(txt) else _fail("pollinations-text", "empty/short reply")
    except Exception as e:
        return _fail("pollinations-text", e)

# Registry: slug -> (callable, model label). "local" is special: the router
# invokes the caller-supplied local_fn (NewsHub's own composer) for it.
TEXT_PROVIDERS = {
    "gemini": gemini, "mistral": mistral, "qwen": qwen,
    "deepseek": deepseek, "pollinations": pollinations_text,
}

def groq(prompt):
    return _openai_style("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile",
                         getattr(settings, "GROQ_API_KEY", ""), prompt)

def openrouter(prompt):
    # Zero-billing: ONLY ':free' models are ever requested from OpenRouter.
    return _openai_style("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free",
                         getattr(settings, "OPENROUTER_API_KEY", ""), prompt)

def cloudflare(prompt):
    acct = getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
    token = getattr(settings, "CLOUDFLARE_API_TOKEN", "")
    if not acct or not token:
        return _fail("@cf/meta/llama-3.1-8b-instruct", "no api key configured")
    return _openai_style(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/v1",
                         "@cf/meta/llama-3.1-8b-instruct", token, prompt)

def huggingface_text(prompt):
    token = getattr(settings, "HUGGINGFACE_API_KEY", "") or getattr(settings, "HF_TOKEN", "")
    return _openai_style("https://router.huggingface.co/v1", "meta-llama/Llama-3.1-8B-Instruct",
                         token, prompt)

def nvidia(prompt):
    return _openai_style("https://integrate.api.nvidia.com/v1", "meta/llama-3.1-70b-instruct",
                         getattr(settings, "NVIDIA_API_KEY", ""), prompt)

TEXT_PROVIDERS.update({
    "groq": groq, "openrouter": openrouter, "cloudflare": cloudflare,
    "huggingface": huggingface_text, "nvidia": nvidia,
})
