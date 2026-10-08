"""Single company resolution; Organization remains an internal DB mapping."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.core.models import Organization


class ConfigurationError(ImproperlyConfigured):
    """Actionable deployment/data configuration errors, safe for the UI."""


def get_default_organization():
    if settings.APP_MODE != "single_company":
        raise ConfigurationError("APP_MODE phải là single_company. Ứng dụng hiện không hỗ trợ chế độ khác.")
    configured = settings.DEFAULT_ORGANIZATION_ID
    active = Organization.objects.filter(is_active=True)
    if configured not in (None, ""):
        try:
            identifier = int(configured)
            if not 0 < identifier < 2**63:
                raise ValueError
        except (ValueError, TypeError):
            raise ConfigurationError("DEFAULT_ORGANIZATION_ID phải là ID số nguyên dương hợp lệ.") from None
        try:
            return active.get(pk=identifier)
        except Organization.DoesNotExist:
            raise ConfigurationError("DEFAULT_ORGANIZATION_ID không tồn tại hoặc công ty đã ngừng hoạt động. Vui lòng kiểm tra cấu hình.") from None
    organizations = list(active.order_by("pk")[:2])
    if not organizations:
        raise ConfigurationError("Chưa có công ty hoạt động trong cơ sở dữ liệu. Vui lòng bổ sung dữ liệu công ty đang hoạt động để sử dụng hệ thống.")
    if len(organizations) > 1:
        raise ConfigurationError("Có nhiều công ty hoạt động trong cơ sở dữ liệu. Vui lòng cấu hình DEFAULT_ORGANIZATION_ID để xác định công ty sử dụng hệ thống.")
    return organizations[0]
