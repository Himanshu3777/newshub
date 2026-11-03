from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from core import views
urlpatterns=[path("",views.home,name="home"),path("about/",views.about,name="about"),path("methodology/",views.methodology,name="methodology"),path("sources/",views.sources_page,name="sources"),path("fact-check/",views.factcheck_page,name="factcheck"),path("analysis/",views.analysis_page,name="analysis"),path("dashboard/",views.dashboard,name="dashboard"),path("contact/",views.contact,name="contact"),path("check-claim/",views.check_claim_page,name="check_claim"),path("accounts/login/",LoginView.as_view(template_name="core/login.html"),name="login"),path("accounts/register/",views.register_view,name="register"),path("accounts/logout/",LogoutView.as_view(),name="logout")]
