"""Resolve a bounded snapshot first; interpret it without further database I/O."""
from dataclasses import dataclass, field
from django.db.models import Q
from django.utils import timezone
from django.db.models.functions import Upper
from apps.core.models import CostElement, Formula, FormulaVersion
from .dependencies import references, topological_order
from .errors import FormulaError
from .evaluator import Budget, EvaluationResult, checked_value, evaluate
from .limits import limits
from .parser import parse
from .validator import element_type, validate

ELEMENT_RELATIONS = ("currency_code", "default_uom", "default_uom__category")
FORMULA_RELATIONS = tuple("output_element__" + name for name in ELEMENT_RELATIONS) + ("output_element",)


@dataclass
class Plan:
    root_code: str
    roots: dict = field(default_factory=dict)
    bindings: dict = field(default_factory=dict)
    types: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)
    versions: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)
    order: list = field(default_factory=list)

    def run(self, inputs, *, budget=None):
        context = {}
        for code, element in self.inputs.items():
            if code not in inputs:
                raise FormulaError(f'Thiếu dữ liệu cho biến "{code}".', category="evaluation")
            context[code] = checked_value(inputs[code], element_type(element))
        computed, trace = {}, []
        budget = budget or Budget(limits().steps)
        for code in self.order:
            values = {key: context[target.code.upper()] if kind == "ELEMENT" else computed[target.code.upper()]
                for key, (kind, target) in self.bindings[code].items()}
            symbols = {key: element_type(target) if kind == "ELEMENT" else self.types[target.code.upper()]
                for key, (kind, target) in self.bindings[code].items()}
            result = evaluate(self.roots[code], values, self.types[code], budget=budget, symbol_types=symbols)
            computed[code] = result.value
            version = self.versions.get(code)
            trace.extend({**step, "formula": code, "version": version.version_no if version else None}
                for step in result.trace[:max(0, limits().trace_rows-len(trace))])
        return EvaluationResult(computed[self.root_code], self.types[self.root_code].kind, tuple(trace),
            ("Kiểm thử dùng phiên bản được liệt kê trong diễn giải; không phải kết quả tính giá thành.",)
            + (("Diễn giải được rút gọn do vượt giới hạn số bước hiển thị.",) if len(trace) >= limits().trace_rows else ()))


def build_plan(*, organization, formula, expression, publication=False, effective_date=None):
    """Studio previews latest versions; publication requires dated EFFECTIVE dependencies.

    References are resolved in batches per dependency layer, never per AST node.
    Bare names must be unambiguous. $ always means an element; @ means a formula.
    """
    today = effective_date or timezone.localdate()
    root_code = formula.code.upper()
    plan = Plan(root_code)
    plan.roots[root_code] = parse(expression)
    formulas = {root_code: formula}
    pending = [root_code]
    level = 0
    while pending:
        level += 1
        if level > limits().graph_depth:
            raise FormulaError("Phụ thuộc công thức vượt giới hạn độ sâu.")
        node_refs = {code: references(plan.roots[code]) for code in pending}
        codes = {name for refs in node_refs.values() for _, name in refs}
        def index_records(queryset):
            rows = list(queryset[:limits().nodes + 1])
            result = {}
            for row in rows:
                name = row.code.upper()
                if name in result:
                    raise FormulaError(f'Mã "{name}" có nhiều bản ghi khác chữ hoa/chữ thường; cần xử lý dữ liệu mơ hồ.')
                result[name] = row
            if len(rows) > limits().nodes: raise FormulaError("Danh mục tham chiếu vượt giới hạn.")
            return result
        elements = index_records(CostElement.objects.filter(organization=organization).annotate(normalized_code=Upper("code")).filter(
            normalized_code__in=codes).select_related(*ELEMENT_RELATIONS))
        targets = index_records(Formula.objects.filter(organization=organization).annotate(normalized_code=Upper("code")).filter(
            normalized_code__in=codes).select_related(*FORMULA_RELATIONS))
        targets[root_code] = formula
        needed = {}
        for code in pending:
            plan.bindings[code] = {}
            plan.graph[code] = set()
            for key, node in node_refs[code].items():
                requested_kind, name = key
                element = elements.get(name) if requested_kind != "formula" else None
                target = targets.get(name) if requested_kind != "element" else None
                if element and target:
                    raise FormulaError(f'Mã "{name}" đồng thời là biến và công thức. Dùng ${name} hoặc @{name}.', position=node.position)
                if element:
                    if not element.is_active:
                        raise FormulaError(f'Biến "{name}" đã ngừng hoạt động.', position=node.position)
                    plan.inputs[name] = element
                    plan.bindings[code][key] = ("ELEMENT", element)
                elif target:
                    if not target.is_active:
                        raise FormulaError(f'Công thức "{name}" đã ngừng hoạt động.', position=node.position)
                    plan.bindings[code][key] = ("FORMULA", target)
                    plan.graph[code].add(name)
                    formulas[name] = target
                    if name not in plan.roots: needed[name] = target
                else:
                    raise FormulaError(f'Không tìm thấy biến hoặc công thức "{name}".', position=node.position)
        if len(formulas) > limits().graph_nodes or len(plan.inputs) > limits().nodes:
            raise FormulaError("Phụ thuộc vượt giới hạn số công thức hoặc biến.")
        pending = []
        if needed:
            versions = FormulaVersion.objects.filter(formula_id__in=[target.pk for target in needed.values()]).order_by("formula_id", "-version_no", "-pk")
            if publication:
                versions = versions.filter(status="EFFECTIVE", effective_from__lte=today).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=today))
            # Limit even when malformed legacy data contains thousands of versions.
            from django.db.models import OuterRef, Subquery
            latest = versions.filter(formula_id=OuterRef("formula_id"))
            if not publication:
                versions = versions.filter(pk=Subquery(latest.values("pk")[:1]))
            fetched = list(versions[:limits().graph_nodes * 2 + 1])
            by_formula = {}
            for version in fetched: by_formula.setdefault(version.formula_id, []).append(version)
            for name, target in needed.items():
                matches = by_formula.get(target.pk, [])
                if not matches:
                    raise FormulaError(f'Công thức "{name}" chưa có phiên bản phù hợp' + (" đang hiệu lực tại ngày kích hoạt." if publication else "."))
                if len(matches) > 1:
                    raise FormulaError(f'Công thức "{name}" có nhiều phiên bản hiệu lực cùng ngày; cần xử lý cấu hình mơ hồ.')
                version = matches[0]
                plan.versions[name] = version
                try:
                    plan.roots[name] = parse(version.expression)
                except FormulaError as error:
                    raise FormulaError(f'Công thức "{name}" · Phiên bản {version.version_no}: {error.describe(version.expression)}', category=error.category) from None
                pending.append(name)
    plan.order = topological_order(plan.graph, root_code)
    for code in plan.order:
        symbols = {key: element_type(target) if kind == "ELEMENT" else plan.types[target.code.upper()]
            for key, (kind, target) in plan.bindings[code].items()}
        output = element_type(formulas[code].output_element)
        if formulas[code].output_element and (not formulas[code].output_element.is_active or formulas[code].output_element.organization_id != organization.pk):
            raise FormulaError("Phần tử chi phí đầu ra đã ngừng hoạt động hoặc không thuộc dữ liệu hệ thống.")
        try:
            plan.types[code] = validate(plan.roots[code], symbols, output)
        except FormulaError as error:
            if code == root_code: raise
            version = plan.versions[code]
            raise FormulaError(f'Công thức "{code}" · Phiên bản {version.version_no}: {error.describe(version.expression)}', category=error.category) from None
    return plan
