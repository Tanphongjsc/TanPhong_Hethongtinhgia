from apps.master_data.presentation import display_label

VERSION_STATUSES = tuple((code, display_label(code)) for code in ("DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED"))
VALIDATION_STATUSES = (("NOT_VALIDATED", "Chưa kiểm tra"), ("VALID", "Hợp lệ"), ("INVALID", "Không hợp lệ"))
HEADER_FIELDS = ("code", "name", "description", "output_element", "is_active")
VERSION_FIELDS = ("expression", "effective_from", "effective_to", "change_reason")
