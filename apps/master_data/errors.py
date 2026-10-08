from uuid import uuid4

from django.shortcuts import render


def error_response(request, *, status, title, message, trace_id=None):
    is_partial = request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"
    template = "partials/error.html" if is_partial else "base/error.html"
    # Avoid another database/context query when the original error is a DB outage.
    from .access import Workspace
    if status in (500, 503):
        request._costing_workspace = Workspace(None)
    return render(request, template, {
        "page_title": title, "error_message": message, "trace_id": trace_id,
    }, status=status)


def permission_denied(request, exception):
    message = "Bạn không có quyền thực hiện thao tác này."
    return error_response(request, status=403, title="Không đủ quyền truy cập", message=message)


def csrf_failure(request, reason=""):
    # Keep CSRF enforcement; never expose its internal reason or request token.
    response = error_response(request, status=403, title="Không thể gửi yêu cầu",
        message="Yêu cầu không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang rồi thử lại.",
        trace_id=getattr(request, "trace_id", None))
    response["X-Error-Code"] = "CSRF_FAILED"
    return response


def bad_request(request, exception):
    return error_response(request, status=400, title="Yêu cầu không hợp lệ",
        message="Yêu cầu không hợp lệ. Vui lòng kiểm tra địa chỉ và dữ liệu đã nhập.",
        trace_id=getattr(request, "trace_id", None))


def configuration_error(request, exception):
    return error_response(request, status=503, title="Cấu hình công ty chưa hợp lệ", message=str(exception), trace_id=getattr(request, "trace_id", None))


def not_found(request, exception):
    resource = getattr(request, "costing_resource_label", "dữ liệu")
    return error_response(request, status=404, title="Không tìm thấy", message=f"Không tìm thấy {resource}.")


def server_error(request):
    return error_response(request, status=500, title="Không thể xử lý yêu cầu", message="Đã xảy ra lỗi khi xử lý yêu cầu.", trace_id=getattr(request, "trace_id", str(uuid4())))
