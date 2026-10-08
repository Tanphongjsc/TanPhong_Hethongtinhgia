"""Canonical production entry point: python -m config.serve [--check]."""
import argparse
import logging
import os


def server_options(settings):
    from django.core.exceptions import ImproperlyConfigured

    def integer(name, default, lower, upper):
        try:
            value = int(os.environ.get(name, default))
            if not lower <= value <= upper:
                raise ValueError
            return value
        except ValueError:
            raise ImproperlyConfigured(f"{name} phải nằm trong khoảng {lower}–{upper}.") from None

    options = {
        "host": os.environ.get("APP_BIND", "127.0.0.1"),
        "port": integer("APP_PORT", 8000, 1, 65535),
        "threads": integer("APP_THREADS", 4, 1, 64),
        "channel_timeout": integer("APP_CHANNEL_TIMEOUT", 120, 10, 3600),
        "max_request_body_size": settings.DATA_UPLOAD_MAX_MEMORY_SIZE,
        "expose_tracebacks": False,
        "ident": "costing",
        "clear_untrusted_proxy_headers": True,
    }
    if settings.APP_TRANSPORT == "https_proxy":
        options.update(trusted_proxy=settings.APP_TRUSTED_PROXY,
                       trusted_proxy_count=1, trusted_proxy_headers={"x-forwarded-proto"})
    return options


def preflight():
    import django
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
    from django.core.management import call_command
    from django.db import connections
    django.setup()
    options = server_options(settings)
    call_command("check", deploy=True, fail_level="ERROR")
    from .health import database_ready
    from apps.master_data.company_context import get_default_organization
    try:
        if not database_ready():
            raise ImproperlyConfigured("Database chưa sẵn sàng hoặc search_path/schema costing không đúng.")
        get_default_organization()  # Existing compatibility layer, never creates data.
    finally:
        connections.close_all()
    return options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm tra cấu hình, static, DB; không mở HTTP port.")
    args = parser.parse_args()
    os.environ.setdefault("APP_ENV", "production")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.production")
    if os.environ["DJANGO_SETTINGS_MODULE"] != "config.production":
        parser.exit(1, "Production entry point yêu cầu DJANGO_SETTINGS_MODULE=config.production.\n")
    try:
        options = preflight()
        if args.check:
            print("Production preflight PASS (không ghi dữ liệu).")
            return
        from django.core.wsgi import get_wsgi_application
        from waitress import serve
        logging.getLogger(__name__).info("application_start", extra={"stage": "startup"})
        serve(get_wsgi_application(), **options)
    except KeyboardInterrupt:
        return
    except Exception:
        # Detailed diagnostic stays server-side, redacted by the JSON formatter.
        from .logging import JsonFormatter
        if not logging.getLogger().handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            logging.getLogger().addHandler(handler)
        logging.getLogger(__name__).exception("production_start_failed")
        parser.exit(1, "Không thể khởi động ứng dụng. Kiểm tra cấu hình và technical log.\n")


if __name__ == "__main__":
    main()
