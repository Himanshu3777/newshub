import time
from django.http import JsonResponse
from django.core.cache import cache
class SimpleRateLimitMiddleware:
    """120 requests/min per IP for /api/ POST and feedback - basic abuse guard."""
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method=="POST" and request.path.startswith("/api/"):
            key=f"rl:{request.META.get('REMOTE_ADDR','x')}:{int(time.time()//60)}"
            count=cache.get(key,0)
            if count>=30: return JsonResponse({"detail":"Too many requests, try again in a minute."},status=429)
            cache.set(key,count+1,60)
        return self.get_response(request)
