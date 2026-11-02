from rest_framework import serializers
from news.models import NewsArticle, NewsCategory, NewsTag
from sources.models import NewsSource, FetchingLog
from verification.models import VerificationReport, VerificationEvidence
from moderation.models import SensitiveContentFinding
from feedback_app.models import UserFeedback, CorrectionRequest
class SourceSerializer(serializers.ModelSerializer):
    article_count=serializers.IntegerField(source="articles.count",read_only=True)
    class Meta: model=NewsSource; fields="__all__"
class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=NewsCategory; fields="__all__"
class ArticleSerializer(serializers.ModelSerializer):
    source_name=serializers.CharField(source="source.name",read_only=True)
    category_name=serializers.CharField(source="category.name",read_only=True,default="")
    tags_list=serializers.StringRelatedField(source="tags",many=True,read_only=True)
    class Meta: model=NewsArticle; fields=["id","title","slug","ai_brief","is_unconfirmed","source_note","source","source_name","source_url","author","category","category_name","tags_list","image_url","language","published_at","verification_status","confidence_score","has_sensitive_content","view_count","is_breaking"]
class EvidenceSerializer(serializers.ModelSerializer):
    class Meta: model=VerificationEvidence; fields="__all__"
class ReportSerializer(serializers.ModelSerializer):
    evidence=EvidenceSerializer(many=True,read_only=True)
    article_title=serializers.CharField(source="article.title",read_only=True)
    class Meta: model=VerificationReport; fields="__all__"
class SensitiveSerializer(serializers.ModelSerializer):
    class Meta: model=SensitiveContentFinding; fields="__all__"
class FeedbackSerializer(serializers.ModelSerializer):
    # is_resolved is staff-controlled: never writable through the public API
    # (mass-assignment fix - a submitter must not mark their own feedback resolved).
    class Meta: model=UserFeedback; fields=["id","name","email","message","created_at","is_resolved"]; read_only_fields=["id","created_at","is_resolved"]
class CorrectionSerializer(serializers.ModelSerializer):
    # status is a moderation decision (pending/accepted/rejected): read-only for
    # the public API so nobody can submit a correction pre-marked "accepted".
    class Meta: model=CorrectionRequest; fields=["id","article","article_url","name","email","description","status","created_at"]; read_only_fields=["id","status","created_at"]
class FetchLogSerializer(serializers.ModelSerializer):
    class Meta: model=FetchingLog; fields="__all__"
