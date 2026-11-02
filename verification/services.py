"""Phase 9: Verification engine.
Google Fact Check Tools API is evidence, not proof. Without a key, claims stay
Unverified / Needs Human Review. Repetition alone never verifies.

MULTI-SIGNAL RULE (binding): a final status always combines multiple evidence
signals - a published fact-check is only ONE signal, never a truth engine.
- Fact-check says false/incorrect/misleading -> False / Misleading.
- Fact-check says true/correct -> Verified ONLY when at least one independent
  publisher in our own collection also covers the story (related_count >= 1).
  A lone true fact-check with no corroboration -> Partially Verified.
- No fact-check -> cross-publisher coverage alone can at most partially
  verify; a single source stays Unverified; no evidence -> Needs Human Review.
"""
import re, requests
from django.conf import settings

def extract_claims(title, summary=""):
    text=f"{title}. {summary}"
    sentences=[s.strip() for s in re.split(r"[.!?]\s+", text) if len(s.strip())>25]
    claims=[]
    for s in sentences:
        if re.search(r"\d|[A-Z][a-z]+\s[A-Z][a-z]+", s): claims.append(s[:500])
    return claims[:3] or [title[:500]]

def google_factcheck(query):
    key=getattr(settings,"GOOGLE_FACTCHECK_API_KEY","")
    if not key: return [], "no_api_key"
    try:
        r=requests.get("https://factchecktools.googleapis.com/v1alpha1/claims:search",params={"query":query,"key":key,"pageSize":5},timeout=10)
        if r.status_code!=200: return [], f"api_{r.status_code}"
        out=[]
        for c in r.json().get("claims",[]):
            for rev in c.get("claimReview",[]):
                out.append({"title":rev.get("title",""),"url":rev.get("url",""),"publisher":(rev.get("publisher") or {}).get("name",""),"rating":rev.get("textualRating",""),"snippet":c.get("text","")})
        return out, "ok"
    except Exception as e:
        return [], f"error:{type(e).__name__}"

def score_verification(article, factchecks, related_count=0):
    """Returns (status, confidence, summary). Conservative by design."""
    if factchecks:
        ratings=" ".join(f.get("rating","").lower() for f in factchecks)
        if any(w in ratings for w in ["false","incorrect","misleading"]):
            return "false" if "false" in ratings else "misleading", 85.0, f"Existing fact-check found with rating: {factchecks[0].get('rating')}"
        if any(w in ratings for w in ["true","correct"]):
            # Multi-signal rule: a published fact-check rating true is one
            # signal only. "Verified" additionally needs independent publisher
            # corroboration inside our own collection (related_count >= 1).
            if related_count>=1:
                return "verified", 90.0, "Existing fact-check rates this claim true/correct."
            return "partially_verified", 70.0, "A published fact-check rates this claim true/correct, but independent corroboration is not yet in our collection. Multi-signal rule: one signal alone does not fully verify."
    if related_count>=2:
        return "partially_verified", 55.0, f"Covered by {related_count} articles in our collection from different publishers. Cross-publisher coverage supports but does not prove the claim - no independent fact-check found."
    if related_count==1:
        return "unverified", 30.0, "Only single-source coverage found so far. Awaiting independent corroboration or fact-check."
    return "needs_review", 15.0, "No independent evidence found automatically. Sent for human review. Automated assessment only - not a confirmed fact."
