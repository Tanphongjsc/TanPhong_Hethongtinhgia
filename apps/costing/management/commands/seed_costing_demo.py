from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from apps.costing.demo_data import seed_demo, manual_expected, inventory
from config.command_safety import require_demo_environment


class Command(BaseCommand):
    help = "Tạo bộ dữ liệu DEMO_ thống nhất trong công ty hiện có; chạy lại không nhân bản."

    def handle(self, *args, **options):
        require_demo_environment()
        try:
            demo = seed_demo()
        except ValidationError as error:
            raise CommandError("Không thể seed dữ liệu mẫu: " + "; ".join(error.messages)) from None
        self.stdout.write(f"Công ty hiện có: {demo.workspace.organization.code} (ID {demo.workspace.organization.pk}); không tạo/sửa công ty.")
        self.stdout.write(f"Bản ghi tạo trực tiếp: {sum(demo.created.values())}; {demo.created}")
        self.stdout.write(f"Inventory (gồm versions/lines do service tạo và bản sao): {inventory(demo)}")
        self.stdout.write(f"Kỳ vọng thủ công: {manual_expected()}")
        self.stdout.write(self.style.SUCCESS("Đã seed bộ mẫu. Chạy verify_costing_demo để thực thi và đối soát trên database thật."))
