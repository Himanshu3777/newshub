def stats(request):
    try:
        from news.models import NewsCategory
        return {"nav_categories": NewsCategory.objects.all()[:13]}
    except Exception: return {"nav_categories":[]}
