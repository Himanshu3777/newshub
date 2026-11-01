import time
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    help = ("Keep NewsHub dynamic: fetch fresh news from all active sources every "
            "--minutes (default 30), forever. Run this in a second window next to "
            "runserver. Stop with Ctrl+C. Use --once for a single pass.")

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=30)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **opts):
        from news.fetcher import fetch_all_sources
        minutes = max(1, int(opts["minutes"]))
        while True:
            started = timezone.now()
            try:
                results = fetch_all_sources()
                created = sum(r["created"] for r in results)
                self.stdout.write(self.style.SUCCESS(
                    f"[{started:%Y-%m-%d %H:%M:%S}] fetch pass done: {created} new articles "
                    f"from {len(results)} sources"))
            except Exception as e:  # keep the loop alive no matter what one pass does
                self.stdout.write(self.style.ERROR(f"[{started:%H:%M:%S}] fetch pass failed: {e}"))
            if opts["once"]:
                break
            self.stdout.write(f"Next fetch in {minutes} min. (Ctrl+C to stop)")
            try:
                for _ in range(minutes * 12):  # 5-second slices so Ctrl+C reacts fast
                    time.sleep(5)
            except KeyboardInterrupt:
                self.stdout.write("Auto-fetch stopped.")
                break
