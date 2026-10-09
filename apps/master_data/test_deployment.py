"""Production configuration and real WSGI/static smoke on isolated localhost DB."""
from decimal import Decimal
from io import StringIO
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.wsgi import get_wsgi_application
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from config.checks import REQUIRED_STATIC, static_errors
from config.logging import JsonFormatter, request_trace
from config.serve import server_options


def safe_environment(**changes):
    # Deliberately discard inherited database credentials and Django settings.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("DB_", "DJANGO_", "APP_", "DEFAULT_ORGANIZATION", "DATABASE_URL", "RENDER", "GUNICORN_", "WEB_CONCURRENCY", "PORT"))}
    environment.update(APP_ENV="production", DJANGO_SETTINGS_MODULE="config.production",
        DJANGO_SECRET_KEY="isolated-production-settings-test-key-with-at-least-fifty-characters",
        DJANGO_DEBUG="False", DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver",
        DB_NAME="unused", DB_USER="unused", DB_PASSWORD="test-only-password", DB_HOST="127.0.0.1",
        DB_PORT="55432", DB_SSLMODE="require", APP_TRANSPORT="private_http", LOG_LEVEL="INFO")
    for key, value in changes.items():
        if value is None: environment.pop(key, None)
        else: environment[key] = value
    return environment


class ProductionSettingsTests(SimpleTestCase):
    def load(self, **changes):
        code = """import django, json
django.setup()
from django.conf import settings as s
print(json.dumps(dict(debug=s.DEBUG, search_path=s.DATABASES['default']['OPTIONS']['options'],
    ssl=s.DATABASES['default']['OPTIONS']['sslmode'], timezone=s.TIME_ZONE, locale=s.LANGUAGE_CODE,
    middleware=s.MIDDLEWARE, apps=s.INSTALLED_APPS, ssl_redirect=s.SECURE_SSL_REDIRECT,
    csrf_secure=s.CSRF_COOKIE_SECURE, proxy_header=s.SECURE_PROXY_SSL_HEADER)))
"""
        return subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR,
                              env=safe_environment(**changes), capture_output=True, text=True, encoding="utf-8", timeout=20)

    def test_valid_production_settings_load_without_local_env(self):
        result = self.load()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["debug"])
        self.assertEqual(data["search_path"], "-c search_path=costing,public")
        self.assertEqual((data["timezone"], data["locale"]), ("Asia/Ho_Chi_Minh", "vi"))
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", data["middleware"])
        self.assertFalse(any(word in app for app in data["apps"] for word in ("auth", "workflow", "audit", "sessions")))

    def test_missing_secrets_and_database_fail_fast(self):
        for key in ("DJANGO_SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
            with self.subTest(key=key):
                result = self.load(**{key: None})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)

    def test_unsafe_settings_rejected(self):
        for changes in (
            {"DJANGO_DEBUG": "True"}, {"DJANGO_SECRET_KEY": "change-me"}, {"DJANGO_ALLOWED_HOSTS": "*"},
            {"DJANGO_ALLOWED_HOSTS": "https://localhost"}, {"DJANGO_ALLOWED_HOSTS": ".example.com"},
            {"DJANGO_ALLOWED_HOSTS": ""}, {"DB_SSLMODE": "disable"}, {"DB_PORT": "0"},
            {"DB_CONN_MAX_AGE": "-1"}, {"DB_CONNECT_TIMEOUT": "0"}, {"APP_TRANSPORT": ""},
            {"APP_TRANSPORT": "https_proxy"}, {"APP_TRUSTED_PROXY": "*"},
            {"DJANGO_SECURE_HSTS_SECONDS": "3600"}, {"LOG_LEVEL": "DEBUG"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.example.com"},
            {"DJANGO_STATIC_ROOT": str(settings.BASE_DIR / "static")},
        ):
            with self.subTest(keys=tuple(changes)):
                self.assertNotEqual(self.load(**changes).returncode, 0)

    def test_https_proxy_uses_peer_validation_and_secure_cookie(self):
        result = self.load(APP_TRANSPORT="https_proxy", APP_TRUSTED_PROXY="127.0.0.1",
                           DJANGO_CSRF_TRUSTED_ORIGINS="https://costing.example", APP_HTTPS_VERIFIED="True",
                           DJANGO_SECURE_HSTS_SECONDS="300")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["ssl_redirect"])
        self.assertTrue(data["csrf_secure"])
        self.assertIsNone(data["proxy_header"])

    def test_test_command_refuses_production_settings_before_db_connection(self):
        for args in (("test",), ("test", "--settings=config.production"), ("flush", "--noinput"), ("migrate",), ("makemigrations",)):
            result = subprocess.run([sys.executable, "manage.py", *args], cwd=settings.BASE_DIR,
                env=safe_environment(), capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)

    def test_waitress_defaults_and_exact_proxy_settings(self):
        policy = SimpleNamespace(APP_TRANSPORT="private_http", DATA_UPLOAD_MAX_MEMORY_SIZE=2621440)
        with patch.dict(os.environ, {}, clear=True):
            options = server_options(policy)
        self.assertEqual((options["host"], options["threads"], options["channel_timeout"]), ("127.0.0.1", 4, 120))
        self.assertFalse(options["expose_tracebacks"])
        policy.APP_TRANSPORT, policy.APP_TRUSTED_PROXY = "https_proxy", "127.0.0.1"
        options = server_options(policy)
        self.assertEqual(options["trusted_proxy_headers"], {"x-forwarded-proto"})
        self.assertTrue(options["clear_untrusted_proxy_headers"])

    def test_manifest_missing_or_escaping_release_rejected(self):
        with TemporaryDirectory() as folder, override_settings(STATIC_ROOT=folder):
            self.assertEqual(static_errors()[0].id, "costing.E002")
            paths = {name: "../outside.js" for name in REQUIRED_STATIC}
            Path(folder, "staticfiles.json").write_text(json.dumps({"paths": paths}), encoding="utf-8")
            self.assertEqual(static_errors()[0].id, "costing.E002")

    def test_json_logs_redact_secrets_and_correlate_request(self):
        token = request_trace.set("trace-test")
        try:
            with patch.dict(os.environ, DB_PASSWORD="secret-db-password", DJANGO_SECRET_KEY="secret-signing-key"):
                try: raise OperationalError("password=secret-db-password postgres://user:pass@host/db secret-signing-key")
                except OperationalError:
                    record = logging.LogRecord("costing", logging.ERROR, "", 1, "run_id=abc stage=price secret-db-password", (), sys.exc_info())
                payload = json.loads(JsonFormatter().format(record))
        finally:
            request_trace.reset(token)
        self.assertEqual(payload["trace_id"], "trace-test")
        for secret in ("secret-db-password", "secret-signing-key", "user:pass@host"):
            self.assertNotIn(secret, json.dumps(payload))
        self.assertIn("run_id=abc", payload["message"])


