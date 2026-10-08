document.addEventListener('htmx:configRequest', (event) => {
  if (['post', 'put', 'patch', 'delete'].includes(event.detail.verb)) {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    if (token) event.detail.headers['X-CSRFToken'] = token;
  }
});
document.addEventListener('htmx:beforeRequest', () => {
  document.getElementById('request-error').hidden = true;
});
document.addEventListener('htmx:responseError', (event) => {
  const notice = document.getElementById('request-error');
  const status = event.detail.xhr.status;
  notice.textContent = event.detail.xhr.getResponseHeader('X-Error-Code') === 'CSRF_FAILED'
    ? 'Yêu cầu không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang rồi thử lại.'
    : status === 403 ? 'Bạn không có quyền thực hiện thao tác này.'
    : status === 404 ? `Không tìm thấy ${document.querySelector('main[data-resource-label]')?.dataset.resourceLabel || 'dữ liệu'}.` : 'Đã xảy ra lỗi khi xử lý yêu cầu.';
  const trace = event.detail.xhr.getResponseHeader('X-Trace-ID');
  if (trace) notice.textContent += ` Mã tham chiếu: ${trace}`;
  notice.hidden = false;
});
document.addEventListener('htmx:sendError', () => {
  const notice = document.getElementById('request-error');
  notice.textContent = 'Không thể kết nối. Vui lòng thử lại.';
  notice.hidden = false;
});
