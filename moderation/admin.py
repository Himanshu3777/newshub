from django.contrib import admin
from moderation.models import SensitiveContentFinding, AuditLog
@admin.register(SensitiveContentFinding)
class SensitiveAdmin(admin.ModelAdmin):
    list_display=["article","finding_type","severity","needs_human_review","reviewed"]
    list_filter=["severity","finding_type","reviewed"]
    actions=["mark_reviewed"]
    @admin.action(description="Mark reviewed")
    def mark_reviewed(self,request,queryset): queryset.update(reviewed=True)
@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display=["action","actor","created_at"]
