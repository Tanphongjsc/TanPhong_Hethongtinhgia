"""Render/Linux WSGI server: gunicorn -c config/gunicorn.py config.wsgi:application."""
import os

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.production")
if os.environ["APP_ENV"] != "production" or os.environ["DJANGO_SETTINGS_MODULE"] != "config.production":
    raise RuntimeError("Render yêu cầu APP_ENV=production và DJANGO_SETTINGS_MODULE=config.production.")
if os.environ.get("APP_TRANSPORT") != "render_https":
    raise RuntimeError("Gunicorn Render yêu cầu APP_TRANSPORT=render_https.")


def integer(name, default, lower, upper):
    try:
        value = int(os.environ.get(name, default))
        if lower <= value <= upper:
            return value
    except (ValueError, TypeError):
        pass
    raise RuntimeError(f"{name} phải nằm trong khoảng {lower}–{upper}.")


bind = f"0.0.0.0:{integer('PORT', 10000, 1, 65535)}"
workers = integer("WEB_CONCURRENCY", 1, 1, 8)
worker_class = "gthread"
threads = integer("GUNICORN_THREADS", 4, 1, 16)
timeout = integer("GUNICORN_TIMEOUT", 30, 10, 120)
graceful_timeout = 25
keepalive = 5
preload_app = False
# Django handles Render's one canonical scheme header. Do not trust every
# Gunicorn forwarder header or client-provided SCRIPT_NAME/PATH_INFO.
secure_scheme_headers = {}
forwarded_allow_ips = "127.0.0.1,::1"
forwarder_headers = ""
accesslog = None  # Request middleware logs path/status/trace; never query/body.
errorlog = "-"
capture_output = True
logconfig_dict = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.logging.JsonFormatter"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "json"},
        "null": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Gunicorn also enables access output when logconfig_dict exists, even
        # with accesslog=None. Drop it explicitly to keep query strings private.
        "gunicorn.access": {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
    },
}


def post_worker_init(worker):
    # Read-only readiness before this worker handles requests; no build/DDL/DML.
    from django.db import connections
    from django.core.exceptions import ImproperlyConfigured
    from config.health import database_ready
    from config.checks import static_errors
    from apps.master_data.company_context import get_default_organization
    try:
        if static_errors() or not database_ready():
            raise ImproperlyConfigured("Static manifest hoặc database/schema costing chưa sẵn sàng.")
        get_default_organization()  # Existing DB compatibility only, no user workflow.
        worker.log.info("application_start", extra={"stage": "startup"})
    finally:
        connections.close_all()
