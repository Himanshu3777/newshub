from news.models import NewsArticle
from news.services import title_similarity
from verification.models import VerificationReport, VerificationEvidence
from verification.services import extract_claims, google_factcheck, score_verification

def verify_article(article):
    claims=extract_claims(article.title, article.summary)
    results=[]
    for claim in claims:
        factchecks, api_status = google_factcheck(claim)
        # related coverage: similar titles from OTHER publishers
        related=0
        for other in NewsArticle.objects.exclude(id=article.id).exclude(source=article.source).order_by("-published_at")[:300]:
            if title_similarity(article.title, other.title) >= 0.55: related+=1
        status, conf, summary = score_verification(article, factchecks, related)
        report=VerificationReport.objects.create(article=article,claim=claim,search_query=claim,status=status,confidence_score=conf,summary=f"{summary} [FactCheck API: {api_status}]")
        for fc in factchecks:
            VerificationEvidence.objects.create(report=report,title=fc.get("title","")[:500],url=fc.get("url",""),publisher=fc.get("publisher",""),kind="factcheck",snippet=fc.get("snippet","")[:800],rating=fc.get("rating",""))
        results.append({"claim":claim,"status":status,"confidence":conf})
    # Cross-confirmation: another publisher independently covering this claim
    # removes the 'not confirmed' source note (NewsHub methodology step).
    others=0
    for o in NewsArticle.objects.exclude(id=article.id).exclude(source=article.source).order_by("-published_at")[:300]:
        if title_similarity(article.title, o.title) >= 0.55: others+=1
    if article.is_unconfirmed and others>=1:
        article.is_unconfirmed=False; article.source_note=""; article.save(update_fields=["is_unconfirmed","source_note"])
    if results:
        best=max(results,key=lambda r:r["confidence"])
        article.verification_status=best["status"]; article.confidence_score=best["confidence"]; article.save(update_fields=["verification_status","confidence_score"])
    return results
