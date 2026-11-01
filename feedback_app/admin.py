from django.contrib import admin
from feedback_app.models import UserFeedback, CorrectionRequest
@admin.register(UserFeedback)
class FAdmin(admin.ModelAdmin): list_display=["name","email","is_resolved","created_at"]
@admin.register(CorrectionRequest)
class CAdmin(admin.ModelAdmin): list_display=["name","status","created_at"]; list_filter=["status"]
