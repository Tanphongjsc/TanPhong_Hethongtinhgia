#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Render supplies secrets as process environment. Never source a developer .env.
export APP_ENV=production
export DJANGO_SETTINGS_MODULE=config.production

python -m pip install -r requirements-render.txt
npm ci
npm run build
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level=ERROR
