"""Check-a-Claim: a user pastes a social media post / WhatsApp forward.
We check it against (1) Google Fact Check API, (2) our own collected publisher
news. The submission is NEVER turned into a news article. Fake/contradicted
claims are flagged so the user gets the actual picture."""
import re
from news.models import NewsArticle
from news.services import title_similarity, extract_keywords
from verification.services import google_factcheck
from verification.models import ClaimSubmission

def check_claim(text, platform="other", url=""):
    sub=ClaimSubmission.objects.create(platform=platform, claim_text=text[:2000], source_url=url or "")
    factchecks, api_status = google_factcheck(text[:200])
    for fc in factchecks:
        rating=(fc.get("rating") or "").lower()
        if any(w in rating for w in ["false","incorrect","misleading","fake"]):
            sub.result="contradicted"; sub.result_note=f"A fact-check by {fc.get('publisher') or 'a fact-checker'} rates this claim: {fc.get('rating')}. Do not forward it as news."
            sub.save(); return sub
        if any(w in rating for w in ["true","correct"]):
            sub.result="confirmed"; sub.result_note=f"A fact-check by {fc.get('publisher') or 'a fact-checker'} rates this claim: {fc.get('rating')}."
            sub.save(); return sub
    # Match against collected publisher news by keyword overlap + similarity
    kws=set(extract_keywords(text,10))
    best=None; best_score=0
    for art in NewsArticle.objects.exclude(verification_status__in=["false","misleading","disputed"]).select_related("source").order_by("-published_at")[:400]:
        overlap=len(kws & set(extract_keywords(art.title+" "+art.summary,12)))
        sim=title_similarity(text, art.title)
        score=overlap + (3 if sim>=0.4 else 0)
        if score>best_score: best_score=score; best=art
    if best is not None and best_score>=3:
        sub.result="confirmed"; sub.matched_article=best
        sub.result_note=f"This claim matches reporting by {best.source.name}: '{best.title}'. Read the original at the publisher link on the matched story."
    else:
        sub.result="not_confirmed"
        sub.result_note="No publisher in our collection and no fact-check has confirmed this claim yet. Treat it as unconfirmed - do not share it as fact. If a publisher confirms it later, it will appear in our news with the source note removed."
    sub.save(); return sub
