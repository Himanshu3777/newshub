from django.shortcuts import render, get_object_or_404
from django.db.models import Q, F
from django.core.paginator import Paginator
from news.models import NewsArticle, NewsCategory
from sources.models import NewsSource

QUARANTINE=["false","misleading","disputed"]
def public_qs():
    """Public feeds never include fake/misleading/disputed stories, and only
    show sources whose license_status is "permitted" - a technically working
    feed is not by itself legal permission for public display."""
    return NewsArticle.objects.exclude(verification_status__in=QUARANTINE).filter(source__license_status="permitted")
def article_list(request):
    qs=public_qs().select_related("source","category").all()
    if request.GET.get("unconfirmed"): qs=qs.filter(is_unconfirmed=True)
    q=request.GET.get("q","").strip(); cat=request.GET.get("category",""); src=request.GET.get("source",""); status=request.GET.get("status","")
    if q: qs=qs.filter(Q(title__icontains=q)|Q(summary__icontains=q))
    if cat: qs=qs.filter(category__slug=cat)
    if src: qs=qs.filter(source__slug=src)
    if status: qs=qs.filter(verification_status=status)
    sort=request.GET.get("sort","-published_at"); qs=qs.order_by(sort if sort in ("-published_at","published_at","-view_count") else "-published_at")
    page=Paginator(qs,12).get_page(request.GET.get("page"))
    most_read=public_qs().order_by("-view_count","-published_at")[:5]
    current_category=NewsCategory.objects.filter(slug=cat).first() if cat else None
    page_range=list(page.paginator.get_elided_page_range(page.number,on_each_side=1,on_ends=1))
    return page, {"q":q,"cat":cat,"src":src,"status":status,"sort":request.GET.get("sort",""),"most_read":most_read,"current_category":current_category,"page_range":page_range}

def home(request):
    from django.utils import timezone
    from sources.models import NewsSource
    from news.models import NewsCategory as NC
    base=public_qs().select_related("source","category")
    latest=list(base[:13])
    top_story=latest[0] if latest else None
    top_stories=latest[1:7]
    trending=list(base.order_by("-view_count","-published_at")[:5])
    breaking=base.filter(is_breaking=True)[:3]
    stats={"today":base.filter(published_at__date=timezone.now().date()).count(),"total":base.count(),"publishers":NewsSource.objects.filter(is_active=True).count(),"categories":NC.objects.count()}
    # Portal section blocks (PPT home page): lead + 3 links per main section.
    from core.context_processors import NAV_ORDER, HINDI_LABELS
    sections=[]
    for slug in NAV_ORDER:
        cat_obj=NC.objects.filter(slug=slug).first()
        if not cat_obj: continue
        arts=list(base.filter(category=cat_obj)[:4])
        if arts: sections.append({"category":cat_obj,"hindi":HINDI_LABELS.get(slug,cat_obj.name),"articles":arts})
        if len(sections)>=5: break
    photo_strip=list(base[:8])
    return render(request,"news/home.html",{"breaking":breaking,"latest":latest,"top_story":top_story,"top_stories":top_stories,"trending":trending,"stats":stats,"sections":sections,"photo_strip":photo_strip,"page_obj":None})

def listing(request):
    page,ctx=article_list(request)
    return render(request,"news/list.html",{"page_obj":page,"categories":NewsCategory.objects.all(),"sources":NewsSource.objects.all(),**ctx})

def detail(request,slug):
    art=get_object_or_404(NewsArticle.objects.select_related("source","category"),slug=slug)
    if (art.is_quarantined or not art.source.is_publicly_displayable) and not request.user.is_staff:
        # Same direct-link handling as quarantined stories: a warning page,
        # never the story itself, for non-staff visitors.
        return render(request,"news/quarantined.html",{"article":art,"reports":art.verification_reports.prefetch_related("evidence").all()})
    NewsArticle.objects.filter(id=art.id).update(view_count=F("view_count")+1)
    reports=art.verification_reports.prefetch_related("evidence").all()
    related=public_qs().filter(category=art.category).exclude(id=art.id).select_related("source")[:4] if art.category else []
    latest5=public_qs().select_related("source","category").exclude(id=art.id)[:5]
    return render(request,"news/detail.html",{"article":art,"reports":reports,"related":related,"latest5":latest5,"findings":art.sensitive_findings.all()})

def search_page(request):
    page,ctx=article_list(request)
    return render(request,"news/search.html",{"page_obj":page,"categories":NewsCategory.objects.all(),"sources":NewsSource.objects.all(),**ctx})

def cover(request,pk):
    from django.http import HttpResponse, Http404
    try: art=NewsArticle.objects.select_related("category","source").get(id=pk)
    except NewsArticle.DoesNotExist: raise Http404
    if art.cover_jpeg:
        resp=HttpResponse(bytes(art.cover_jpeg),content_type="image/jpeg")
        resp["Cache-Control"]="public, max-age=604800"
        return resp
    from news.ai_content import cover_svg
    resp=HttpResponse(cover_svg(art),content_type="image/svg+xml")
    resp["Cache-Control"]="public, max-age=86400"
    return resp
