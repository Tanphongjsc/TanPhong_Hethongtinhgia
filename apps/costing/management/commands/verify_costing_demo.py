import json
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import verify_demo
from config.command_safety import require_demo_environment


class Command(BaseCommand):
    help = "Thực thi Costing thật, đối soát thủ công, kiểm tra lịch sử và UI của bộ DEMO_."

    def add_arguments(self, parser):
        parser.add_argument("--report", default="", help="File JSON báo cáo nằm trong workspace.")

    def handle(self, *args, **options):
        require_demo_environment()
        report_path = None
        if options["report"]:
            report_path = Path(options["report"]).resolve()
            if not report_path.is_relative_to(settings.BASE_DIR.resolve()):
                raise CommandError("Báo cáo phải nằm trong thư mục dự án.")
        try:
            report = verify_demo(seed_demo())
        except ValidationError as error:
            raise CommandError("NOT READY FOR PRICING FOUNDATION: " + "; ".join(error.messages)) from None
        content = json.dumps(report, ensure_ascii=False, indent=2)
        if report_path:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(content + "\n", encoding="utf-8")
        self.stdout.write(content)
        self.stdout.write(self.style.SUCCESS(report["readiness"]))
