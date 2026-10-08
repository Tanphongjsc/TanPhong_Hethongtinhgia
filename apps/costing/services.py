"""Atomic scheme/version/line writes; never create or evaluate a Costing Run."""
from copy import deepcopy
from hashlib import sha256
import json
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone
from apps.core.models import CostingScheme, CostingSchemeVersion, CostingSchemeLine, CostElement, FormulaVersion, Organization, RuleTable
from apps.master_data.access import require_write_access
from apps.formula_engine.engine import ELEMENT_RELATIONS, FORMULA_RELATIONS
from apps.formula_engine.errors import FormulaError
from .constants import SCHEME_FIELDS, VERSION_FIELDS, LINE_FIELDS, COPY_FIELDS
from .configuration import analyze_formula, validate_costing_scheme
from .validators import normalize_values, validate_scheme, validate_version, validate_line, ensure_editable


def _database_error(error):
    state = getattr(error.__cause__, "sqlstate", None)
    name = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "")
    messages = {"uq_costing_scheme": {"code": "Mã phương án đã tồn tại."},
        "uq_costing_scheme_line_code": {"line_code": "Mã dòng đã tồn tại trong phiên bản này."},
        "uq_costing_scheme_line_order": {"display_order": "Thứ tự đã tồn tại trong phiên bản này."},
        "uq_costing_scheme_version": "Số phiên bản đã tồn tại. Vui lòng tải lại và thử lại."}
    if name in messages: raise ValidationError(messages[name]) from None
    if state == "P0001": raise ValidationError("Phiên bản đã được chốt; hãy tạo phiên bản mới.") from None
    if state in ("23502", "23503", "23505", "23514", "22003"):
        raise ValidationError("Dữ liệu không còn hợp lệ hoặc vượt giới hạn lưu trữ. Vui lòng kiểm tra và thử lại.") from None
    raise error


def _lock(workspace, scheme=None, version=None):
    # Same compatibility-row lock as Formula Engine graph writes. This is not
    # identity/membership resolution or a new company workflow.
    Organization.objects.select_for_update().get(pk=workspace.organization.pk)
    try:
        if scheme: scheme = CostingScheme.objects.select_for_update().get(pk=scheme.pk, organization=workspace.organization)
        if version: version = CostingSchemeVersion.objects.select_for_update().get(pk=version.pk, scheme=scheme)
    except (CostingScheme.DoesNotExist, CostingSchemeVersion.DoesNotExist):
        raise ValidationError("Không tìm thấy phương án hoặc phiên bản của hệ thống.") from None
    return scheme, version


def _assign(record, values):
    for name, value in values.items(): setattr(record, name, value)
    record.full_clean(exclude=("condition_jsonb",) if isinstance(record, CostingSchemeLine) else (), validate_unique=False, validate_constraints=False)


def _references(rows, organization):
    # Refresh stale objects in stable, batched lock order before validating writes.
    for model, name, relations in ((CostElement, "cost_element", ELEMENT_RELATIONS), (RuleTable, "rule_table", ()),
        (FormulaVersion, "formula_version", ("formula", *("formula__" + value for value in FORMULA_RELATIONS)))):
        refs = [row[name] for row in rows if row.get(name) is not None]
        if not refs: continue
        if any(not isinstance(ref, model) for ref in refs): raise ValidationError({name: "Tham chiếu không hợp lệ."})
        query = model.objects.filter(pk__in={ref.pk for ref in refs})
        query = query.filter(**{"formula__organization" if model is FormulaVersion else "organization": organization})
        lookup = {ref.pk: ref for ref in query.select_related(*relations).select_for_update(of=("self",)).order_by("pk")}
        for row in rows:
            if row.get(name) is not None:
                if row[name].pk not in lookup: raise ValidationError({name: "Tham chiếu không còn tồn tại hoặc không thuộc dữ liệu hệ thống."})
                row[name] = lookup[row[name].pk]


def _new_version(*, workspace, scheme, data, source=None):
    values = normalize_values({name: data.get(name) for name in VERSION_FIELDS}, uppercase=())
    validate_version(data=values)
    number = max(CostingSchemeVersion.objects.filter(scheme=scheme).aggregate(number=Max("version_no"))["number"] or 0, 0) + 1
    if number > 2147483647: raise ValidationError("Không thể tăng số phiên bản. Vui lòng kiểm tra dữ liệu.")
    version = CostingSchemeVersion(scheme=scheme, version_no=number, status="DRAFT", created_by=None, approved_by=None)
    _assign(version, values); version.save(force_insert=True)
    if source:
        # Clone the exact definition, including unsupported legacy conditions and
        # inactive references. Their diagnostics stay visible in the new Draft.
        rows = CostingSchemeLine.objects.filter(scheme_version=source).order_by("display_order", "pk").values(*COPY_FIELDS)
        copies = []
        for row in rows:
            for name in ("cost_element", "formula_version", "rule_table"):
                row[f"{name}_id"] = row.pop(name)
            row["condition_jsonb"] = deepcopy(row["condition_jsonb"])
            copies.append(CostingSchemeLine(scheme_version=version, **row))
        CostingSchemeLine.objects.bulk_create(copies, batch_size=200)
    return version


