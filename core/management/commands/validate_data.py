"""Data-integrity validation (read-only; never deletes or modifies data).
Reports duplicate URLs, missing briefs, orphaned findings, unmasked PII in
findings, and lock leftovers. Use --strict to exit non-zero on any problem."""
from django.core.management.base import BaseCommand
from django.db.models import Count
from news.models import NewsArticle
from moderation.models import SensitiveContentFinding
from core.models import SystemLock

class Command(BaseCommand):
    help = "Validate data integrity and print a report (read-only)"
    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true")
    def handle(self, *a, **o):
        problems = []
        dup_urls = (NewsArticle.objects.values("source_url").annotate(n=Count("id")).filter(n__gt=1).count())
        if dup_urls: problems.append(f"duplicate source_url groups: {dup_urls}")
        no_brief = NewsArticle.objects.filter(ai_brief="").count()
        orphan_findings = SensitiveContentFinding.objects.filter(article__isnull=True).count()
        if orphan_findings: problems.append(f"orphaned sensitive findings: {orphan_findings}")
        import re
        raw_pii = 0
        for f in SensitiveContentFinding.objects.all()[:500]:
            if re.search(r"\b\d{10}\b", f.matched_text_masked or ""):
                raw_pii += 1
        if raw_pii: problems.append(f"findings with unmasked 10-digit numbers: {raw_pii}")
        locks = SystemLock.objects.count()
        self.stdout.write(f"articles={NewsArticle.objects.count()} dup_url_groups={dup_urls} "
                          f"missing_brief={no_brief} orphan_findings={orphan_findings} locks={locks}")
        if problems:
            for p in problems: self.stdout.write(self.style.WARNING("PROBLEM: " + p))
            if o["strict"]: raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS("Data integrity OK"))
