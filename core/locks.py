import socket
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from core.models import SystemLock

def acquire_lock(name, stale_minutes=45):
    now=timezone.now(); owner=f"{socket.gethostname()}"
    try:
        with transaction.atomic():
            lock,created=SystemLock.objects.select_for_update().get_or_create(
                name=name, defaults={"acquired_at":now,"owner":owner})
            if created: return True
            if lock.acquired_at <= now-timedelta(minutes=stale_minutes):
                lock.acquired_at=now; lock.owner=owner; lock.save(update_fields=["acquired_at","owner"])
                return True
            return False
    except Exception:
        return False

def release_lock(name):
    SystemLock.objects.filter(name=name).delete()
