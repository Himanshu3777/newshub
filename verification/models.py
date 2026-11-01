from django.db import models
class VerificationReport(models.Model):
    STATUS=[("verified","Verified"),("partially_verified","Partially Verified"),("disputed","Disputed"),("misleading","Misleading"),("false","False"),("unverified","Unverified"),("needs_review","Needs Human Review")]
    article=models.ForeignKey("news.NewsArticle",on_delete=models.CASCADE,related_name="verification_reports")
    claim=models.TextField()
    search_query=models.CharField(max_length=500,blank=True)
    status=models.CharField(max_length=30,choices=STATUS,default="unverified")
    confidence_score=models.FloatField(default=0.0)
    method=models.CharField(max_length=120,default="heuristic+factcheck-api",help_text="Automated assessment, not independently confirmed fact")
    summary=models.TextField(blank=True)
    reviewed_by_human=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.article.title[:40]} - {self.status}"

class VerificationEvidence(models.Model):
    KIND=[("supporting","Supporting"),("contradicting","Contradicting"),("neutral","Neutral"),("factcheck","Fact-check")]
    report=models.ForeignKey(VerificationReport,on_delete=models.CASCADE,related_name="evidence")
    title=models.CharField(max_length=500,blank=True); url=models.URLField(max_length=1000)
    publisher=models.CharField(max_length=200,blank=True); published_at=models.DateTimeField(null=True,blank=True)
    kind=models.CharField(max_length=20,choices=KIND,default="neutral"); snippet=models.TextField(blank=True)
    rating=models.CharField(max_length=120,blank=True,help_text="Fact-check rating e.g. from Google Fact Check API")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return self.url[:80]

class ClaimSubmission(models.Model):
    """A social-media claim a user asked us to check. NEVER published as news."""
    PLATFORMS=[("instagram","Instagram"),("whatsapp","WhatsApp"),("facebook","Facebook"),("x","X / Twitter"),("youtube","YouTube"),("other","Other")]
    RESULTS=[("confirmed","Confirmed by publisher"),("not_confirmed","Not confirmed"),("contradicted","Contradicted / Fake"),("checking","Checking")]
    platform=models.CharField(max_length=20,choices=PLATFORMS,default="other")
    claim_text=models.TextField()
    source_url=models.URLField(blank=True)
    result=models.CharField(max_length=20,choices=RESULTS,default="checking")
    result_note=models.TextField(blank=True)
    matched_article=models.ForeignKey("news.NewsArticle",on_delete=models.SET_NULL,null=True,blank=True,related_name="matched_claims")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"Claim {self.id}: {self.claim_text[:50]}"
