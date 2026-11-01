from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = ("Generate AI cover photos (Pollinations/FLUX) for articles that do not "
            "have one yet and store the JPEG on the article. Safe to re-run: "
            "articles with a cover are skipped. Use --limit to bound a run.")

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        from news.models import NewsArticle
        from news.ai_image import fetch_ai_cover
        qs = NewsArticle.objects.filter(cover_jpeg__isnull=True).order_by("-published_at")[: opts["limit"]]
        done = failed = 0
        for art in qs:
            data = fetch_ai_cover(art)
            if data:
                art.cover_jpeg = data
                art.save(update_fields=["cover_jpeg"])
                done += 1
                self.stdout.write(f"cover OK   #{art.id} {art.title[:60]}")
            else:
                failed += 1
                self.stdout.write(f"cover FAIL #{art.id} (SVG fallback stays)")
        self.stdout.write(self.style.SUCCESS(f"AI covers generated: {done}, failed: {failed}"))
