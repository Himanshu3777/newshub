from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help="Run verification on unverified articles"
    def add_arguments(self,p): p.add_argument("--limit",type=int,default=20)
    def handle(self,*a,**o):
        from news.models import NewsArticle
        from verification.engine import verify_article
        qs=NewsArticle.objects.filter(verification_status="unverified")[:o["limit"]]
        for art in qs: self.stdout.write(f"{art.id}: {verify_article(art)}")
