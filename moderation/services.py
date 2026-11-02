"""Phase 8: Sensitive content detection. Raw PII is NEVER stored - only masked."""
import re
PATTERNS=[
 ("phone", re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}"), "high"),
 ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "medium"),
 ("aadhaar_like", re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "critical"),
 ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "high"),
 ("bank_account", re.compile(r"\b\d{11,18}\b"), "high"),
]
KEYWORDS=[
 ("minor_private", ["minor girl","minor boy","schoolgirl","schoolboy","underage"], "critical"),
 ("private_allegation", ["allegedly raped","sexual assault victim name","victim identified as"], "high"),
]
def mask(text):
    if len(text)<=4: return "****"
    return text[:2]+"*"*(len(text)-4)+text[-2:]
def mask_pii_in_text(text):
    """Mask every PII occurrence INSIDE a longer text, leaving the rest of
    the text intact. (mask() alone is for a single matched token - applying
    it to a whole document would destroy the document.)"""
    t=text or ""
    for _name,pat,_sev in PATTERNS:
        t=pat.sub(lambda m: mask(m.group(0)), t)
    return t

def detect_sensitive(text):
    findings=[]; t=text or ""
    for name,pat,sev in PATTERNS:
        for m in pat.finditer(t):
            # bank pattern overlaps aadhaar/phone - skip if already covered length
            findings.append({"type":name,"masked":mask(m.group(0)),"severity":sev,"needs_review":sev in ("high","critical")})
    low=t.lower()
    for name,words,sev in KEYWORDS:
        if any(w in low for w in words):
            findings.append({"type":name,"masked":"[keyword match - text withheld]","severity":sev,"needs_review":True})
    return findings
