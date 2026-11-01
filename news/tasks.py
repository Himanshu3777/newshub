from celery import shared_task
@shared_task
def fetch_all_sources_task():
    from news.fetcher import fetch_all_sources
    return fetch_all_sources()
@shared_task
def verify_article_task(article_id):
    from news.models import NewsArticle
    from verification.engine import verify_article
    try: a=NewsArticle.objects.get(id=article_id)
    except NewsArticle.DoesNotExist: return {"error":"not found"}
    return verify_article(a)
