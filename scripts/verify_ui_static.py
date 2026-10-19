"""Exercise the existing production static pipeline with no database access."""
import json
import os
from pathlib import Path
import secrets
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
target = (root / 'artifacts/ui-redesign/collected-static').resolve()
if not target.is_relative_to(root) or target == (root / 'static').resolve():
    raise RuntimeError('Static audit output must stay inside workspace artifacts.')

# Process-local dummy configuration; production does not read .env. These values
# are neither real credentials nor a production deployment configuration.
os.environ.update(APP_ENV='production', DJANGO_SETTINGS_MODULE='config.production',
                  DJANGO_SECRET_KEY=secrets.token_urlsafe(64), DJANGO_DEBUG='False',
                  DJANGO_ALLOWED_HOSTS='localhost', DJANGO_CSRF_TRUSTED_ORIGINS='',
                  APP_TRANSPORT='private_http', APP_TRUSTED_PROXY='',
                  DATABASE_URL='', DB_NAME='ui_static_audit', DB_USER='ui_static_audit',
                  DB_PASSWORD='not-used', DB_HOST='127.0.0.1', DB_PORT='55432',
                  DB_SSLMODE='require', DJANGO_STATIC_ROOT=str(target))

import django
django.setup()
from django.core.management import call_command
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import connections
from django.template.loader import render_to_string


def no_database(*args, **kwargs):
    raise RuntimeError('Static verification must never access a database.')


for connection in connections.all():
    connection.cursor = no_database
call_command('collectstatic', interactive=False, clear=True, verbosity=1)
assets = ('css/app.css', 'js/alpine-components.js', 'vendor/lucide/sprite.svg',
          'vendor/fonts/inter-latin-wght-normal.woff2',
          'vendor/fonts/inter-vietnamese-wght-normal.woff2')
urls = {name: staticfiles_storage.url(name) for name in assets}
for name in assets:
    assert (target / staticfiles_storage.stored_name(name)).exists(), name
assert not (target / 'src/tailwind.css').exists()
html = render_to_string('base/base.html')
assert urls['css/app.css'] in html and urls['js/alpine-components.js'] in html
css = (target / staticfiles_storage.stored_name('css/app.css')).read_text(encoding='utf-8')
for font in assets[-2:]:
    assert Path(staticfiles_storage.stored_name(font)).name in css, font
report = {'production_storage': staticfiles_storage.__class__.__name__,
          'database_queries': 0, 'manifest_urls': urls, 'raw_tailwind_excluded': True}
(root / 'artifacts/ui-redesign/static-verification.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
