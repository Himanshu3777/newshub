from django.db import models
from django.contrib.auth.models import User
class SensitiveContentFinding(models.Model):
    SEV=[("low","Low"),("medium","Medium"),("high","High"),("critical","Critical")]
    article=models.ForeignKey("news.NewsArticle",on_delete=models.CASCADE,related_name="sensitive_findings")
    finding_type=models.CharField(max_length=60,help_text="phone/email/aadhaar_like/pan/bank/minor/private_allegation")
    matched_text_masked=models.CharField(max_length=200,help_text="Masked only - raw PII is never stored")
    severity=models.CharField(max_length=20,choices=SEV,default="low")
    needs_human_review=models.BooleanField(default=False)
    reviewed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.finding_type} {self.severity}"

class AuditLog(models.Model):
    actor=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=200); object_type=models.CharField(max_length=100,blank=True); object_id=models.CharField(max_length=50,blank=True)
    details=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.action} {self.created_at:%Y-%m-%d}"
