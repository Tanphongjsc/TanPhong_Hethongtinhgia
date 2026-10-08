"""Transactions, stored AST/dependencies, version cloning and guarded activation."""
from decimal import Decimal, InvalidOperation, localcontext
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone
from apps.core.models import CostElement, Formula, FormulaDependency, FormulaTestCase, FormulaVersion, Organization
from apps.master_data.access import require_write_access
from .ast_nodes import fingerprint
from .constants import HEADER_FIELDS, VERSION_FIELDS
from .engine import build_plan
from .errors import FormulaError
from .validator import NUMERIC
from .evaluator import Budget
from .limits import limits


def ensure_editable(version):
    if version.status not in ("DRAFT", "IN_REVIEW"):
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.")


def validate_period(data):
    if data.get("effective_to") and not data.get("effective_from"):
        raise ValidationError({"effective_from": "Vui lòng nhập ngày bắt đầu hiệu lực."})
    if data.get("effective_to") and data["effective_to"] <= data["effective_from"]:
        raise ValidationError({"effective_to": "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực."})


def validate_header(*, data, organization, instance=None):
    code = (data.get("code") or "").strip()
    if not instance or instance._state.adding: code = code.upper()
    from .parser import IDENTIFIER
    existing_code = instance and not instance._state.adding and code == instance.code
    if not existing_code and (not code or not IDENTIFIER.fullmatch(code) or code in ("TRUE", "FALSE", "AND", "OR", "NOT")):
        raise ValidationError({"code": "Mã phải bắt đầu bằng chữ cái, chỉ gồm chữ cái, số và dấu gạch dưới."})
    if not (data.get("name") or "").strip():
        raise ValidationError({"name": "Vui lòng nhập tên công thức."})
    if Formula.objects.filter(organization=organization, code=code).exclude(pk=instance.pk if instance else None).exists():
        raise ValidationError({"code": "Mã công thức đã tồn tại."})
    output = data.get("output_element")
    if output and (output.organization_id != organization.pk or (not output.is_active and (not instance or instance.output_element_id != output.pk))):
        raise ValidationError({"output_element": "Vui lòng chọn phần tử chi phí đang hoạt động của hệ thống."})
    if instance and not instance._state.adding and (code != instance.code or getattr(output, "pk", None) != instance.output_element_id):
        raise ValidationError("Mã và phần tử đầu ra là định danh ổn định; không đổi khi chỉnh sửa công thức.")


def _db_error(error):
    state = getattr(error.__cause__, "sqlstate", None)
    name = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "")
    if name == "uq_formula": raise ValidationError({"code": "Mã công thức đã tồn tại."}) from None
    if state == "P0001": raise ValidationError("Phiên bản đã được chốt; hãy tạo phiên bản mới.") from None
    if state in ("23502", "23503", "23505", "23514", "22003"):
        raise ValidationError("Dữ liệu không còn hợp lệ hoặc vượt giới hạn lưu trữ. Vui lòng kiểm tra và thử lại.") from None
    raise error


def _lock(workspace, formula=None):
    # Serialize definition/publish graph changes through the existing compatibility
    # row; no membership, identity, organization selection or user workflow.
    Organization.objects.select_for_update().get(pk=workspace.organization.pk)
    if formula:
        try: return Formula.objects.select_for_update(of=("self",)).select_related("output_element").get(pk=formula.pk, organization=workspace.organization)
        except Formula.DoesNotExist: raise ValidationError("Không tìm thấy công thức.") from None


def _persist_analysis(version, plan):
    version.ast_jsonb, version.ast_hash = fingerprint(plan.roots[plan.root_code])
    version.validation_status = "VALID"
    version.validation_message = "Cú pháp, kiểu dữ liệu, đơn vị và đồ thị phụ thuộc hợp lệ."
    version.save()
    FormulaDependency.objects.filter(formula_version=version).delete()
    unique = {}
    for _, (kind, target) in plan.bindings[plan.root_code].items(): unique[(kind, target.pk)] = target
    FormulaDependency.objects.bulk_create([FormulaDependency(formula_version=version, dependency_kind=kind, dependency_code=target.code,
        depends_on_element=target if kind == "ELEMENT" else None, depends_on_formula=target if kind == "FORMULA" else None)
        for (kind, _), target in unique.items()])


