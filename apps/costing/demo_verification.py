"""Real persisted execution and read-only UI checks for the one DEMO dataset."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
import uuid

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import CostingRun, CostingRunLine
from .configuration import validate_costing_scheme
from .demo_data import DAY, FUTURE, MARKER, manual_expected, seed_future_changes, inventory
from .engine.context import digest
from .run_services import create_run


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def request_data(demo, *, day=DAY):
    r = demo.records
    return dict(product=r["product"], sku=r["sku"], scheme=r["scheme"], costing_date=day,
        quantity=Decimal(10), quantity_uom=r["box"], result_currency_code=r["VND"], run_type="STANDARD",
        packaging_quantity=Decimal(1), packaging_uom=r["box"], notes=MARKER, manual={})


def create_golden_run(demo, *, day=DAY):
    # This is an operation key, not an actor UUID. Actor fields remain NULL.
    key = uuid.uuid5(uuid.NAMESPACE_URL, f"costing-demo:{MARKER}:{demo.workspace.organization.pk}:{day.isoformat()}")
    return create_run(workspace=demo.workspace, data=request_data(demo, day=day), idempotency_key=key)


def stored_fingerprint(run):
    """Hash persisted header AND every persisted line, including trace/snapshot."""
    record = CostingRun.objects.values().get(pk=run.pk)
    rows = list(CostingRunLine.objects.filter(run=run).order_by("display_order", "pk").values())
    return sha256(json.dumps([record, rows], sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def reconcile(demo, run, *, future=False):
    run.refresh_from_db()
    require(run.run_status == "LOCKED", f"Lần tính chưa hoàn tất: {run.run_status}; {run.context_jsonb.get('errors', [])}")
    require(run.created_by is None and run.approved_by is None, "Lần tính mẫu không được gán người dùng giả.")
    lines = list(CostingRunLine.objects.filter(run=run).order_by("display_order", "pk"))
    require(len(lines) == 6, "Breakdown mẫu phải có đúng 6 dòng.")
    actual = {line.line_code.removeprefix("DEMO_"): line.amount for line in lines}
    resource = next(line for line in lines if line.line_code == "DEMO_RESOURCE_COST")
    resource_steps = resource.source_trace_jsonb.get("steps", [])
    raw_resource = {}
    for key, code in (("MACHINE_COST", "DEMO_MIXER"), ("LABOR_COST", "DEMO_PACKING_LABOR")):
        steps = [step for step in resource_steps if step.get("title", "").startswith("Nguồn lực " + code + " —")]
        require(len(steps) == 1, f"Thiếu trace nguồn lực {code}.")
        raw_resource[key] = Decimal(dict(steps[0]["fields"])["Thành tiền"])
        # Inverse 60 conversion has a repeating decimal. Reconcile component
        # trace amounts at the demo's declared six-place HALF_UP money boundary,
        # retaining the unrounded value/delta as evidence, not changing expected.
        with localcontext() as context:
            context.prec = 64
            actual[key] = raw_resource[key].quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    actual["UNIT_COST"] = Decimal(run.context_jsonb["per_unit"])
    expected = manual_expected(future=future)
    comparisons = {code: {"expected": str(value), "actual": str(actual[code]), "delta": str(actual[code] - value)} for code, value in expected.items()}
    for code, value in raw_resource.items():
        with localcontext() as context:
            context.prec = 64
            comparisons[code].update(raw_trace=str(value), raw_delta=str(value - expected[code]), rounding="HALF_UP / 6")
    require(all(Decimal(row["delta"]) == 0 for row in comparisons.values()), f"Golden không khớp: {comparisons}")
    require(run.full_cost == expected["FULL_COST"] and run.manufacturing_cost == expected["FULL_COST"], "Tổng persisted header khác breakdown.")
    snapshot = run.version_snapshot_jsonb
    require(snapshot.get("sha256") == digest({key: value for key, value in snapshot.items() if key != "sha256"}), "Hash snapshot không hợp lệ.")
    sources = list(snapshot.get("sources", {}).values())
    def ids(table):
        return {row["id"] for row in sources if row["table"] == table}
    r = demo.records
    require(ids("uom_conversion") == {r["mass_conversion"].pk, r["time_conversion"].pk}, "Hai phép quy đổi phải thực sự được resolve và snapshot.")
    price_keys = ("coffee_future_price" if future else "coffee_price", "sugar_price", "sachet_price", "box_item_price")
    require(ids("supplier_price") == {r[key].pk for key in price_keys}, "Chọn giá mua theo ngày không đúng.")
    rate_keys = ("mixer_future_rate", "labor_future_rate") if future else ("mixer_rate", "labor_rate")
    require(ids("resource_rate") == {r[key].pk for key in rate_keys}, "Chọn đơn giá nguồn lực theo ngày không đúng.")
    for table, key in (("recipe_version", "recipe_version"), ("packaging_config_version", "packaging_version"),
        ("routing_version", "routing_version"), ("costing_scheme_version", "scheme_version")):
        require(ids(table) == {r[key].pk}, f"Phiên bản hiệu lực của {table} không đúng; không được chọn Nháp mới nhất.")
    require(len(snapshot.get("formulas", {})) == 2, "Engine phải thực thi cả hai công thức có snapshot AST.")
    require(all(line.input_snapshot_jsonb and line.source_trace_jsonb.get("steps") for line in lines), "Thiếu dữ liệu đầu vào hoặc explain trace persisted.")
    return {"id": run.pk, "public_id": str(run.public_id), "run_no": run.run_no, "status": run.run_status,
        "snapshot_sha256": snapshot["sha256"], "source_count": len(sources), "line_count": len(lines), "comparisons": comparisons}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def ui_smoke(demo, run):
    """Only GETs: can run on the real seeded development DB without mutations."""
    client, r = Client(raise_request_exception=False), demo.records
    modules = (
        ("master_data", "cost_element", "MATERIAL_COST", "DEMO_MATERIAL_COST", {"active": "true"}),
        ("master_data", "currency", "VND", "VND", {"active": "true"}),
        ("master_data", "uom_category", "MASS", "MASS", {"active": "true"}),
        ("master_data", "uom", "g", "G", {"category": r["g"].category_id}),
        ("master_data", "uom_conversion", "mass_conversion", "G", {"from_uom": r["g"].pk}),
        ("product", "category", "category", "DEMO_COFFEE", {"active": "true"}),
        ("product", "item", "coffee", "DEMO_INSTANT_COFFEE", {"category": r["category"].pk}),
        ("product", "product", "product", "DEMO_CAPPUCCINO", {"category": r["category"].pk}),
        ("product", "sku", "sku", "DEMO_CAPPUCCINO_BOX20", {"product": r["product"].pk}),
        ("master_data", "supplier", "supplier", "DEMO_SUPPLIER", {"active": "true"}),
        ("master_data", "supplier_price", "coffee_price", "DEMO_INSTANT_COFFEE", {"supplier": r["supplier"].pk}),
        ("bom", "bom", "recipe", "DEMO_BOM_CAPPUCCINO", {"product": r["product"].pk}),
        ("bom", "packaging", "packaging", "DEMO_PACK_CAPPUCCINO", {"product": r["product"].pk}),
        ("bom", "work_center", "mixing", "DEMO_WC_MIXING", {"active": "true"}),
        ("bom", "resource", "mixer", "DEMO_MIXER", {"work_center": r["mixing"].pk}),
        ("bom", "resource_rate", "mixer_rate", "DEMO_MIXER", {"resource": r["mixer"].pk}),
        ("bom", "routing", "routing", "DEMO_ROUTE_CAPPUCCINO", {"product": r["product"].pk}),
        ("bom", "cost_pool", "pool", "DEMO_FACTORY_OVERHEAD", {"active": "true"}),
        ("bom", "allocation_rule", "rule", "DEMO_OVERHEAD_NORMAL", {"pool": r["pool"].pk}),
        ("formula_engine", "formula", "direct_formula", "DEMO_DIRECT_FORMULA", {"active": "true"}),
        ("costing", "scheme", "scheme", "DEMO_COSTING_SCHEME", {"active": "true"}),
    )
    banned = re.compile(r"\b(?:Create|Edit|Save|Cancel|Search|Filter|Status|Actions|Active|Inactive|Name|Description|Reset|Login|Logout)\b")
    results = []
    def check(url, *, params=None, htmx=False, table_code=None, empty=False, active_url=None):
        with CaptureQueriesContext(connection) as captured:
            response = client.get(url, params or {}, HTTP_HOST="localhost", **({"HTTP_HX_REQUEST": "true"} if htmx else {}))
        require(response.status_code == 200, f"UI {url}: HTTP {response.status_code}.")
        html = response.content.decode()
        parser = VisibleText(); parser.feed(html)
        require(not banned.search(" ".join(parser.text)), f"UI {url} còn nhãn tiếng Anh.")
        require(not any("organization_member" in query["sql"].lower() for query in captured), "UI không được query OrganizationMember.")
        require(("<!doctype html>" in html.lower()) != htmx, f"UI {url}: full/partial không đúng.")
        if not htmx:
            require('lang="vi"' in html, f"UI {url}: thiếu ngôn ngữ tiếng Việt.")
        if active_url:
            require(f'href="{active_url}" aria-current="page"' in html, f"Menu active sai: {url}.")
        if table_code:
            body = html.split("<tbody", 1)[-1].split("</tbody>", 1)[0]
            require((table_code in body) != empty, f"Search/filter/empty state sai: {url}.")
        require(not any(text in html for text in ("Traceback (most recent call last)", "IntegrityError", "OrganizationMember")), f"UI {url} lộ lỗi nội bộ.")
        return len(captured)
    root = client.get("/", HTTP_HOST="localhost")
    require(root.status_code == 302 and root.url == reverse("master_data:cost_element_list"), "Trang gốc không chuyển trực tiếp vào danh mục.")
    for namespace, name, key, code, filters in modules:
        listing = reverse(f"{namespace}:{name}_list")
        queries = [check(listing, table_code=code, active_url=listing)]
        for action in ("detail", "create", "edit"):
            args = [r[key].pk] if action in ("detail", "edit") else []
            queries.append(check(reverse(f"{namespace}:{name}_{action}", args=args), active_url=listing))
        queries.append(check(listing, params={"q": code, **filters}, table_code=code))
        negative = {name: "false" if value == "true" else "999999999" for name, value in filters.items()}
        queries.append(check(listing, params={"q": code, **negative}, table_code=code, empty=True))
        queries.append(check(listing, params={"q": "__NO_DEMO_MATCH__"}, table_code=code, empty=True))
        queries.append(check(listing, params={"q": code, **filters, "per_page": "25", "sort": "-code"}, htmx=True, table_code=code))
        results.append({"module": name, "requests": len(queries), "max_queries": max(queries), "status": "PASS"})
    for namespace, name, key, version_key, kwargs_key in (("bom", "bom", "recipe", "recipe_draft", "version_pk"),
        ("bom", "packaging", "packaging", "packaging_draft", "version_pk"),
        ("bom", "routing", "routing", "routing_draft", "version_pk"),
        ("costing", "scheme", "scheme", "scheme_draft", "version_pk"),
        ("formula_engine", "formula", "direct_formula", "direct_formula_draft", "version_id")):
        for action in ("detail", "edit"):
            check(reverse(f"{namespace}:{name}_version_{action}", kwargs={"pk": r[key].pk, kwargs_key: r[version_key].pk}))
    listing = reverse("costing:run_list")
    run_queries = [check(listing, table_code=run.run_no, active_url=listing), check(reverse("costing:run_create")),
        check(reverse("costing:run_detail", args=[run.public_id])), check(reverse("costing:run_snapshot", args=[run.public_id])),
        check(reverse("costing:run_rerun", args=[run.public_id])),
        check(listing, params={"q": "DEMO_CAPPUCCINO", "status": "LOCKED", "product": r["product"].pk}, htmx=True, table_code=run.run_no)]
    for line in CostingRunLine.objects.filter(run=run):
        check(reverse("costing:run_trace", args=[run.public_id, line.pk]), htmx=True)
    results.append({"module": "run", "requests": len(run_queries) + 6, "max_queries": max(run_queries), "status": "PASS"})
    return results


def verify_demo(demo, *, smoke=True):
    report = validate_costing_scheme(organization=demo.workspace.organization, scheme=demo.records["scheme"],
        version=demo.records["scheme_version"], effective_date=DAY)
    require(not report.errors, "Phương án mẫu chưa hợp lệ: " + "; ".join(report.errors))
    # Freeze independently calculated expectations before calling the engine.
    expected = manual_expected()
    run = create_golden_run(demo)
    golden = reconcile(demo, run)
    before = stored_fingerprint(run)
    seed_future_changes(demo)
    # New rates/prices are real records. Re-executing the old date must still
    # resolve the old records; a different key creates a distinct saved result.
    repeated = create_run(workspace=demo.workspace, data=request_data(demo),
        idempotency_key=uuid.uuid5(uuid.NAMESPACE_URL, f"costing-demo-history:{demo.workspace.organization.pk}:{MARKER}"))
    reconcile(demo, repeated)
    later = create_golden_run(demo, day=FUTURE)
    future_report = reconcile(demo, later, future=True)
    require(before == stored_fingerprint(run), "Kết quả lịch sử thay đổi sau khi thêm giá/đơn giá tương lai.")
    ui = ui_smoke(demo, run) if smoke else []
    return {"dataset": MARKER, "company_id": demo.workspace.organization.pk, "company_code": demo.workspace.organization.code,
        "expected_before_execution": {key: str(value) for key, value in expected.items()},
        "golden": golden, "future": future_report, "historical_run_id": repeated.pk, "historical_unchanged": True,
        "historical_fingerprint": before, "ui_smoke": ui,
        "inventory": inventory(demo),
        "readiness": "READY FOR PRICING FOUNDATION" if smoke else "GOLDEN PASS; UI chưa kiểm tra"}
