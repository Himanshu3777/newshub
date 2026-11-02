from django.contrib import admin
from sources.models import NewsSource, FetchingLog
@admin.register(NewsSource)
class SourceAdmin(admin.ModelAdmin):
    list_display=["name","feed_type","language","is_active","license_status","last_status","last_fetched_at"]
    list_filter=["is_active","language","license_status"]
    actions=["activate","deactivate","mark_license_permitted","mark_license_restricted"]
    @admin.action(description="Activate sources")
    def activate(self,request,queryset): queryset.update(is_active=True)
    @admin.action(description="Deactivate sources")
    def deactivate(self,request,queryset): queryset.update(is_active=False)
    @admin.action(description="Mark license: permitted (terms checked)")
    def mark_license_permitted(self,request,queryset): queryset.update(license_status="permitted")
    @admin.action(description="Mark license: restricted")
    def mark_license_restricted(self,request,queryset): queryset.update(license_status="restricted")
@admin.register(FetchingLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display=["source","status","fetched","created","duplicates","started_at"]
    list_filter=["status"]
