"""Tests use a separate localhost PostgreSQL database, never Supabase."""
import os

os.environ["APP_ENV"] = "test"
# A production URL must never influence even the base-settings import in tests.
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("DJANGO_SECRET_KEY", "costing-isolated-test-key")
for key, value in {
    "DB_NAME": "unused", "DB_USER": "unused", "DB_PASSWORD": "unused",
    "DB_HOST": "127.0.0.1", "DB_PORT": "55432",
}.items():
    os.environ.setdefault(key, value)

from .settings import *  # noqa: E402,F403

APP_ENV = "test"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "costing_test",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": os.environ.get("COSTING_TEST_DB_PORT", "55432"),
        "OPTIONS": {"sslmode": "disable"},
        "TEST": {"NAME": "test_costing_slice"},
    },
}
TEST_RUNNER = "apps.master_data.testing.CostingTestRunner"
CSRF_COOKIE_SECURE = False
APP_MODE = "single_company"
DEFAULT_ORGANIZATION_ID = None
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
