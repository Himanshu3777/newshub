from django.contrib import admin
from verification.models import VerificationReport, VerificationEvidence
class EvInline(admin.TabularInline): model=VerificationEvidence; extra=0
@admin.register(VerificationReport)
class RAdmin(admin.ModelAdmin): list_display=["article","status","confidence_score","reviewed_by_human","created_at"]; list_filter=["status"]; inlines=[EvInline]
@admin.register(VerificationEvidence)
class EvAdmin(admin.ModelAdmin): list_display=["publisher","kind","rating","report"]
from verification.models import ClaimSubmission
@admin.register(ClaimSubmission)
class ClaimAdmin(admin.ModelAdmin):
    list_display=["id","platform","result","created_at"]; list_filter=["platform","result"]; search_fields=["claim_text"]
