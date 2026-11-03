from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from news.models import NewsArticle, NewsCategory
from sources.models import NewsSource, FetchingLog
from verification.models import VerificationReport, VerificationEvidence
from moderation.models import SensitiveContentFinding
from feedback_app.models import UserFeedback, CorrectionRequest
from api.serializers import *

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    # Public API: quarantined stories excluded. During the testing phase
    # (owner decision 2026-11-03) all sources are publicly listed - the
    # license_status gate can be re-enabled when testing ends.
    queryset=NewsArticle.objects.exclude(verification_status__in=["false","misleading","disputed"]).select_related("source","category").prefetch_related("tags")
    serializer_class=ArticleSerializer; filter_backends=[DjangoFilterBackend,filters.SearchFilter,filters.OrderingFilter]
    filterset_fields={"category__slug":["exact"],"source__slug":["exact"],"verification_status":["exact"],"language":["exact"],"published_at":["gte","lte"]}
    search_fields=["title","summary"]; ordering_fields=["published_at","view_count"]; ordering=["-published_at"]
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=NewsCategory.objects.all(); serializer_class=CategorySerializer; pagination_class=None
class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=NewsSource.objects.all(); serializer_class=SourceSerializer; pagination_class=None
class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=VerificationReport.objects.select_related("article").prefetch_related("evidence"); serializer_class=ReportSerializer
    filter_backends=[DjangoFilterBackend]; filterset_fields=["status","article"]
class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=VerificationEvidence.objects.all(); serializer_class=EvidenceSerializer; filter_backends=[DjangoFilterBackend]; filterset_fields=["report","kind"]
class SensitiveViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=SensitiveContentFinding.objects.all(); serializer_class=SensitiveSerializer; permission_classes=[permissions.IsAdminUser]
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset=UserFeedback.objects.all(); serializer_class=FeedbackSerializer
    def get_permissions(self): return [permissions.AllowAny()] if self.action=="create" else [permissions.IsAdminUser()]
class CorrectionViewSet(viewsets.ModelViewSet):
    queryset=CorrectionRequest.objects.all(); serializer_class=CorrectionSerializer
    def get_permissions(self): return [permissions.AllowAny()] if self.action=="create" else [permissions.IsAdminUser()]

@api_view(["GET"])
def stats(request):
    return Response({
      "total":NewsArticle.objects.count(),
      "verified":NewsArticle.objects.filter(verification_status="verified").count(),
      "partially_verified":NewsArticle.objects.filter(verification_status="partially_verified").count(),
      "disputed":NewsArticle.objects.filter(verification_status__in=["disputed","misleading","false"]).count(),
      "unverified":NewsArticle.objects.filter(verification_status="unverified").count(),
      "needs_review":NewsArticle.objects.filter(verification_status="needs_review").count(),
      "sensitive_pending":SensitiveContentFinding.objects.filter(needs_human_review=True,reviewed=False).count(),
      "by_source":list(NewsArticle.objects.values("source__name").annotate(count=Count("id")).order_by("-count")),
      "by_category":list(NewsArticle.objects.values("category__name").annotate(count=Count("id")).order_by("-count")),
      "by_status":list(NewsArticle.objects.values("verification_status").annotate(count=Count("id")).order_by("-count")),
    })
@api_view(["GET"])
def search_api(request):
    q=request.GET.get("q","").strip()
    qs=NewsArticle.objects.filter(Q(title__icontains=q)|Q(summary__icontains=q)).select_related("source","category")[:50] if q else NewsArticle.objects.none()
    return Response(ArticleSerializer(qs,many=True).data)
@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def run_fetch(request):
    from news.fetcher import fetch_all_sources
    return Response(fetch_all_sources())

def trigger_fetch_async():
    """Run a full scan in a background thread (used by the scheduler trigger)."""
    import threading
    from news.fetcher import fetch_all_sources
    threading.Thread(target=fetch_all_sources,daemon=True).start()

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def fetch_trigger(request):
    """Pinged by an external free scheduler (e.g. cron-job.org) to start a
    news scan. Protected by the FETCH_TRIGGER_TOKEN env var; when the token
    is not configured the endpoint is disabled (404). Overlapping scans are
    already prevented by the rss_fetch lock inside fetch_all_sources."""
    import hmac
    from django.conf import settings
    token=getattr(settings,"FETCH_TRIGGER_TOKEN","")
    if not token: return Response({"detail":"trigger disabled"},status=404)
    if not hmac.compare_digest(request.GET.get("token",""),token): return Response({"detail":"forbidden"},status=403)
    trigger_fetch_async()
    return Response({"status":"fetch triggered"},status=202)
@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def run_verify(request,article_id):
    from verification.engine import verify_article
    try: art=NewsArticle.objects.get(id=article_id)
    except NewsArticle.DoesNotExist: return Response({"detail":"not found"},status=404)
    return Response(verify_article(art))
