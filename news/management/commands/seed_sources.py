from django.core.management.base import BaseCommand
from django.utils.text import slugify
from sources.models import NewsSource
from news.models import NewsCategory
SOURCES=[
 ("BBC News","https://www.bbc.com","https://feeds.bbci.co.uk/news/world/asia/india/rss.xml","en",90),
 ("The Hindu","https://www.thehindu.com","https://www.thehindu.com/news/national/feeder/default.rss","en",88),
 ("NDTV","https://www.ndtv.com","https://feeds.feedburner.com/ndtvnews-top-stories","en",82),
 ("Indian Express","https://indianexpress.com","https://indianexpress.com/feed/","en",85),
 ("Hindustan Times","https://www.hindustantimes.com","https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml","en",80),
 ("India Today","https://www.indiatoday.in","https://www.indiatoday.in/rss/home","en",80),
 ("Aaj Tak","https://www.aajtak.in","https://aajtak.intoday.in/rss/1-home-news.xml","hi",75),
 ("Dainik Jagran","https://www.jagran.com","https://www.jagran.com/rss/news/national.xml","hi",72),
 ("Times of India","https://timesofindia.indiatimes.com","https://timesofindia.indiatimes.com/rssfeedstopstories.cms","en",78),
 ("Zee News","https://zeenews.india.com","https://zeenews.india.com/rss/india-national-news.xml","hi",70),
 ("News18","https://www.news18.com","https://www.news18.com/commonfeeds/v1/eng/rss/india.xml","en",74),
 ("Moneycontrol","https://www.moneycontrol.com","https://www.moneycontrol.com/rss/latestnews.xml","en",76),
 ("LiveMint","https://www.livemint.com","https://www.livemint.com/rss/news","en",80),
 ("ABP Live","https://news.abplive.com","https://news.abplive.com/home/feed","hi",68),
 ("Al Jazeera","https://www.aljazeera.com","https://www.aljazeera.com/xml/rss/all.xml","en",84),
 ("DW News","https://www.dw.com","https://rss.dw.com/rdf/rss-en-all","en",86),
 ("The Guardian","https://www.theguardian.com","https://www.theguardian.com/world/rss","en",88),
]
CATS=["Breaking News","Politics","Technology","Business","Education","Sports","Entertainment","Science","Health","International","National","Crime","Environment"]
class Command(BaseCommand):
    help="Seed 8 publishers + 13 categories (idempotent)"
    def handle(self,*a,**o):
        for name in CATS: NewsCategory.objects.get_or_create(name=name,defaults={"slug":slugify(name)})
        for name,site,feed,lang,cred in SOURCES:
            NewsSource.objects.update_or_create(name=name,defaults={"slug":slugify(name),"website":site,"feed_url":feed,"language":lang,"credibility_score":cred,"is_active":True})
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(SOURCES)} sources, {len(CATS)} categories"))
