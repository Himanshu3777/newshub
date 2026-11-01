from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help="Fetch all active RSS sources now"
    def handle(self,*a,**o):
        from news.fetcher import fetch_all_sources
        for r in fetch_all_sources(): self.stdout.write(str(r))
