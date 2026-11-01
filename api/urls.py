from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views
r=DefaultRouter(); r.register("articles",views.ArticleViewSet); r.register("categories",views.CategoryViewSet); r.register("sources",views.SourceViewSet); r.register("verifications",views.ReportViewSet); r.register("evidence",views.EvidenceViewSet); r.register("sensitive",views.SensitiveViewSet); r.register("feedback",views.FeedbackViewSet); r.register("corrections",views.CorrectionViewSet)
urlpatterns=[path("",include(r.urls)),path("stats/",views.stats),path("search/",views.search_api),path("fetch/run/",views.run_fetch),path("verify/<int:article_id>/",views.run_verify)]
