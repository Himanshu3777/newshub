"""Phase 7: Cleaning, language, keywords, entities, category classification + dedup."""
import re, html, unicodedata, hashlib
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

CATEGORY_KEYWORDS={
 "Politics":["election","parliament","minister","bjp","congress","modi","government","vote","assembly","lok sabha"],
 "Technology":["technology","ai","artificial intelligence","software","smartphone","startup","cyber","data","internet"],
 "Business":["market","sensex","nifty","economy","gdp","bank","trade","stock","business","finance","rupee"],
 "Education":["exam","university","student","school","education","cbse","upsc","admission","result"],
 "Sports":["cricket","football","match","ipl","olympic","player","tournament","hockey","tennis"],
 "Entertainment":["film","movie","bollywood","actor","music","web series","celebrity"],
 "Science":["science","isro","space","research","scientist","nasa","climate study","discovery"],
 "Health":["health","hospital","doctor","disease","vaccine","medical","covid","cancer"],
 "International":["world","global","us ","china","russia","ukraine","united nations","international"],
 "National":["india","delhi","mumbai","state","national"],
 "Crime":["police","arrest","crime","murder","theft","court","fir","accused"],
 "Environment":["climate","pollution","environment","forest","rain","flood","cyclone","earthquake"],
 "Breaking News":["breaking","urgent","just in","live update"],
}
STOP=set("the a an and or of to in is are was were for on with as by at from that this it its be has have had will would can could should may might".split())

def clean_html(text):
    if not text: return ""
    soup=BeautifulSoup(text,"html.parser")
    return html.unescape(soup.get_text(" ",strip=True))

def normalize_text(text):
    t=unicodedata.normalize("NFKC", clean_html(text or ""))
    return re.sub(r"\s+"," ",t).strip()

def normalize_title(title):
    t=normalize_text(title).lower()
    t=re.sub(r"[^a-z0-9\u0900-\u097F ]","",t)
    return re.sub(r"\s+"," ",t).strip()

def detect_language(text):
    if re.search(r"[\u0900-\u097F]", text or ""): return "hi"
    return "en"

def extract_keywords(text, limit=8):
    words=re.findall(r"[A-Za-z\u0900-\u097F]{4,}", (text or "").lower())
    freq={}
    for w in words:
        if w not in STOP: freq[w]=freq.get(w,0)+1
    return [w for w,_ in sorted(freq.items(),key=lambda x:-x[1])[:limit]]

def extract_entities(text):
    """Lightweight NER: capitalized sequences + known org suffixes. Honest heuristic, not ML NER."""
    ents=[]
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text or ""):
        name=m.group(1).strip()
        if name.lower() in STOP or len(name)<3: continue
        typ="org" if any(s in name for s in ["India","Bank","University","Court","Government","Police","Board"]) else "person"
        if name not in [e[0] for e in ents]: ents.append((name,typ))
    return ents[:12]

def classify_category(title, summary="", feed_hint=""):
    text=f"{title} {summary}".lower()
    scores={cat:sum(1 for kw in kws if kw in text) for cat,kws in CATEGORY_KEYWORDS.items()}
    best=max(scores, key=scores.get)
    if scores[best]>0: return best
    return feed_hint if feed_hint in CATEGORY_KEYWORDS else "National"

def fingerprint(title, url=""):
    return hashlib.sha256(f"{normalize_title(title)}|{url}".encode()).hexdigest()

def title_similarity(a,b):
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()

def is_duplicate_candidate(new_title, existing_titles, threshold=0.92):
    for t in existing_titles:
        if title_similarity(new_title,t)>=threshold: return True, t
    return False, None

# --- Social / viral claim detection (NewsHub source-note system) ---
SOCIAL_PATTERNS=[
 (r"viral (video|clip|post|photo|reel|message)", "viral social media post"),
 (r"instagram (video|reel|post)", "viral Instagram video"),
 (r"whatsapp (forward|message|video)", "viral WhatsApp forward"),
 (r"facebook (post|video)", "viral Facebook post"),
 (r"social media (post|video|claim|rumou?r)", "social media post"),
 (r"video going viral|clip going viral|going viral on", "viral social media video"),
 (r"सोशल मीडिया|वायरल", "viral social media post"),
]
def detect_social_origin(title, summary=""):
    """Returns (platform_desc, note) if the story's claim originates from a viral/social
    source, else (None, ''). A news report ABOUT a viral video (e.g. police response)
    still counts: readers must know the underlying claim is not confirmed."""
    text=f"{title} {summary}".lower()
    for pat, desc in SOCIAL_PATTERNS:
        if re.search(pat, text):
            note=f"According to a {desc}, but this has not been confirmed."
            return desc, note
    return None, ""
