"""Original content generation - the copyright-safe core of NewsHub.

We never display the publisher's article text or photos. Facts and headlines
are not copyrightable expression; from them we write our OWN brief and draw
our OWN cover illustration.

Brief providers:
- "gemini" if GEMINI_API_KEY is set: an LLM writes an original brief from the
  headline + extracted facts only (the publisher's text is never sent for
  copying; the prompt forbids reproducing it).
- "local" (default): a deterministic composer that builds an original brief
  from headline structure, entities, numbers, category and source attribution.
"""
import hashlib, html, re, requests
from django.conf import settings
from news.services import extract_entities, extract_keywords

OPENERS=[
 "{lead} The development was reported by {source} on {date}.",
 "{lead} {source} reported this development on {date}.",
 "{lead} This report comes from {source}, published on {date}.",
]
def _lead_from_title(title):
    t=title.strip().rstrip(".")
    # Turn a headline into a plain factual sentence without copying any article body.
    t=re.sub(r"\s*\|\s*(live|updates?).*$","",t,flags=re.I)
    return t[0].upper()+t[1:] if t else t

def local_brief(title, summary_internal, source_name, category_name, published_str, article_seed=0):
    lead=_lead_from_title(title)
    opener=OPENERS[article_seed % len(OPENERS)].format(lead=lead, source=source_name, date=published_str)
    facts=[]
    nums=re.findall(r"(?:₹|Rs\.?\s*)?[\d][\d,\.]*\s*(?:crore|lakh|%|km|kg|people|students|seats)?", f"{title} {summary_internal}")
    ents=[n for n,_ in extract_entities(f"{title} {summary_internal}")][:3]
    kws=extract_keywords(f"{title} {summary_internal}",4)
    if ents: facts.append(f"Key names in the report include {', '.join(ents)}.")
    if nums:
        clean=[n.strip() for n in nums if len(n.strip())>1][:3]
        if clean: facts.append(f"Figures mentioned in the headline report: {', '.join(clean)}.")
    mid=""
    if category_name: mid=f" Filed under {category_name}, this is a developing report in that area."
    tail=" NewsHub writes this brief from the headline and public facts only and does not reproduce the publisher's text. Read the complete story at the original publisher, linked below."
    return (opener + " " + " ".join(facts) + mid + tail).strip()

def gemini_brief(title, facts_text, source_name):
    key=getattr(settings,"GEMINI_API_KEY","")
    if not key: return None
    prompt=(f"Write an original 2-3 sentence news brief in your own words from this headline and facts only. "
            f"Do NOT copy or closely paraphrase any article text. Headline: {title}. Facts: {facts_text}. "
            f"End with: 'Reported by {source_name}.'")
    try:
        r=requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            params={"key":key}, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
        if r.status_code==200:
            txt=r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if 40<len(txt)<1200: return txt
    except Exception:
        pass
    return None

def generate_brief(article):
    published_str=article.published_at.strftime("%d %B %Y")
    facts_text=f"Entities: {[n for n,_ in extract_entities(article.title+' '+article.summary)]}; Keywords: {extract_keywords(article.title+' '+article.summary,6)}; Figures: {re.findall(r'[0-9][0-9,\.]*', article.title+' '+article.summary)[:5]}"
    brief=gemini_brief(article.title, facts_text, article.source.name)
    provider="gemini" if brief else "local"
    if not brief:
        brief=local_brief(article.title, article.summary, article.source.name,
                          article.category.name if article.category else "", published_str, article_seed=article.id or 0)
    return brief, provider

# ---------- Original cover illustration (SVG, generated per article) ----------
PALETTES={
 "Politics":("#1e3a8a","#e3b341"),"Technology":("#0f766e","#5eead4"),"Business":("#7c2d12","#fdba74"),
 "Sports":("#166534","#86efac"),"Entertainment":("#86198f","#f0abfc"),"Health":("#9f1239","#fda4af"),
 "Science":("#155e75","#67e8f9"),"Education":("#3730a3","#a5b4fc"),"Crime":("#7f1d1d","#fca5a5"),
 "Environment":("#14532d","#4ade80"),"International":("#1e40af","#93c5fd"),"National":("#854d0e","#fde047"),
 "Breaking News":("#991b1b","#fecaca"),
}
def cover_svg(article):
    cat=article.category.name if article.category else "National"
    bg,fg=PALETTES.get(cat,("#1e3a8a","#e3b341"))
    words=[w for w in re.findall(r"[A-Za-z\u0900-\u097F]{3,}", article.title) if w.lower() not in ("the","and","for","with","from")][:3]
    lines=[]
    y=120
    for w in words:
        lines.append(f'<text x="40" y="{y}" font-family="Georgia,serif" font-size="54" font-weight="700" fill="#ffffff">{html.escape(w)}</text>'); y+=62
    seed=int(hashlib.md5(article.source_url.encode()).hexdigest()[:4],16)
    circles="".join(f'<circle cx="{(seed*(i+3))%760+40}" cy="{(seed*(i+7))%180+20}" r="{18+i*9}" fill="{fg}" opacity="0.14"/>' for i in range(4))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420" viewBox="0 0 800 420">
<rect width="800" height="420" fill="{bg}"/>{circles}
<text x="40" y="52" font-family="Arial" font-size="19" letter-spacing="4" fill="{fg}">{html.escape(cat.upper())}</text>
{''.join(lines)}
<rect x="40" y="330" width="52" height="52" rx="26" fill="{fg}"/>
<text x="66" y="365" font-family="Arial" font-size="19" font-weight="800" fill="#14100a" text-anchor="middle">NV</text>
<text x="106" y="356" font-family="Georgia,serif" font-size="24" fill="#ffffff">NewsHub</text>
<text x="106" y="380" font-family="Arial" font-size="13" fill="#ffffff" opacity="0.75">AI ILLUSTRATION · {html.escape(article.source.name)}</text>
</svg>'''
