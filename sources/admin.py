from django.contrib import admin
from sources.models import NewsSource, FetchingLog
@admin.register(NewsSource)
class SourceAdmin(admin.ModelAdmin):
    list_display=["name","feed_type","language","is_active","last_status","last_fetched_at"]
    list_filter=["is_active","language"]
    actions=["activate","deactivate"]
    @admin.action(description="Activate sources")
    def activate(self,request,queryset): queryset.update(is_active=True)
    @admin.action(description="Deactivate sources")
    def deactivate(self,request,queryset): queryset.update(is_active=False)
@admin.register(FetchingLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display=["source","status","fetched","created","duplicates","started_at"]
    list_filter=["status"]
