from news.models import NewsArticle
from news.services import title_similarity
from verification.models import VerificationReport, VerificationEvidence
from verification.providers import get_search_providers
# Kept importable at module level for backwards compatibility; the live
# evidence path goes through the pluggable providers (verification.providers).
from verification.services import extract_claims, google_factcheck, score_verification

def verify_article(article):
    claims=extract_claims(article.title, article.summary)
    providers=get_search_providers()
    results=[]
    for claim in claims:
        # Gather evidence from ALL enabled search providers. The Fact Check
        # provider is the default; Google CSE is legacy/optional only.
        evidence_items=[]; provider_status={}
        for provider in providers:
            items, pstatus = provider.search(claim)
            provider_status[provider.name]=pstatus
            evidence_items.extend(items)
        # Only fact-check items carry ratings and feed the scoring signals.
        factchecks=[{"title":i.title,"url":i.url,"publisher":i.publisher,"rating":i.rating,"snippet":i.snippet}
                    for i in evidence_items if i.kind=="factcheck"]
        # related coverage: similar titles from OTHER publishers
        related=0
        for other in NewsArticle.objects.exclude(id=article.id).exclude(source=article.source).order_by("-published_at")[:300]:
            if title_similarity(article.title, other.title) >= 0.55: related+=1
        status, conf, summary = score_verification(article, factchecks, related)
        prov_note=", ".join(f"{n}={s}" for n,s in provider_status.items())
        report=VerificationReport.objects.create(article=article,claim=claim,search_query=claim,status=status,confidence_score=conf,summary=f"{summary} [Providers: {prov_note}]")
        for item in evidence_items:
            VerificationEvidence.objects.create(report=report,title=item.title[:500],url=item.url,publisher=item.publisher,kind=item.kind,snippet=item.snippet[:800],rating=item.rating)
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