def save_formula(*, workspace, data, version_data=None, instance=None):
    require_write_access(workspace, resource="formula", editing=instance is not None)
    try:
        with transaction.atomic():
            record = _lock(workspace, instance) if instance else (_lock(workspace) or Formula(organization=workspace.organization))
            values = {key: data.get(key) for key in HEADER_FIELDS}
            values.update(code=record.code if instance else (values["code"] or "").strip().upper(), name=(values["name"] or "").strip(), description=(values["description"] or "").strip() or None)
            if values["output_element"]:
                values["output_element"] = CostElement.objects.select_for_update().get(pk=values["output_element"].pk, organization=workspace.organization)
            validate_header(data=values, organization=workspace.organization, instance=record)
            for key, value in values.items(): setattr(record, key, value)
            record.full_clean(validate_unique=False, validate_constraints=False)
            record.save()
            if instance is None:
                _create_version(workspace, record, version_data or {})
            return record
    except FormulaError as error: raise ValidationError({"expression": error.describe((version_data or {}).get("expression", ""))}) from None
    except CostElement.DoesNotExist: raise ValidationError({"output_element": "Phần tử chi phí không còn tồn tại."}) from None
    except DatabaseError as error: _db_error(error)


def _create_version(workspace, formula, data):
    validate_period(data)
    plan = build_plan(organization=workspace.organization, formula=formula, expression=data.get("expression", ""))
    number = max(0, FormulaVersion.objects.filter(formula=formula).aggregate(number=Max("version_no"))["number"] or 0) + 1
    if number > 2147483647: raise ValidationError("Số phiên bản vượt giới hạn lưu trữ.")
    version = FormulaVersion(formula=formula, version_no=number, **{key: data.get(key) or None for key in VERSION_FIELDS})
    version.status = "DRAFT"
    _persist_analysis(version, plan)
    Formula.objects.filter(pk=formula.pk).update(updated_at=timezone.now())
    return version


def save_version(*, workspace, formula, data, instance=None, source=None):
    require_write_access(workspace, resource="formula_version", editing=instance is not None)
    try:
        with transaction.atomic():
            record = _lock(workspace, formula)
            if source:
                source = FormulaVersion.objects.get(pk=source.pk, formula=record)
            if instance is None:
                # Test cases belong to the identity and are reused, never duplicated.
                return _create_version(workspace, record, data)
            version = FormulaVersion.objects.select_for_update().get(pk=instance.pk, formula=record)
            ensure_editable(version); validate_period(data)
            plan = build_plan(organization=workspace.organization, formula=record, expression=data.get("expression", ""))
            for key in VERSION_FIELDS: setattr(version, key, data.get(key) or None)
            _persist_analysis(version, plan)
            Formula.objects.filter(pk=record.pk).update(updated_at=timezone.now())
            return version
    except FormulaError as error: raise ValidationError({"expression": error.describe(data.get("expression", ""))}) from None
    except FormulaVersion.DoesNotExist: raise ValidationError("Không tìm thấy phiên bản.") from None
    except DatabaseError as error: _db_error(error)


def test_inputs(plan, stored):
    if not isinstance(stored, dict): raise FormulaError("Dữ liệu mẫu đã lưu không hợp lệ.", category="evaluation")
    values = {}
    for code, element in plan.inputs.items():
        if code not in stored: raise FormulaError(f'Thiếu dữ liệu cho biến "{code}".', category="evaluation")
        raw = stored[code]
        if element.value_type in NUMERIC:
            if isinstance(raw, (bool, float)) or not isinstance(raw, (str, int, Decimal)):
                raise FormulaError("Giá trị số mẫu không hợp lệ.", category="evaluation")
            try: values[code] = Decimal(raw)
            except (InvalidOperation, ValueError): raise FormulaError("Giá trị số mẫu không hợp lệ.", category="evaluation") from None
        else: values[code] = raw
    return values


