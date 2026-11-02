from django.db import models

class SystemLock(models.Model):
    """DB-backed named lock so only one background job (RSS fetch) runs at a
    time across the cron service, the local fetch loop and manual commands.
    A lock older than the stale window is treated as abandoned (crashed run)
    and can be taken over."""
    name=models.CharField(max_length=60,unique=True)
    owner=models.CharField(max_length=80,blank=True)
    acquired_at=models.DateTimeField()
    class Meta: app_label="core"
    def __str__(self): return f"lock {self.name} since {self.acquired_at}"
