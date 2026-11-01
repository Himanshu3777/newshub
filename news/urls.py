from django.urls import path
from news import views
urlpatterns=[path("cover/<int:pk>/",views.cover,name="cover"),path("news/",views.listing,name="news_list"),path("news/<slug:slug>/",views.detail,name="news_detail"),path("search/",views.search_page,name="search")]
