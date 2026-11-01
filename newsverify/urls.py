from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
def health(request): return JsonResponse({"status":"ok","service":"NewsVerify AI"})
urlpatterns=[path("admin/",admin.site.urls),path("health/",health,name="health"),path("api/",include("api.urls")),path("",include("core.urls")),path("",include("news.urls")),path("ai/",include("airouter.urls"))]
