"""Analyze definitions only. No evaluator, price/rate resolver or costing writes."""
from dataclasses import dataclass, field
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.formula_engine.dependencies import topological_order
from apps.formula_engine.engine import build_plan
from apps.formula_engine.errors import FormulaError
from apps.formula_engine.limits import limits
from apps.formula_engine.validator import element_type
from .selectors import line_queryset
from .validators import validate_line, validate_version


@dataclass
class ConfigurationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    order: list = field(default_factory=list)

    @property
    def valid(self):
        return not self.errors


def analyze_formula(*, organization, version, target=None, effective_date=None):
    """Reuse Formula Engine parser, type system and dated dependency checks."""
    formula = version.formula
    if formula.organization_id != organization.pk or not formula.is_active:
        raise FormulaError("Công thức không thuộc dữ liệu hệ thống hoặc đã ngừng hoạt động.")
    if version.status != "EFFECTIVE" or version.validation_status != "VALID":
        raise FormulaError("Phiên bản công thức chưa được kích hoạt hoặc không hợp lệ.")
    day = effective_date or timezone.localdate()
    if not version.effective_from or version.effective_from > day or (version.effective_to and version.effective_to < day):
        raise FormulaError("Phiên bản công thức không có hiệu lực tại ngày kiểm tra cấu hình.")
    if target and formula.output_element_id and formula.output_element_id != target.pk:
        raise FormulaError("Phần tử chi phí đầu ra của công thức không khớp dòng cấu hình.")
    plan = build_plan(organization=organization, formula=formula, expression=version.expression, publication=True, effective_date=day)
    if target and not element_type(target).compatible(plan.types[plan.root_code]):
        raise FormulaError("Kiểu hoặc đơn vị kết quả không khớp phần tử chi phí được gán.")
    return plan


def validate_costing_scheme(*, organization, scheme, version, effective_date=None):
    report = ConfigurationReport()
    if scheme.organization_id != organization.pk or version.scheme_id != scheme.pk:
        report.errors.append("Phương án hoặc phiên bản không thuộc dữ liệu hệ thống.")
        return report
    if not scheme.is_active: report.errors.append("Phương án đã ngừng hoạt động.")
    try: validate_version(data={"effective_from": version.effective_from, "effective_to": version.effective_to})
    except ValidationError as error: report.errors.extend(error.messages)
    if not version.effective_from:
        report.warnings.append("Chưa đặt ngày bắt đầu hiệu lực; kiểm tra công thức theo ngày hôm nay. Kích hoạt cần ngày bắt đầu.")
    rows = list(line_queryset(version=version)[:limits().graph_nodes + 1])
    if len(rows) > limits().graph_nodes:
        report.errors.append("Số dòng vượt giới hạn kiểm tra cấu hình. Vui lòng chia phương án nhỏ hơn.")
        return report
    if not rows: report.errors.append("Phương án chưa có dòng cấu hình.")
    providers, graph, cache = {}, {}, {}
    for row in rows:
        graph[row.line_code] = set()
        if row.cost_element: providers.setdefault(row.cost_element.code.upper(), []).append(row)
    for row in rows:
        prefix = f"Dòng {row.line_code}: "
        try:
            from .constants import LINE_FIELDS
            validate_line(data={name: getattr(row, name) for name in LINE_FIELDS}, organization=organization, instance=row, check_unique=False)
        except ValidationError as error: report.errors.extend(prefix + message for message in error.messages)
        element = row.cost_element
        if element:
            if element.organization_id != organization.pk or not element.is_active:
                report.errors.append(prefix + "Phần tử chi phí đã ngừng hoạt động hoặc không thuộc dữ liệu hệ thống.")
            for reference in (element.currency_code, element.default_uom):
                if reference and not reference.is_active: report.errors.append(prefix + "Tiền tệ hoặc đơn vị tính của phần tử chi phí đã ngừng hoạt động.")
            if element.value_type == "MONEY" and not element.currency_code_id:
                report.errors.append(prefix + "Phần tử chi phí tiền tệ chưa có tiền tệ.")
            if element.value_type == "QUANTITY" and not element.default_uom_id:
                report.errors.append(prefix + "Phần tử chi phí số lượng chưa có đơn vị tính.")
        if row.condition_jsonb:
            report.errors.append(prefix + "Điều kiện nâng cao chưa có bộ kiểm tra; cần rà soát trước khi kích hoạt.")
        if row.source_mode == "SYSTEM":
            from .engine.registry import check_source
            from .engine.errors import CostingError
            try: check_source(row, organization, effective_date or version.effective_from or timezone.localdate())
            except CostingError as error: report.errors.append(prefix + str(error))
            continue
        if row.source_mode in ("LOOKUP", "EXTERNAL"):
            report.errors.append(prefix + "Nguồn dữ liệu này chưa có bộ kiểm tra cấu hình được triển khai; chưa thể kích hoạt phương án.")
            continue
        if row.source_mode != "FORMULA" or not row.formula_version: continue
        if not element:
            report.warnings.append(prefix + "Chưa gán phần tử chi phí; kết quả dòng này không cung cấp biến cho dòng khác.")
        try:
            key = (row.formula_version_id, row.cost_element_id)
            if key not in cache:
                cache[key] = analyze_formula(organization=organization, version=row.formula_version, target=element, effective_date=effective_date or version.effective_from)
            plan = cache[key]
        except FormulaError as error:
            report.errors.append(prefix + error.describe(row.formula_version.expression))
            continue
        period_versions = [row.formula_version, *plan.versions.values()]
        for formula_version in period_versions:
            if formula_version.validation_status != "VALID":
                report.errors.append(prefix + "Công thức phụ thuộc chưa được xác nhận hợp lệ.")
            if effective_date is None and formula_version.effective_to and (not version.effective_to or formula_version.effective_to < version.effective_to):
                report.errors.append(prefix + "Phiên bản công thức kết thúc trước thời hạn phương án; cần thu hẹp ngày hiệu lực.")
        if plan.versions:
            report.warnings.append(prefix + "Công thức phụ thuộc được chọn theo ngày kiểm tra; tham chiếu công thức không cố định phiên bản cho toàn kỳ.")
        for code, dependency in sorted(plan.inputs.items()):
            sources = providers.get(code, [])
            state = "Đã cung cấp" if len(sources) == 1 else "Thiếu nguồn" if not sources else "Nhiều nguồn"
            report.dependencies.append({"line": row.line_code, "formula": row.formula_version.formula.code,
                "element": code, "provider": sources[0].line_code if len(sources) == 1 else "—", "state": state})
            if not sources:
                report.errors.append(f"Phương án chưa cung cấp dữ liệu cho phần tử chi phí {code}.")
            elif len(sources) > 1:
                report.errors.append(f"Phần tử chi phí {code} có nhiều nguồn trong phương án; chưa có quy tắc chọn nguồn.")
            else: graph[row.line_code].add(sources[0].line_code)
    try:
        ordered = []
        for code in graph:
            for key in topological_order(graph, code):
                if key not in ordered: ordered.append(key)
        report.order = ordered
    except FormulaError as error: report.errors.append(str(error))
    report.errors = list(dict.fromkeys(report.errors))
    report.warnings = list(dict.fromkeys(report.warnings))
    return report
