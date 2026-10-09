"""Render settings/transport and DATABASE_URL safety without remote DB writes."""
import json
import logging
import os
import runpy
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import quote

import environ
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.database import database_config
from config.logging import JsonFormatter
from .test_deployment import safe_environment


class DatabaseURLTests(SimpleTestCase):
    def config(self, url, **changes):
        with patch.dict(os.environ, safe_environment(DATABASE_URL=url, **changes), clear=True):
            return database_config(environ.Env())

    def test_reserved_password_decoded_once_and_legacy_credentials_ignored(self):
        password = "test-only:p@ss#?&/%25+ unicode đ"
        config = self.config(f"postgresql://role.project:{quote(password, safe='')}@pooler.example:5432/postgres?sslmode=require")
        self.assertEqual(config["PASSWORD"], password)
        self.assertEqual(config["USER"], "role.project")
        self.assertEqual(config["HOST"], "pooler.example")
        self.assertEqual(config["PORT"], 5432)
        self.assertEqual(config["OPTIONS"]["options"], "-c search_path=costing,public")
        self.assertTrue(config["CONN_HEALTH_CHECKS"])

    def test_postgres_alias_default_port_and_verified_ssl(self):
        config = self.config("postgres://role:secret@db.example/postgres?sslmode=verify-full&sslrootcert=%2Fetc%2Fca.pem")
        self.assertEqual(config["PORT"], 5432)
        self.assertEqual(config["OPTIONS"]["sslmode"], "verify-full")
        self.assertEqual(config["OPTIONS"]["sslrootcert"], "/etc/ca.pem")

    def test_legacy_connection_retained_when_url_absent(self):
        config = self.config("")
        self.assertEqual((config["HOST"], config["PORT"]), ("127.0.0.1", "55432"))

    def test_invalid_urls_fail_without_exposing_credentials(self):
        for url in ("sqlite:///unused", "postgresql://role:secret@host:bad/postgres",
                    "postgresql://role:secret@host:0/postgres",
                    "postgresql://role:secret@host/postgres#fragment",
                    "postgresql://role:raw@secret@host/postgres", "postgresql://role:secret@host/",
                    "postgresql://role:sec%ret@host/postgres", "postgresql://role:secret@host/postgres?sslmode=require&sslmode=disable",
                    "postgresql://role:secret@host/postgres?options=-c%20search_path%3Dpublic",
                    "postgresql://role:secret@host/postgres?host=other"):
            with self.subTest(url_shape=url.split(":", 1)[0]), self.assertRaises(ImproperlyConfigured) as error:
                self.config(url)
            self.assertNotIn("secret", str(error.exception))

    def test_database_url_encoded_and_decoded_passwords_are_redacted(self):
        password = "test-secret@?#%25"
        encoded = quote(password, safe="")
        url = f"postgresql://role:{encoded}@host/postgres"
        with patch.dict(os.environ, DATABASE_URL=url):
            record = logging.LogRecord("gunicorn.error", logging.ERROR, "", 0, f"Failed {url} {password} {encoded}", (), None)
            data = JsonFormatter().format(record)
        for secret in (url, password, encoded):
            self.assertNotIn(secret, data)
        self.assertIn("[REDACTED]", data)


