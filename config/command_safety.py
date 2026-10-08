"""Keep demo execution outside production. No user/permission mechanism."""
from django.conf import settings
from django.core.management.base import CommandError


def require_demo_environment():
    if settings.APP_ENV not in ("development", "test", "staging"):
        raise CommandError("Lệnh DEMO chỉ được chạy ở development/test/staging, không chạy production.")
