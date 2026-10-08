import logging
from time import perf_counter
from uuid import uuid4
from config.logging import request_trace

from django.conf import settings

logger = logging.getLogger(__name__)


class CostingRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.trace_id = str(uuid4())
        token = request_trace.set(request.trace_id)
        started = perf_counter()
        try:
            response = self.get_response(request)
            response["X-Trace-ID"] = request.trace_id
            response["Cache-Control"] = "private, no-store"
            logger.info("http_request", extra={"method": request.method, "path": request.path,
                "status": response.status_code, "duration_ms": round((perf_counter() - started) * 1000, 3)})
            return response
        finally:
            request_trace.reset(token)

    def process_exception(self, request, exception):
        from .company_context import ConfigurationError
        if isinstance(exception, ConfigurationError):
            from .errors import configuration_error
            return configuration_error(request, exception)
        if settings.DEBUG:
            return None
        from django.core.exceptions import PermissionDenied
        from django.http import Http404
        if isinstance(exception, (PermissionDenied, Http404)):
            return None
        logger.exception("Costing request failed trace_id=%s", request.trace_id)
        from .errors import server_error
        return server_error(request)
