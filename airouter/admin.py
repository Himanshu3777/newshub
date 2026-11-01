from django.contrib import admin
from airouter.models import ProviderUsage, ProviderState, AIGenerationLog, AICache
@admin.register(ProviderUsage)
class U(admin.ModelAdmin): list_display=["date","provider","kind","used"]; list_filter=["provider","kind"]
@admin.register(ProviderState)
class S(admin.ModelAdmin): list_display=["provider","status","cooldown_until","consecutive_failures","last_success_at"]
@admin.register(AIGenerationLog)
class L(admin.ModelAdmin): list_display=["created_at","request_type","provider","model","success","response_ms","fallback_used","cached"]; list_filter=["provider","success","request_type"]
@admin.register(AICache)
class C(admin.ModelAdmin): list_display=["kind","provider","model","created_at"]