def compare_test(result, case):
    if result.data_type in NUMERIC:
        if case.expected_value_numeric is None: return False
        with localcontext() as context:
            context.prec = 64
            return abs(result.value - case.expected_value_numeric) <= case.tolerance
    if result.data_type == "BOOLEAN": return ("TRUE" if result.value else "FALSE") == case.expected_value_text
    return result.value == case.expected_value_text


def run_cases(plan, cases):
    results = []
    budget = Budget(limits().steps)
    for case in cases:
        try:
            result = plan.run(test_inputs(plan, case.input_context), budget=budget)
            results.append({"case": case, "passed": compare_test(result, case), "value": result.value, "error": None})
        except FormulaError as error:
            results.append({"case": case, "passed": False, "value": None, "error": error.describe()})
    return results


def deactivate_test_case(*, workspace, formula, case_id):
    require_write_access(workspace, resource="formula_test", editing=True)
    with transaction.atomic():
        record = _lock(workspace, formula)
        count = FormulaTestCase.objects.filter(formula=record, pk=case_id, is_active=True).update(is_active=False, updated_at=timezone.now())
        if not count: raise ValidationError("Không tìm thấy bộ kiểm thử đang hoạt động.")


def save_test_case(*, workspace, formula, plan, data):
    require_write_access(workspace, resource="formula_test", editing=False)
    # Only structured, type-checked values constructed by the form are stored.
    result = plan.run(data["inputs"])
    if data.get("expected") is None: raise ValidationError({"expected": "Vui lòng nhập kết quả mong đợi để lưu bộ kiểm thử."})
    numeric = result.data_type in NUMERIC
    expected = data["expected"]
    values = {code: format(value, "f") if isinstance(value, Decimal) else value for code, value in data["inputs"].items()}
    try:
        with transaction.atomic():
            record = _lock(workspace, formula)
            case = FormulaTestCase(formula=record, name=data["test_name"].strip(), input_context=values, tolerance=Decimal(0),
                expected_value_numeric=expected if numeric else None,
                expected_value_text=("TRUE" if expected else "FALSE") if result.data_type == "BOOLEAN" else expected if not numeric else None)
            case.full_clean(validate_unique=False, validate_constraints=False); case.save()
            return case
    except DatabaseError as error: _db_error(error)


def activate_version(*, workspace, formula, version):
    require_write_access(workspace, resource="formula_version", editing=True)
    try:
        with transaction.atomic():
            record = _lock(workspace, formula)
            locked = FormulaVersion.objects.select_for_update().get(pk=version.pk, formula=record)
            ensure_editable(locked)
            if not record.is_active: raise ValidationError("Công thức đã ngừng hoạt động.")
            if not locked.effective_from: raise ValidationError("Vui lòng đặt ngày bắt đầu hiệu lực trước khi kích hoạt.")
            validate_period({key: getattr(locked, key) for key in VERSION_FIELDS})
            # Check draft graph as well: do not publish a latent circular graph.
            build_plan(organization=workspace.organization, formula=record, expression=locked.expression)
            plan = build_plan(organization=workspace.organization, formula=record, expression=locked.expression,
                publication=True, effective_date=locked.effective_from)
            cases = list(FormulaTestCase.objects.select_for_update().filter(formula=record, is_active=True).order_by("pk")[:201])
            if len(cases) > 200: raise ValidationError("Quá nhiều bộ kiểm thử; tối đa 200 bộ đang hoạt động.")
            if not cases: raise ValidationError("Cần ít nhất một bộ kiểm thử đang hoạt động trước khi kích hoạt.")
            failed = [entry for entry in run_cases(plan, cases) if not entry["passed"]]
            if failed: raise ValidationError("Bộ kiểm thử chưa đạt: " + "; ".join(entry["case"].name for entry in failed[:10]) + ".")
            _persist_analysis(locked, plan)
            locked.status = "EFFECTIVE"
            locked.approved_by = None
            locked.save(update_fields=("status", "approved_by"))
            Formula.objects.filter(pk=record.pk).update(updated_at=timezone.now())
            return locked
    except FormulaError as error: raise ValidationError(error.describe(version.expression)) from None
    except FormulaVersion.DoesNotExist: raise ValidationError("Không tìm thấy phiên bản.") from None
    except DatabaseError as error: _db_error(error)
