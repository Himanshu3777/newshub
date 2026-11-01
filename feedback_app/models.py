from django.db import models
class UserFeedback(models.Model):
    name=models.CharField(max_length=120); email=models.EmailField(); message=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True); is_resolved=models.BooleanField(default=False)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"Feedback {self.name}"
class CorrectionRequest(models.Model):
    STATUS=[("pending","Pending"),("accepted","Accepted"),("rejected","Rejected")]
    article=models.ForeignKey("news.NewsArticle",on_delete=models.SET_NULL,null=True,blank=True,related_name="corrections")
    article_url=models.URLField(blank=True); name=models.CharField(max_length=120); email=models.EmailField()
    description=models.TextField(); status=models.CharField(max_length=20,choices=STATUS,default="pending")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"Correction {self.id} {self.status}"