class RenderSettingsTests(SimpleTestCase):
    def load(self, **changes):
        values = dict(APP_TRANSPORT="render_https", RENDER="true",
            RENDER_EXTERNAL_HOSTNAME="costing-test.onrender.com", DJANGO_ALLOWED_HOSTS=None,
            DATABASE_URL="postgresql://unused:isolated-password@127.0.0.1:55432/unused?sslmode=require")
        values.update(changes)
        environment = safe_environment(**values)
        code = '''import django,json
django.setup()
from django.conf import settings as s
from django.test import Client,RequestFactory,override_settings
from django.middleware.csrf import CsrfViewMiddleware,get_token
from django.http import HttpResponse
factory=RequestFactory()
secure=factory.get('/health/',HTTP_HOST='costing-test.onrender.com',HTTP_X_FORWARDED_PROTO='https')
plain=factory.get('/health/',HTTP_HOST='costing-test.onrender.com')
client=Client()
health=client.get('/health/',HTTP_HOST='costing-test.onrender.com',HTTP_X_FORWARDED_PROTO='https')
redirect=client.get('/product/items/',HTTP_HOST='costing-test.onrender.com')
token=get_token(secure)
post=factory.post('/unused',{'csrfmiddlewaretoken':token},HTTP_HOST='costing-test.onrender.com',HTTP_X_FORWARDED_PROTO='https',HTTP_ORIGIN='https://costing-test.onrender.com',HTTP_COOKIE='csrftoken='+secure.META['CSRF_COOKIE'])
rejected=CsrfViewMiddleware(lambda r:HttpResponse()).process_view(post,lambda r:HttpResponse(),(),{})
post.META['HTTP_ORIGIN']='https://untrusted.example'
post.csrf_processing_done=False
with override_settings(CSRF_FAILURE_VIEW=lambda request,reason='':HttpResponse(status=403)):
    bad=CsrfViewMiddleware(lambda r:HttpResponse()).process_view(post,lambda r:HttpResponse(),(),{})
print(json.dumps(dict(hosts=s.ALLOWED_HOSTS,origins=s.CSRF_TRUSTED_ORIGINS,debug=s.DEBUG,
secure=secure.is_secure(),plain_secure=plain.is_secure(),cookie=s.CSRF_COOKIE_SECURE,
proxy=s.SECURE_PROXY_SSL_HEADER,health=health.status_code,redirect=redirect.status_code,
location=redirect.get('Location'),csrf_valid=rejected is None,csrf_bad=bad.status_code,
ssl=s.DATABASES['default']['OPTIONS']['sslmode'])))
'''
        return subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR, env=environment,
                              capture_output=True, encoding="utf-8", timeout=20)

    def test_render_exact_host_https_health_and_csrf(self):
        result = self.load()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(data["hosts"], ["costing-test.onrender.com"])
        self.assertEqual(data["origins"], ["https://costing-test.onrender.com"])
        self.assertEqual(data["proxy"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertFalse(data["debug"])
        self.assertTrue(data["secure"])
        self.assertFalse(data["plain_secure"])
        self.assertTrue(data["cookie"])
        self.assertEqual(data["health"], 200)
        self.assertEqual(data["redirect"], 301)
        self.assertEqual(data["location"], "https://costing-test.onrender.com/product/items/")
        self.assertTrue(data["csrf_valid"])
        self.assertEqual(data["csrf_bad"], 403)

    def test_render_transport_rejected_off_platform_or_invalid_host(self):
        for changes in ({"RENDER": None}, {"RENDER_EXTERNAL_HOSTNAME": None},
                        {"RENDER_EXTERNAL_HOSTNAME": "https://costing-test.onrender.com"},
                        {"RENDER_EXTERNAL_HOSTNAME": "*.onrender.com"},
                        {"RENDER_EXTERNAL_HOSTNAME": "attacker.example"}, {"APP_TRUSTED_PROXY": "127.0.0.1"}):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.load(**changes).returncode, 0)

    def test_render_url_alone_without_legacy_credentials(self):
        result = self.load(**{f"DB_{field}": None for field in ("NAME", "USER", "PASSWORD", "HOST", "PORT")})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_url_cannot_disable_ssl(self):
        result = self.load(DATABASE_URL="postgresql://role:secret@host/postgres?sslmode=disable")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DB_SSLMODE", result.stderr)


class GunicornConfigTests(SimpleTestCase):
    def config(self, **changes):
        values = dict(APP_TRANSPORT="render_https", PORT="19001")
        values.update(changes)
        environment = safe_environment(**values)
        with patch.dict(os.environ, environment, clear=True):
            return runpy.run_path(str(settings.BASE_DIR / "config/gunicorn.py"))

    def test_bind_and_conservative_concurrency(self):
        config = self.config()
        self.assertEqual(config["bind"], "0.0.0.0:19001")
        self.assertEqual((config["workers"], config["threads"], config["timeout"]), (1, 4, 30))
        self.assertFalse(config["preload_app"])
        self.assertEqual(config["secure_scheme_headers"], {})
        self.assertEqual(config["forwarder_headers"], "")
        self.assertIsNone(config["accesslog"])
        self.assertEqual(config["logconfig_dict"]["loggers"]["gunicorn.access"]["handlers"], ["null"])

    def test_configurable_workers_threads_timeout(self):
        config = self.config(WEB_CONCURRENCY="2", GUNICORN_THREADS="2", GUNICORN_TIMEOUT="45")
        self.assertEqual((config["workers"], config["threads"], config["timeout"]), (2, 2, 45))

    def test_invalid_server_values_rejected(self):
        for changes in ({"PORT": "0"}, {"PORT": "oops"}, {"WEB_CONCURRENCY": "0"},
                        {"GUNICORN_THREADS": "64"}, {"GUNICORN_TIMEOUT": "600"}, {"APP_ENV": "development"},
                        {"DJANGO_SETTINGS_MODULE": "config.settings"}, {"APP_TRANSPORT": "private_http"}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                self.config(**changes)

    def test_worker_preflight_checks_static_database_and_closes_connections(self):
        config = self.config()
        worker = type("Worker", (), {"log": logging.getLogger("gunicorn.error")})()
        with patch("config.checks.static_errors", return_value=[]), patch("config.health.database_ready", return_value=True), patch("apps.master_data.company_context.get_default_organization") as company, patch("django.db.connections.close_all") as close:
            config["post_worker_init"](worker)
        company.assert_called_once()
        close.assert_called_once()
        with patch("config.checks.static_errors", return_value=[]), patch("config.health.database_ready", return_value=False), patch("django.db.connections.close_all") as close, self.assertRaises(ImproperlyConfigured):
            config["post_worker_init"](worker)
        close.assert_called_once()
