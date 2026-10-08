"""Minimal infrastructure probes. No engine, business writes or workspace queries."""
import logging
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def database_ready():
    with connection.cursor() as cursor:
        if settings.APP_ENV in ("production", "staging"):
            cursor.execute("SELECT current_schema(), current_setting('search_path'), to_regclass('costing.cost_element') IS NOT NULL")
            schema, search_path, table_exists = cursor.fetchone()
            return schema == "costing" and search_path.replace(" ", "").replace('"', '') == "costing,public" and table_exists
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


@require_GET
def health(request):
    request.get_host()
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    request.get_host()
    try:
        available = database_ready()
    except Exception:
        available = False
    if not available:
        logger.warning("database_not_ready", extra={"stage": "readiness", "trace_id": getattr(request, "trace_id", None)})
    return JsonResponse({"status": "ok" if available else "unavailable"}, status=200 if available else 503)