def save_scheme(*, workspace, data, instance=None, initial_version=None):
    require_write_access(workspace, resource="scheme", editing=instance is not None)
    try:
        with transaction.atomic():
            scheme, _ = _lock(workspace, instance)
            scheme = scheme or CostingScheme(organization=workspace.organization)
            uppercase = () if instance and scheme.costingschemeversion_set.exclude(status__in=("DRAFT", "IN_REVIEW")).exists() else ("code",)
            values = normalize_values({name: data.get(name) for name in SCHEME_FIELDS}, uppercase=uppercase)
            validate_scheme(data=values, organization=workspace.organization, instance=scheme)
            _assign(scheme, values); scheme.updated_at = timezone.now()
            scheme.save(force_insert=instance is None, force_update=instance is not None)
            if instance is None:
                if initial_version is None: raise ValidationError("Vui lòng nhập cấu hình phiên bản đầu tiên.")
                _new_version(workspace=workspace, scheme=scheme, data=initial_version)
            return scheme
    except DatabaseError as error: _database_error(error)


def save_version(*, workspace, scheme, data, instance=None, source=None):
    require_write_access(workspace, resource="scheme_version", editing=instance is not None)
    try:
        with transaction.atomic():
            scheme, version = _lock(workspace, scheme, instance or source)
            if instance is None: return _new_version(workspace=workspace, scheme=scheme, data=data, source=version)
            ensure_editable(version)
            values = normalize_values({name: data.get(name) for name in VERSION_FIELDS}, uppercase=())
            validate_version(data=values)
            _assign(version, values); version.content_hash = None; version.save(force_update=True)
            return version
    except DatabaseError as error: _database_error(error)


def save_line(*, workspace, scheme, version, data, instance=None):
    require_write_access(workspace, resource="scheme_line", editing=instance is not None)
    try:
        with transaction.atomic():
            scheme, version = _lock(workspace, scheme, version)
            ensure_editable(version)
            line = CostingSchemeLine(scheme_version=version)
            if instance:
                try: line = CostingSchemeLine.objects.select_for_update().get(pk=instance.pk, scheme_version=version)
                except CostingSchemeLine.DoesNotExist: raise ValidationError("Không tìm thấy dòng cấu hình.") from None
            values = normalize_values({name: data.get(name) for name in LINE_FIELDS}, uppercase=("line_code",))
            _references([values], workspace.organization)
            validate_line(data=values, organization=workspace.organization, instance=line, version=version)
            if values["source_mode"] == "FORMULA":
                try: analyze_formula(organization=workspace.organization, version=values["formula_version"], target=values["cost_element"], effective_date=version.effective_from)
                except FormulaError as error: raise ValidationError({"formula_version": error.describe(values["formula_version"].expression)}) from None
            # Keep references for the selected source only. Legacy condition JSON
            # and fields not exposed in this form remain unchanged.
            current = {"SYSTEM": "system_resolver_code", "FORMULA": "formula_version", "LOOKUP": "rule_table", "EXTERNAL": "external_adapter_code"}.get(values["source_mode"])
            for name in ("system_resolver_code", "formula_version", "rule_table", "external_adapter_code"):
                if name != current: values[name] = None
            _assign(line, values); line.save(force_insert=instance is None, force_update=instance is not None)
            version.content_hash = None; version.save(update_fields=["content_hash"])
            return line
    except DatabaseError as error: _database_error(error)


def remove_line(*, workspace, scheme, version, instance):
    require_write_access(workspace, resource="scheme_line", editing=True)
    if not workspace.permissions.can_delete_scheme_line: raise ValidationError("Thao tác xóa chưa được hỗ trợ.")
    try:
        with transaction.atomic():
            scheme, version = _lock(workspace, scheme, version)
            ensure_editable(version)
            deleted, _ = CostingSchemeLine.objects.filter(pk=instance.pk, scheme_version=version).delete()
            if not deleted: raise ValidationError("Không tìm thấy dòng cấu hình.")
            version.content_hash = None; version.save(update_fields=["content_hash"])
    except DatabaseError as error: _database_error(error)


def activate_version(*, workspace, scheme, version):
    require_write_access(workspace, resource="scheme_version", editing=True)
    try:
        with transaction.atomic():
            scheme, version = _lock(workspace, scheme, version)
            ensure_editable(version)
            if not version.effective_from: raise ValidationError("Vui lòng đặt ngày bắt đầu hiệu lực trước khi kích hoạt.")
            report = validate_costing_scheme(organization=workspace.organization, scheme=scheme, version=version)
            if report.errors: raise ValidationError(report.errors)
            # Hash only this version's definition, never results or price snapshots.
            content = {"version": {name: getattr(version, name) for name in VERSION_FIELDS},
                "lines": list(CostingSchemeLine.objects.filter(scheme_version=version).order_by("display_order", "pk").values(*COPY_FIELDS))}
            version.content_hash = sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()
            version.status = "EFFECTIVE"
            version.approved_by = None; version.approved_at = None
            version.save(update_fields=["content_hash", "status", "approved_by", "approved_at"])
            return version
    except DatabaseError as error: _database_error(error)
