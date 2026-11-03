def stats(request):
    try:
        from news.models import NewsCategory
        return {"nav_categories": NewsCategory.objects.all()[:13]}
    except Exception: return {"nav_categories":[]}

# Portal navigation (PPT wireframe): main sections in Jagran-style order with
# Hindi labels, e.g. देश / दुनिया / राजनीति / व्यापार / खेल / मनोरंजन.
NAV_ORDER=["national","international","politics","business","sports","entertainment","technology","health"]
HINDI_LABELS={"national":"देश","international":"दुनिया","politics":"राजनीति","business":"व्यापार","sports":"खेल","entertainment":"मनोरंजन","technology":"टेक्नोलॉजी","health":"स्वास्थ्य","education":"शिक्षा","science":"विज्ञान","crime":"क्राइम","environment":"पर्यावरण","breaking-news":"ताज़ा खबर"}

def portal_nav(request):
    try:
        from news.models import NewsCategory
        by_slug={c.slug:c for c in NewsCategory.objects.all()}
        cats=[]
        for slug in NAV_ORDER:
            c=by_slug.get(slug)
            if c: cats.append({"name":c.name,"slug":c.slug,"hindi":HINDI_LABELS.get(c.slug,c.name)})
        return {"portal_categories":cats}
    except Exception:
        return {"portal_categories":[]}
