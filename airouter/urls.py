from django.urls import path
from airouter import views
urlpatterns = [
    path("", views.dashboard, name="ai_dashboard"),
    path("api/text/", views.api_text, name="ai_api_text"),
]