class ProbeAndSafetyTests(TestCase):
    def test_liveness_does_not_query_database_or_workspace(self):
        with self.assertNumQueries(0), patch("apps.master_data.access.get_workspace", side_effect=AssertionError("workspace")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("X-Trace-ID", response)

    def test_readiness_local_probe(self):
        with self.assertNumQueries(1):
            response = self.client.get("/ready/")
        self.assertEqual(response.status_code, 200)

    def test_production_schema_and_search_path_are_verified(self):
        with override_settings(APP_ENV="production"), patch("config.health.connection") as db:
            cursor = db.cursor.return_value.__enter__.return_value
            for row, expected in ((('costing', 'costing,public', True), 200),
                                  (('public', 'costing,public', True), 503),
                                  (('costing', 'public,costing', True), 503),
                                  (('costing', 'costing,public', False), 503)):
                cursor.fetchone.return_value = row
                self.assertEqual(self.client.get("/ready/").status_code, expected)
            self.assertIn("to_regclass('costing.cost_element')", cursor.execute.call_args.args[0])

    def test_readiness_outage_returns_safe_503(self):
        with patch("config.health.database_ready", side_effect=OperationalError("password=secret_db")):
            response = self.client.get("/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn(b"secret_db", response.content)
        self.assertEqual(self.client.get("/health/").status_code, 200)

    def test_probes_require_get_and_validate_host(self):
        for path in ("/health/", "/ready/"):
            self.assertEqual(self.client.post(path).status_code, 405)
            self.assertEqual(self.client.get(path, HTTP_HOST="untrusted.invalid").status_code, 400)

    @override_settings(APP_ENV="production")
    def test_all_demo_commands_refused_without_queries(self):
        for command in ("seed_costing_demo", "verify_costing_demo", "verify_pricing_demo"):
            with self.subTest(command=command), self.assertNumQueries(0), self.assertRaisesMessage(CommandError, "không chạy production"):
                call_command(command, stdout=StringIO())

    def test_request_log_excludes_query_and_body(self):
        with self.assertLogs("apps.master_data.middleware", level="INFO") as captured:
            response = self.client.get("/health/?token=do-not-log")
        record = captured.records[-1]
        self.assertEqual(record.path, "/health/")
        self.assertNotIn("do-not-log", repr(record.__dict__))
        self.assertEqual(record.status, 200)
        self.assertIsNone(request_trace.get())
        self.assertIn("X-Trace-ID", response)


class ProductionHTTPTests(TransactionTestCase):
    """Real Waitress/WhiteNoise, DEBUG=False, localhost test fixtures only."""
    def setUp(self):
        from apps.core.models import Organization
        from apps.costing.demo_data import seed_demo
        from apps.costing.demo_verification import verify_demo
        from apps.pricing.demo_scenario import verify_pricing_demo
        from apps.costing.run_test_data import cleanup
        cleanup()
        Organization.objects.create(code="INTERNAL", name="Công ty kiểm thử")
        self.costing = verify_demo(seed_demo(), smoke=False)
        self.pricing = verify_pricing_demo()
        self.folder = TemporaryDirectory()
        self.policy = override_settings(DEBUG=False, STATIC_ROOT=self.folder.name,
            STATICFILES_FINDERS=["config.staticfiles.BuiltAssetFinder", "django.contrib.staticfiles.finders.AppDirectoriesFinder"],
            SECURE_SSL_REDIRECT=False, CSRF_COOKIE_SECURE=False,
            MIDDLEWARE=[settings.MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *settings.MIDDLEWARE[1:]],
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                      "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}},
            WHITENOISE_AUTOREFRESH=False, WHITENOISE_USE_FINDERS=False, WHITENOISE_ALLOW_ALL_ORIGINS=False)
        self.policy.enable()
        call_command("collectstatic", interactive=False, verbosity=0)
        from waitress import create_server
        self.server = create_server(get_wsgi_application(), host="127.0.0.1", port=0, threads=4,
                                    expose_tracebacks=False, asyncore_loop_timeout=0.1)
        self.thread = Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.effective_port}"

    def tearDown(self):
        from waitress import wasyncore
        from apps.costing.run_test_data import cleanup
        self.server.task_dispatcher.shutdown()
        wasyncore.close_all(self.server._map)
        self.thread.join(timeout=5)
        self.policy.disable()
        self.folder.cleanup()
        cleanup()
        super().tearDown()

    def test_production_like_http_static_csrf_errors_and_golden_history(self):
        from scripts.smoke_production import smoke
        from apps.core.models import CostingRun, PriceScenario
        from apps.costing.demo_verification import stored_fingerprint
        historical_run = CostingRun.objects.get(pk=self.costing["golden"]["id"])
        report = smoke(self.base_url, costing_run=historical_run.public_id,
            costing_line=historical_run.costingrunline_set.order_by("pk").first().pk,
            pricing_scenario=self.pricing["scenario_id"])
        self.assertTrue(report["passed"], report)
        self.assertEqual(static_errors(), [])
        with urlopen(self.base_url + "/product/items/") as response:
            html = response.read().decode()
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        paths = json.loads(Path(self.folder.name, "staticfiles.json").read_text())["paths"]
        with urlopen(Request(self.base_url + "/static/" + paths["css/app.css"], headers={"Accept-Encoding": "gzip"})) as response:
            self.assertIn("immutable", response.headers["Cache-Control"])
            self.assertEqual(response.headers["Content-Encoding"], "gzip")
        for path, method, status in (("/khong-ton-tai/", "GET", 404), ("/master-data/cost-elements/create/", "POST", 403)):
            with self.assertRaises(HTTPError) as captured:
                urlopen(Request(self.base_url + path, method=method, data=b"" if method == "POST" else None))
            self.assertEqual(captured.exception.code, status)
            body = captured.exception.read().decode()
            self.assertNotIn("Traceback", body)
            self.assertIn(paths["css/app.css"], body)
        with patch("apps.master_data.views.require_access", side_effect=OperationalError("password=do-not-expose")):
            with self.assertRaises(HTTPError) as captured:
                urlopen(self.base_url + "/master-data/cost-elements/")
            self.assertEqual(captured.exception.code, 500)
            body = captured.exception.read().decode()
            self.assertNotIn("do-not-expose", body)
            self.assertIn("Đã xảy ra lỗi", body)
            self.assertIn(paths["css/app.css"], body)
        run = CostingRun.objects.get(pk=self.costing["golden"]["id"])
        self.assertEqual(stored_fingerprint(run), self.costing["historical_fingerprint"])
        self.assertEqual(Decimal(self.costing["golden"]["comparisons"]["UNIT_COST"]["actual"]), Decimal("58300"))
        self.assertEqual(PriceScenario.objects.get(pk=self.pricing["scenario_id"]).status, "CALCULATED")
        if os.environ.get("COSTING_BROWSER_TESTS") == "1":
            from playwright.sync_api import sync_playwright, expect
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(locale="vi-VN", viewport={"width": 1366, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(self.base_url + "/master-data/cost-elements/")
                page.wait_for_function("window.Alpine !== undefined && window.htmx !== undefined")
                self.assertEqual(page.locator("body").evaluate("el => getComputedStyle(el).fontSize"), "14px")
                page.locator("input[name=q]").fill("__ABSENT_PRODUCTION__")
                expect(page).to_have_url(__import__('re').compile("q=__ABSENT_PRODUCTION__"))
                expect(page.locator("#cost-element-table")).to_contain_text("Không có kết quả phù hợp.")
                self.assertEqual(errors, [])
                screenshot = settings.BASE_DIR / "artifacts/screenshots/production-waitress.png"
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot), full_page=True)
                browser.close()
        report.update(debug=False, server="waitress", static="whitenoise-manifest",
            browser=os.environ.get("COSTING_BROWSER_TESTS") == "1", golden_costing=self.costing,
            golden_pricing=self.pricing, errors_safe=True, csrf_enforced=True)
        report_path = settings.BASE_DIR / "artifacts/production-http-smoke.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
