import json
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from apps.pricing.demo_scenario import verify_pricing_demo
from config.command_safety import require_demo_environment


class Command(BaseCommand):
    help = "Bổ sung Pricing DEMO idempotent và đối soát Golden độc lập, không chạy lại Costing."

    def add_arguments(self, parser): parser.add_argument("--report")

    def handle(self, *args, **options):
        require_demo_environment()
        try: report = verify_pricing_demo()
        except ValidationError as error: raise CommandError(" ".join(error.messages)) from None
        if options["report"]:
            path = Path(options["report"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Golden Pricing PASS; delta = 0; Costing Run giữ nguyên."))
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
