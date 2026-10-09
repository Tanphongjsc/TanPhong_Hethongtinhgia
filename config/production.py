"""Production/staging settings. No .env discovery or business configuration changes."""
import os
from urllib.parse import urlsplit
from ipaddress import ip_address
from django.core.exceptions import ImproperlyConfigured

os.environ.setdefault("APP_ENV", "production")
if os.environ["APP_ENV"] not in ("production", "staging"):
    raise ImproperlyConfigured("config.production yêu cầu APP_ENV=production hoặc staging.")

from .settings import *  # noqa: E402,F403


def invalid(message):
    raise ImproperlyConfigured(message)


if env.bool("DJANGO_DEBUG", default=False):
    invalid("Production phải dùng DJANGO_DEBUG=False.")
DEBUG = False
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-") or any(word in SECRET_KEY.lower() for word in ("replace-with", "change-me", "replace-me")):
    invalid("DJANGO_SECRET_KEY phải là khóa ngẫu nhiên đủ mạnh, không dùng placeholder.")

APP_TRANSPORT = env("APP_TRANSPORT", default="")
RENDER_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="") if APP_TRANSPORT == "render_https" else ""
if APP_TRANSPORT == "render_https":
    if env("RENDER", default="") != "true" or not RENDER_HOSTNAME or not RENDER_HOSTNAME.endswith(".onrender.com"):
        invalid("render_https chỉ dùng trên Render Web Service có RENDER=true và RENDER_EXTERNAL_HOSTNAME hợp lệ.")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if RENDER_HOSTNAME and RENDER_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)
if not ALLOWED_HOSTS:
    invalid("Thiếu DJANGO_ALLOWED_HOSTS cho production.")
from django.http.request import split_domain_port
for hostname in ALLOWED_HOSTS:
    domain, port = split_domain_port(hostname)
    if not domain or port or "*" in hostname or hostname.startswith(".") or hostname != hostname.strip():
        invalid("DJANGO_ALLOWED_HOSTS phải gồm hostname/IP cụ thể, không URL/port/wildcard.")

for field in ("NAME", "USER", "PASSWORD", "HOST", "PORT"):
    if not str(DATABASES["default"].get(field, "")).strip():
        invalid(f"Thiếu cấu hình DB_{field} hoặc DATABASE_URL hợp lệ.")
if DATABASES["default"]["OPTIONS"]["sslmode"] not in ("require", "verify-ca", "verify-full"):
    invalid("Production DB_SSLMODE phải là require, verify-ca hoặc verify-full.")
if not 0 <= DATABASES["default"]["CONN_MAX_AGE"] <= 3600:
    invalid("DB_CONN_MAX_AGE phải nằm trong khoảng 0–3600 giây.")
if not 1 <= DATABASES["default"]["OPTIONS"]["connect_timeout"] <= 60:
    invalid("DB_CONNECT_TIMEOUT phải nằm trong khoảng 1–60 giây.")
try:
    if not 1 <= int(DATABASES["default"]["PORT"]) <= 65535: raise ValueError
except (TypeError, ValueError):
    invalid("DB_PORT không hợp lệ.")

if APP_TRANSPORT not in ("private_http", "https_proxy", "render_https"):
    invalid("Chọn rõ APP_TRANSPORT=private_http, https_proxy hoặc render_https theo hạ tầng thực tế.")
APP_TRUSTED_PROXY = env("APP_TRUSTED_PROXY", default="")
if APP_TRUSTED_PROXY:
    try: ip_address(APP_TRUSTED_PROXY)
    except ValueError: invalid("APP_TRUSTED_PROXY phải là IP peer cụ thể, không wildcard.")
if APP_TRANSPORT == "https_proxy" and not APP_TRUSTED_PROXY:
    invalid("https_proxy cần APP_TRUSTED_PROXY đúng IP của gateway TLS.")
if APP_TRANSPORT != "https_proxy" and APP_TRUSTED_PROXY:
    invalid("APP_TRUSTED_PROXY chỉ dùng với https_proxy; Render dùng managed ingress riêng.")

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
if RENDER_HOSTNAME and f"https://{RENDER_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOSTNAME}")
for origin in CSRF_TRUSTED_ORIGINS:
    parsed = urlsplit(origin)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or "*" in origin or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        invalid("DJANGO_CSRF_TRUSTED_ORIGINS phải là origin cụ thể, không path/wildcard.")
    if APP_TRANSPORT in ("https_proxy", "render_https") and parsed.scheme != "https":
        invalid("Origin production dùng gateway HTTPS phải bắt đầu bằng https://.")

SECURE_SSL_REDIRECT = APP_TRANSPORT in ("https_proxy", "render_https")
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
# Signed toast cookies reuse this setting; there is still no session backend.
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_REDIRECT_EXEMPT = [r"^health/$", r"^ready/$"]
# Waitress validates the peer and sets wsgi.url_scheme itself; Django does not
# trust an arbitrary client-supplied X-Forwarded-Proto header.
SECURE_PROXY_SSL_HEADER = None
# Render terminates public TLS and sets X-Forwarded-Proto at its managed ingress.
# This trust applies only to the explicitly selected Render platform transport.
if APP_TRANSPORT == "render_https":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)
if SECURE_HSTS_SECONDS < 0 or (SECURE_HSTS_SECONDS and (not SECURE_SSL_REDIRECT or not env.bool("APP_HTTPS_VERIFIED", default=False))):
    invalid("Chỉ bật HSTS sau khi HTTPS đã được xác minh (APP_HTTPS_VERIFIED=True).")
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

STATIC_ROOT = Path(env("DJANGO_STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))
if not STATIC_ROOT.is_absolute() or STATIC_ROOT.resolve() == (BASE_DIR / "static").resolve():
    invalid("DJANGO_STATIC_ROOT phải là đường dẫn tuyệt đối, khác thư mục static source.")
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_ALLOW_ALL_ORIGINS = False
STATICFILES_FINDERS = ["config.staticfiles.BuiltAssetFinder", "django.contrib.staticfiles.finders.AppDirectoriesFinder"]

LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper()
if LOG_LEVEL not in ("INFO", "WARNING", "ERROR", "CRITICAL"):
    invalid("LOG_LEVEL production phải là INFO/WARNING/ERROR/CRITICAL.")
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "waitress": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# Registration is production-only; checks never query or mutate business data.
from . import checks  # noqa: E402,F401
