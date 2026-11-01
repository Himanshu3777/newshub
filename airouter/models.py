from django.db import models

class ProviderUsage(models.Model):
    """Daily request counter per provider+kind. A new row per day (Asia/Kolkata)
    means the quota resets itself every morning - no manual reset, ever."""
    date=models.DateField(db_index=True)
    provider=models.CharField(max_length=40,db_index=True)
    kind=models.CharField(max_length=10,choices=[("text","Text"),("image","Image")])
    used=models.PositiveIntegerField(default=0)
    class Meta:
        unique_together=[("date","provider","kind")]
    def __str__(self): return f"{self.date} {self.provider}/{self.kind}: {self.used}"

class ProviderState(models.Model):
    """Live health of a provider: status + cooldown after repeated failures."""
    STATUS=[("available","Available"),("rate_limited","Rate Limited"),("quota_exhausted","Quota Exhausted"),
            ("error","Error"),("disabled","Disabled"),("cooldown","Cooldown")]
    provider=models.CharField(max_length=40,unique=True)
    status=models.CharField(max_length=20,choices=STATUS,default="available")
    cooldown_until=models.DateTimeField(null=True,blank=True)
    consecutive_failures=models.PositiveIntegerField(default=0)
    last_error=models.CharField(max_length=300,blank=True)
    last_success_at=models.DateTimeField(null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.provider}: {self.status}"

class AICache(models.Model):
    """Generated results cached by a hash of prompt+model+params. A repeat
    request returns the cached row and consumes ZERO provider quota."""
    kind=models.CharField(max_length=10,choices=[("text","Text"),("image","Image")],db_index=True)
    cache_key=models.CharField(max_length=64,unique=True,db_index=True)
    provider=models.CharField(max_length=40)
    model=models.CharField(max_length=80,blank=True)
    text_result=models.TextField(blank=True)
    image_result=models.BinaryField(blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.kind}:{self.cache_key[:10]} via {self.provider}"

class AIGenerationLog(models.Model):
    """One row per generation attempt (success or failure) - the audit trail
    behind the /ai/ monitoring dashboard."""
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    request_type=models.CharField(max_length=10,choices=[("text","Text"),("image","Image")])
    request_class=models.CharField(max_length=20,blank=True)
    provider=models.CharField(max_length=40)
    model=models.CharField(max_length=80,blank=True)
    success=models.BooleanField(default=False)
    failure_reason=models.CharField(max_length=300,blank=True)
    response_ms=models.PositiveIntegerField(default=0)
    tokens_used=models.PositiveIntegerField(default=0)
    quota_remaining=models.IntegerField(default=-1)
    fallback_used=models.BooleanField(default=False)
    cached=models.BooleanField(default=False)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.created_at:%H:%M} {self.request_type} {self.provider} {'OK' if self.success else 'FAIL'}"
