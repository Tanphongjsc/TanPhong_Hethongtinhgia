"""Deep UI verification on isolated fixtures, with no business implementation changes."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import re
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from apps.core import models as m
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run
from apps.costing.run_test_data import cleanup
from apps.pricing.demo_scenario import verify_pricing_demo
from apps.master_data.ui_coverage_testing import SurfaceDOM

OUT = Path(settings.BASE_DIR) / "artifacts/ui-deep-coverage"


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Enable COSTING_BROWSER_TESTS=1.")
class DeepUIBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        cleanup()
        m.Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        self.demo = seed_demo()
        self.run = create_golden_run(self.demo)
        verify_pricing_demo()
        self.records = self.demo.records
        self.scenario = m.PriceScenario.objects.get(code="DEMO_PRICING_GOLDEN")
        self.draft = self.clone(m.PriceScenario, self.scenario, code="DEEP_DRAFT", name="Kịch bản nháp",
                                status="DRAFT", output_snapshot_jsonb={})
        usd = m.Currency.objects.get(code="USD")
        self.fx = m.FxRate.objects.create(organization=self.demo.workspace.organization, rate_type="SPOT",
                      from_currency_code=usd, to_currency_code_id="VND", rate=Decimal("26000.123456789012"),
                      effective_at=timezone.make_aware(datetime(2026, 1, 1)), source_name="Nguồn kiểm thử", status="DRAFT")
        self.route_inventory = json.loads((OUT / "inventory.json").read_text(encoding="utf-8"))["routes"]
        self.urls = {r["name"]: self.route_url(r) for r in self.route_inventory
                     if "GET" in r["methods"] and r["classification"] not in ("NON_UI", "HEALTH/TECHNICAL")}
        self.evidence = []
        self.errors = []
        self.missing = []

    def tearDown(self):
        if self.evidence:
            self.save_evidence(self._testMethodName + "-observations")
        self.assertEqual(self.errors, [])
        self.assertEqual(self.missing, [])
        cleanup()
        super().tearDown()

    def clone(self, model, record, **changes):
        data = model.objects.values().get(pk=record.pk)
        data.pop(model._meta.pk.attname)
        data.update(changes)
        return model.objects.create(**data)

    def route_url(self, row):
        name = row["name"]
        suffix = name.split(":")[-1]
        resources = {
            "supplier_price": m.SupplierPrice, "supplier": m.Supplier, "cost_element": m.CostElement,
            "currency": m.Currency, "uom_category": m.UomCategory, "uom_conversion": m.UomConversion, "uom": m.Uom,
            "category": m.ProductCategory, "item": m.Item, "product": m.Product, "sku": m.Sku,
            "work_center": m.WorkCenter, "resource_rate": m.ResourceRate, "resource": m.Resource,
            "cost_pool": m.CostPool, "allocation_rule": m.AllocationRule, "channel_fee_rule": m.ChannelFeeRule,
            "channel": m.Channel, "tax_rule": m.TaxRule, "fx_rate": m.FxRate,
        }
        parameters = re.findall(r"<(?:\w+:)?(\w+)>", row["path"])
        kwargs = {}
        if suffix.startswith("bom_"):
            parent, version = self.records["recipe"], self.records["recipe_draft"]
            children = {"line_pk": m.RecipeLine.objects.filter(recipe_version=version).first()}
        elif suffix.startswith("packaging_"):
            parent, version = self.records["packaging"], self.records["packaging_draft"]
            children = {"line_pk": m.PackagingLine.objects.filter(packaging_config_version=version).first(),
                        "assignment_pk": m.SkuPackagingAssignment.objects.first()}
        elif suffix.startswith("routing_"):
            parent, version = self.records["routing"], self.records["routing_draft"]
            children = {"operation_pk": m.RoutingOperation.objects.filter(routing_version=version).first()}
        elif suffix.startswith("scheme_"):
            parent, version = self.records["scheme"], self.records["scheme_draft"]
            children = {"line_pk": m.CostingSchemeLine.objects.filter(scheme_version=version).first()}
        elif suffix.startswith("formula_"):
            parent, version = self.records["full_formula"], self.records["full_formula_draft"]
            children = {}
        elif suffix.startswith("run_"):
            parent, version = self.run, None
            children = {"line_pk": m.CostingRunLine.objects.filter(run=self.run).first()}
        elif suffix.startswith("scenario_"):
            parent, version, children = (self.draft if suffix.endswith("_edit") else self.scenario), None, {}
        else:
            key = next(k for k in resources if suffix.startswith(k + "_"))
            parent = self.fx if key == "fx_rate" else resources[key].objects.first()
            if parent is None:
                raise AssertionError(f"Missing fixture for {name}")
            version, children = None, {}
        for parameter in parameters:
            if parameter == "pk":
                kwargs[parameter] = parent.pk
            elif parameter == "code":
                kwargs[parameter] = parent.pk
            elif parameter in ("version_pk", "version_id"):
                kwargs[parameter] = version.pk
            elif parameter == "public_id":
                kwargs[parameter] = self.run.public_id
            else:
                self.assertIsNotNone(children.get(parameter), (name, parameter))
                kwargs[parameter] = children[parameter].pk
        return reverse(name, kwargs=kwargs)

    def observe(self, page, browser, name, state, width):
        page.wait_for_function("!document.querySelector('.ui-shell') || document.querySelector('.ui-shell').dataset.collapsed !== undefined")
        layout = page.evaluate("""() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          width: document.documentElement.scrollWidth,
          bad: [...document.querySelectorAll('main *,[role=dialog] *')].filter(e=>{
            const r=e.getBoundingClientRect(); return r.width && r.right>innerWidth+1 &&
              !e.closest('.ui-table-scroll') && !e.closest('pre');
          }).slice(0,5).map(e=>({tag:e.tagName,id:e.id,class:e.className,right:e.getBoundingClientRect().right})),
          dialogs:[...document.querySelectorAll('[role=dialog]')].filter(e=>e.getClientRects().length).map(e=>{
            const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,scroll:e.scrollWidth,client:e.clientWidth};}),
          unlabelled:[...document.querySelectorAll('input:not([type=hidden]):not([type=submit]),select,textarea')]
            .filter(e=>!e.labels?.length&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby'))
            .map(e=>e.name),
          headers:document.querySelectorAll('th:not([scope])').length
        })""")
        self.evidence.append({"browser": browser, "route": name, "state": state, "width": width, "layout": layout})
        if layout["overflow"] or layout["unlabelled"] or any(d["scroll"] > d["client"] for d in layout["dialogs"]):
            slug = re.sub(r"[^a-z0-9_-]", "-", name.lower())
            page.screenshot(path=str(OUT / f"issue-{slug}-{width}.png"), full_page=True)
        self.assertFalse(layout["overflow"], (name, state, width, layout))
        self.assertEqual(layout["unlabelled"], [], (name, state, width))
        self.assertEqual(layout["headers"], 0, (name, state, width, "unscoped table header"))
        for dialog in layout["dialogs"]:
            self.assertLessEqual(dialog["scroll"], dialog["client"], (name, state, width, "dialog content overflow", dialog))
            self.assertGreaterEqual(dialog["top"], -1, (name, dialog))
            self.assertLessEqual(dialog["bottom"], page.viewport_size["height"] + 1, (name, dialog))
        if state in ("five columns / long names", "MANY ROWS / LONG CODE / LONG NAME",
                      "drawer HTMX invalid / error focus", "deactivate modal / focus / Escape"):
            slug = re.sub(r"[^a-z0-9_-]", "-", name.lower())
            folder = OUT / "screenshots"
            folder.mkdir(exist_ok=True)
            page.screenshot(path=str(folder / f"fixed-{slug}-{width}.png"), full_page=True)
        if width >= 992 and page.locator(".ui-topbar").count():
            sidebar, topbar = page.locator("#workspace-sidebar").bounding_box(), page.locator(".ui-topbar").bounding_box()
            self.assertGreaterEqual(topbar["x"], sidebar["x"] + sidebar["width"] - 1, (name, "sidebar overlap"))

    def page(self, browser):
        page = browser.new_page(locale="vi-VN", viewport={"width": 1440, "height": 960})
        page.on("pageerror", lambda error: self.errors.append(page.url + ": " + error.stack))
        page.on("response", lambda response: self.missing.append(response.url) if "/static/" in response.url and response.status >= 400 else None)
        return page

    def save_evidence(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{name}.json").write_text(json.dumps(self.evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_all_get_routes_full_partial_and_invalid_forms(self):
        events = []
        for name, url in self.urls.items():
            for htmx in (False, True):
                response = self.client.get(url, HTTP_HX_REQUEST="true" if htmx else "false")
                if response.status_code == 302:
                    self.assertFalse(htmx, name)
                    self.assertIn(name, ("bom:routing_operation_resources", "costing:scheme_line_sources", "costing:run_options"))
                    response = self.client.get(response["Location"])
                self.assertIn(response.status_code, (200, 409), (name, htmx))
                self.assertNotIn(b"Traceback", response.content)
                events.append({"route": name, "htmx": htmx, "status": response.status_code,
                               "templates": sorted({t.name for t in response.templates if t.name})})
            if name.endswith("_create") and "version" not in name and "line" not in name and "operation" not in name and "assignment" not in name:
                for htmx in (False, True):
                    response = self.client.post(url, {"code": ""}, HTTP_HX_REQUEST="true" if htmx else "false")
                    self.assertEqual(response.status_code, 200, name)
                    dom = SurfaceDOM()
                    dom.feed(response.content.decode())
                    self.assertGreater(dom.invalid, 0, (name, "invalid form must identify a field"))
        (OUT / "route-contract-requests.json").write_text(json.dumps(events, indent=2), encoding="utf-8")

    def test_every_document_get_at_five_viewports(self):
        from playwright.sync_api import sync_playwright
        fragments = {"formula_engine:formula_catalogue", "bom:routing_operation_resources", "costing:scheme_line_sources", "costing:run_options"}
        # scenario_options has an intentional normal-request full form fallback.
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = self.page(browser)
            for width in (1440, 1280, 1024, 768, 390):
                page.set_viewport_size({"width": width, "height": 960 if width >= 1024 else 844})
                for name, url in self.urls.items():
                    if name in fragments:
                        continue
                    response = page.goto(self.live_server_url + url)
                    self.assertIn(response.status, (200, 409), name)
                    self.observe(page, "chromium", name, "normal GET", width)
            browser.close()
        self.save_evidence("route-browser")

    def test_representative_states_htmx_drawers_and_long_content(self):
        from playwright.sync_api import sync_playwright, expect
        screenshots = OUT / "screenshots"
        screenshots.mkdir(exist_ok=True)
        paths = {
            "list": self.urls["product:item_list"], "form": self.urls["product:item_create"],
            "detail": self.urls["product:item_detail"], "version": self.urls["bom:routing_version_detail"],
            "costing": self.urls["costing:run_detail"], "pricing": self.urls["pricing:scenario_detail"],
            "comparison": reverse("pricing:scenario_compare") + "?compare=1&" + "&".join(
                "scenario=" + str(row.pk) for row in m.PriceScenario.objects.filter(status="CALCULATED")[:2]),
        }
        # Five columns with valid copied historical snapshots; no engine or current-rate resolution.
        for i in range(3):
            self.clone(m.PriceScenario, self.scenario, code=f"DEEP_COMPARE_{i}", name=("Tên kịch bản rất dài " * 8)[:250])
        comparison_ids = list(m.PriceScenario.objects.filter(status="CALCULATED").values_list("pk", flat=True)[:5])
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = self.page(browser)
            for width in (1440, 768, 390):
                page.set_viewport_size({"width": width, "height": 960 if width == 1440 else 844})
                for label, path in paths.items():
                    page.goto(self.live_server_url + path)
                    self.observe(page, "chromium", label, "representative", width)
                    page.evaluate("scrollTo(0,0)")
                    page.screenshot(path=str(screenshots / f"{label}-{width}.png"), full_page=True)
                page.goto(self.live_server_url + reverse("pricing:scenario_compare") + "?compare=1&" + "&".join("scenario=" + str(pk) for pk in comparison_ids))
                expect(page.locator("#comparison-results thead th")).to_have_count(6)
                self.observe(page, "chromium", "pricing:scenario_compare", "five columns / long names", width)
                page.goto(self.live_server_url + paths["list"])
                search = page.locator('main input[type=search]').first
                search.fill("__DEEP_ABSENT__")
                expect(page.locator("main")).to_contain_text("Không có kết quả")
                self.observe(page, "chromium", "product:item_list", "HTMX no result", width)
                page.goto(self.live_server_url + paths["form"])
                page.locator("#id_name").fill("Giữ nguyên giá trị đã nhập")
                page.locator('main button[type=submit]').last.click()
                expect(page.locator("#id_code")).to_have_attribute("aria-invalid", "true")
                expect(page.locator("#id_code")).to_be_focused()
                expect(page.locator("#id_name")).to_have_value("Giữ nguyên giá trị đã nhập")
                self.observe(page, "chromium", "product:item_create", "invalid / preserved / focus", width)
                for parent_name, trigger, label in (
                    ("bom:packaging_version_detail", "#packaging-lines-table a[hx-get]", "packaging drawer"),
                    ("bom:routing_version_detail", "#routing-operations-table a[hx-get]", "operation drawer"),
                    ("costing:scheme_version_detail", "#scheme-lines-table a[hx-get]", "scheme drawer"),
                    ("costing:run_detail", "a[hx-target='#run-trace-editor']", "trace drawer")):
                    page.goto(self.live_server_url + self.urls[parent_name])
                    candidates = page.locator(trigger)
                    if not candidates.count():
                        candidates = page.locator('a[hx-get][hx-target$="-editor"]')
                    self.assertGreater(candidates.count(), 0, label)
                    candidates.first.click()
                    dialog = page.get_by_role("dialog")
                    expect(dialog).to_be_visible()
                    self.observe(page, "chromium", parent_name, label, width)
                    close = dialog.get_by_role("button", name="Đóng chi tiết", exact=True)
                    expect(close).to_be_focused()
                    page.keyboard.press("Shift+Tab")
                    self.assertTrue(dialog.evaluate("e=>e.contains(document.activeElement)"), label)
                    page.keyboard.press("Escape")
                    expect(dialog).not_to_be_visible()
                    self.assertTrue(page.evaluate("document.activeElement!==document.body"), (label, "return focus"))
                page.goto(self.live_server_url + paths["pricing"])
                # Visual stress fixture only, without rewriting persisted snapshots or numerical formatters.
                page.locator(".ui-metric dd").first.evaluate("e=>e.textContent='999.999.999.999.999,12345678 VND'")
                page.locator("main h1").evaluate("e=>e.textContent='MÃ_RẤT_DÀI_KHÔNG_CÓ_KHOẢNG_TRẮNG_'.repeat(5)")
                self.observe(page, "chromium", "pricing:scenario_detail", "large decimal / unbroken code visual fixture", width)
            browser.close()
        self.save_evidence("states-browser")

    def test_empty_many_long_locked_and_native_fallback(self):
        from playwright.sync_api import sync_playwright, expect
        element = m.CostElement.objects.first()
        for i in range(32):
            self.clone(m.CostElement, element, code=f"DEEP_{i:03}", name=("Tên phần tử chi phí dài " * 9)[:255])
        m.CostElement.objects.filter(pk=element.pk).update(code="L" * 120, name="Tên rất dài " * 20)
        for model, parent_field, parent, order_field, source in (
            (m.RecipeLine, "recipe_version", self.records["recipe_draft"], "display_order", m.RecipeLine.objects.filter(recipe_version=self.records["recipe_draft"]).first()),
            (m.RoutingOperation, "routing_version", self.records["routing_draft"], "sequence_no", m.RoutingOperation.objects.filter(routing_version=self.records["routing_draft"]).first())):
            for i in range(3, 28):
                changes = {order_field: i * 10}
                if model == m.RoutingOperation:
                    changes.update(operation_code=f"EDGE_{i}", operation_name=("Tên công đoạn dài " * 12)[:255])
                self.clone(model, source, **changes)
        import uuid
        context = deepcopy(self.run.context_jsonb)
        context["errors"] = [{"code": "FIXTURE_FAILURE", "message": "Không thể hoàn thành lần tính trong dữ liệu kiểm thử."}]
        failed = self.clone(m.CostingRun, self.run, public_id=uuid.uuid4(), run_no="DEEP_FAILED",
                            idempotency_key="DEEP_FAILED", trace_id=uuid.uuid4(), run_status="FAILED",
                            full_cost=None, context_jsonb=context, locked_at=None)
        locked = [
            reverse("bom:bom_version_edit", args=[self.records["recipe"].pk, self.records["recipe_version"].pk]),
            reverse("bom:packaging_version_edit", args=[self.records["packaging"].pk, self.records["packaging_version"].pk]),
            reverse("bom:routing_version_edit", args=[self.records["routing"].pk, self.records["routing_version"].pk]),
            reverse("costing:scheme_version_edit", args=[self.records["scheme"].pk, self.records["scheme_version"].pk]),
            reverse("formula_engine:formula_version_edit", args=[self.records["full_formula"].pk, self.records["full_formula_version"].pk]),
        ]
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = self.page(browser)
            for width in (1440, 1024, 768, 390):
                page.set_viewport_size({"width": width, "height": 960 if width >= 1024 else 844})
                for name, path in self.urls.items():
                    if name.endswith("_list") and "version" not in name and "assignment" not in name:
                        page.goto(self.live_server_url + path + "?q=__DEEP_EMPTY__")
                        expect(page.locator("main")).to_contain_text(re.compile("Không có|Chưa có"))
                        self.observe(page, "chromium", name, "EMPTY / FILTER NO RESULT", width)
                for route in ("master_data:cost_element_list", "master_data:cost_element_detail",
                              "bom:bom_version_detail", "bom:routing_version_detail"):
                    page.goto(self.live_server_url + self.urls[route])
                    self.observe(page, "chromium", route, "MANY ROWS / LONG CODE / LONG NAME", width)
                page.goto(self.live_server_url + self.urls["master_data:cost_element_list"] + "?page=2")
                expect(page.locator("main")).to_contain_text("Trang 2")
                self.observe(page, "chromium", "master_data:cost_element_list", "PAGINATED", width)
                page.goto(self.live_server_url + reverse("costing:run_detail", args=[failed.public_id]))
                expect(page.locator("main [role=alert]")).to_contain_text("Không thể hoàn thành")
                self.observe(page, "chromium", "costing:run_detail", "FAILED / EMPTY BREAKDOWN", width)
                page.goto(self.live_server_url + self.urls["formula_engine:formula_version_edit"])
                page.locator("#id_expression").fill(" + ".join(["$DEMO_MATERIAL_COST"] * 90))
                page.locator("#token-palette").evaluate("e=>{const nodes=[...e.children];for(let i=0;i<15;i++)nodes.forEach(n=>e.append(n.cloneNode(true)));}")
                self.observe(page, "chromium", "formula_engine:formula_version_edit", "long expression / palette visual fixture", width)
                page.goto(self.live_server_url + self.urls["costing:run_detail"])
                page.locator("#run-lines-table tbody").evaluate("e=>{const row=e.querySelector('tr');for(let i=0;i<35;i++)e.append(row.cloneNode(true));}")
                self.observe(page, "chromium", "costing:run_detail", "many breakdown rows visual fixture", width)
                page.goto(self.live_server_url + self.urls["costing:run_trace"])
                page.locator("main dd").first.evaluate("e=>e.textContent='TRACE_LONG_REFERENCE_'.repeat(200)")
                self.observe(page, "chromium", "costing:run_trace", "long trace visual fixture", width)
                for url in locked:
                    page.goto(self.live_server_url + url)
                    if "/formula-engine/" in url:
                        expect(page.locator("#formula-studio-form")).to_have_count(0)
                        expect(page.locator("main")).to_contain_text("Phiên bản")
                    else:
                        self.assertGreater(page.locator("main :disabled").count(), 0, url)
                    self.observe(page, "chromium", url, "EFFECTIVE / READONLY / DISABLED", width)
            native = browser.new_page(java_script_enabled=False, viewport={"width": 390, "height": 844}, locale="vi-VN")
            native.goto(self.live_server_url + self.urls["master_data:cost_element_list"])
            apply = native.locator("form:has(#page-size)").get_by_role("button", name="Áp dụng", exact=True)
            expect(apply).to_have_class(re.compile("ui-button"))
            native.locator("#page-size").select_option("50")
            apply.click()
            expect(native).to_have_url(re.compile("per_page=50"))
            self.assertLessEqual(native.evaluate("document.documentElement.scrollWidth"), 390)
            native.close()
            browser.close()
        self.save_evidence("edge-browser")

    def test_dependent_swaps_modals_and_validation_focus(self):
        from playwright.sync_api import sync_playwright, expect
        resource = m.Resource.objects.filter(work_center__isnull=False).first()
        m.CostElement.objects.filter(pk=m.CostElement.objects.first().pk).update(code="L" * 120)
        product_id, sku_id, run_id = str(self.run.product_id), str(self.run.sku_id), str(self.run.pk)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = self.page(browser)
            for width in (1440, 768, 390):
                page.set_viewport_size({"width": width, "height": 960 if width == 1440 else 844})
                page.goto(self.live_server_url + self.urls["formula_engine:formula_create"])
                page.locator("#token-search").fill("__ABSENT_TOKEN__")
                expect(page.locator("#token-palette")).to_contain_text("Không có")
                self.observe(page, "chromium", "formula_engine:formula_catalogue", "HTMX catalogue swap", width)
                page.goto(self.live_server_url + self.urls["costing:scheme_line_create"])
                with page.expect_response(lambda r: "/lines/sources/" in r.url):
                    page.locator("#id_source_mode").select_option("FORMULA")
                expect(page.locator("#scheme-source-fields #id_formula_version")).to_be_visible()
                self.observe(page, "chromium", "costing:scheme_line_sources", "HTMX source swap", width)
                page.goto(self.live_server_url + self.urls["bom:routing_operation_create"])
                with page.expect_response(lambda r: "/operations/resources/" in r.url):
                    page.locator("#id_work_center").select_option(str(resource.work_center_id))
                expect(page.locator(f'#id_primary_resource option[value="{resource.pk}"]')).to_have_count(1)
                self.observe(page, "chromium", "bom:routing_operation_resources", "HTMX resource swap", width)
                page.goto(self.live_server_url + self.urls["costing:run_create"])
                with page.expect_response(lambda r: "/runs/options/" in r.url):
                    page.locator("#id_product").select_option(product_id)
                expect(page.locator(f'#id_sku option[value="{sku_id}"]')).to_have_count(1)
                self.observe(page, "chromium", "costing:run_options", "HTMX run options swap", width)
                page.goto(self.live_server_url + self.urls["pricing:scenario_create"])
                with page.expect_response(lambda r: "/scenarios/options/" in r.url):
                    page.locator("#id_product").select_option(product_id)
                expect(page.locator(f'#id_sku option[value="{sku_id}"]')).to_have_count(1)
                self.observe(page, "chromium", "pricing:scenario_options", "HTMX scenario options swap", width)
                for parent in ("bom:packaging_version_detail", "bom:routing_version_detail", "costing:scheme_version_detail"):
                    page.goto(self.live_server_url + self.urls[parent])
                    page.locator('a[hx-get][hx-target$="-editor"]').first.click()
                    dialog = page.get_by_role("dialog")
                    expect(dialog).to_be_visible()
                    dialog.locator('button[type=submit]').last.click()
                    error = dialog.locator('[aria-invalid="true"]').first
                    expect(error).to_be_focused()
                    self.observe(page, "chromium", parent, "drawer HTMX invalid / error focus", width)
                    dialog.get_by_role("button", name="Đóng chi tiết", exact=True).click()
                    expect(dialog).not_to_be_visible()
                page.goto(self.live_server_url + self.urls["master_data:cost_element_edit"])
                page.locator("#id_is_active").uncheck()
                page.locator('#cost-element-form button[type=submit]').click()
                dialog = page.get_by_role("dialog")
                expect(dialog).to_be_visible()
                self.observe(page, "chromium", "master_data:cost_element_edit", "deactivate modal / focus / Escape", width)
                expect(dialog.get_by_role("button", name="Đóng hộp thoại")).to_be_focused()
                page.keyboard.press("Shift+Tab")
                self.assertTrue(dialog.evaluate("e=>e.contains(document.activeElement)"))
                page.keyboard.press("Escape")
                expect(dialog).not_to_be_visible()
                self.assertTrue(page.evaluate("document.activeElement!==document.body"))
                page.locator('#cost-element-form button[type=submit]').click()
                overlay = dialog.locator("..")
                overlay.click(position={"x": 4, "y": 4})
                expect(dialog).not_to_be_visible()
            browser.close()
        self.save_evidence("interaction-browser")

    def test_firefox_webkit_native_controls_and_errors(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            for name in ("firefox", "webkit"):
                browser = getattr(p, name).launch()
                page = self.page(browser)
                for width in (1440, 390):
                    page.set_viewport_size({"width": width, "height": 960 if width == 1440 else 844})
                    for route in ("product:item_list", "product:item_create", "bom:routing_version_detail",
                                  "costing:run_snapshot", "pricing:scenario_detail"):
                        page.goto(self.live_server_url + self.urls[route])
                        self.observe(page, name, route, "cross-browser", width)
                    page.goto(self.live_server_url + self.urls["product:item_create"])
                    page.locator('main button[type=submit]').last.click()
                    expect(page.locator("#id_code")).to_be_focused()
                    self.observe(page, name, "product:item_create", "invalid focus", width)
                browser.close()
        self.save_evidence("cross-browser")