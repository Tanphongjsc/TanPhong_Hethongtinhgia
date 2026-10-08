"""Deployment-only checks for built release assets; no database writes."""
import json
from pathlib import Path
from django.conf import settings
from django.core.checks import Error, Tags, register

REQUIRED_STATIC = ("css/app.css", "js/app.js", "js/htmx-config.js", "js/alpine-components.js",
    "vendor/htmx/htmx.min.js", "vendor/alpine/alpine.min.js", "vendor/alpine/focus.min.js")


def static_errors():
    root = Path(settings.STATIC_ROOT).resolve()
    try:
        paths = json.loads((root / "staticfiles.json").read_text(encoding="utf-8"))["paths"]
        for name in REQUIRED_STATIC:
            target = (root / paths[name]).resolve()
            if not target.is_relative_to(root) or not target.is_file() or not target.stat().st_size:
                raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        return [Error("Static production thiếu hoặc manifest không hợp lệ. Build frontend và chạy collectstatic.", id="costing.E002")]
    return []


@register(Tags.security, deploy=True)
def production_checks(app_configs=None, **kwargs):
    if settings.APP_ENV not in ("production", "staging"):
        return []
    return static_errors()
