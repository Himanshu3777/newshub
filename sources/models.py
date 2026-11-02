from django.db import models
class NewsSource(models.Model):
    name=models.CharField(max_length=120,unique=True)
    slug=models.SlugField(unique=True)
    website=models.URLField()
    feed_url=models.URLField(help_text="Official RSS feed URL")
    feed_type=models.CharField(max_length=20,default="rss",choices=[("rss","RSS"),("api","API")])
    language=models.CharField(max_length=10,default="en",choices=[("en","English"),("hi","Hindi"),("mixed","Mixed")])
    country=models.CharField(max_length=60,default="India")
    credibility_score=models.FloatField(default=70.0,help_text="0-100 editorial prior, not a truth score")
    is_active=models.BooleanField(default=True)
    fetch_interval_minutes=models.PositiveIntegerField(default=60)
    last_fetched_at=models.DateTimeField(null=True,blank=True)
    feed_etag=models.CharField(max_length=200,blank=True,default="")
    feed_last_modified=models.CharField(max_length=120,blank=True,default="")
    last_status=models.CharField(max_length=50,blank=True,default="")
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["name"]
    def __str__(self): return self.name

class FetchingLog(models.Model):
    source=models.ForeignKey(NewsSource,on_delete=models.CASCADE,related_name="fetch_logs")
    started_at=models.DateTimeField(auto_now_add=True); finished_at=models.DateTimeField(null=True,blank=True)
    status=models.CharField(max_length=20,default="running",choices=[("running","Running"),("success","Success"),("partial","Partial"),("failed","Failed")])
    fetched=models.PositiveIntegerField(default=0); created=models.PositiveIntegerField(default=0)
    duplicates=models.PositiveIntegerField(default=0); errors=models.TextField(blank=True)
    class Meta: ordering=["-started_at"]
    def __str__(self): return f"{self.source.name} {self.status} {self.started_at:%Y-%m-%d %H:%M}"
