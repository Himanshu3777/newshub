"""Safe data backup: dumps the project's own data (sources, news,
verification, feedback, AI router usage/logs) to a timestamped JSON file.
Secrets are never part of Django models, so the dump contains no keys."""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

APPS = ["sources", "news", "verification", "moderation", "feedback_app", "airouter", "core"]

class Command(BaseCommand):
    help = "Write a timestamped JSON backup of project data into backups/"
    def add_arguments(self, parser):
        parser.add_argument("--out", default="backups")
    def handle(self, *a, **o):
        os.makedirs(o["out"], exist_ok=True)
        path = os.path.join(o["out"], f"newshub-backup-{timezone.now():%Y%m%d-%H%M%S}.json")
        with open(path, "w", encoding="utf-8") as fh:
            call_command("dumpdata", *APPS, indent=1, stdout=fh)
        self.stdout.write(self.style.SUCCESS(f"Backup written: {path}"))
