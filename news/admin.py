from django.contrib import admin
from news.models import NewsArticle, NewsCategory, NewsTag, NewsEntity
@admin.register(NewsArticle)
class AAdmin(admin.ModelAdmin): list_display=["title","source","category","verification_status","published_at","has_sensitive_content"]; list_filter=["verification_status","source","category"]; search_fields=["title","summary"]; readonly_fields=["fingerprint","fetched_at"]
@admin.register(NewsCategory)
class CAdmin(admin.ModelAdmin): prepopulated_fields={"slug":("name",)}
@admin.register(NewsTag)
class TAdmin(admin.ModelAdmin): prepopulated_fields={"slug":("name",)}
@admin.register(NewsEntity)
class EAdmin(admin.ModelAdmin): list_display=["name","entity_type","article"]; list_filter=["entity_type"]
