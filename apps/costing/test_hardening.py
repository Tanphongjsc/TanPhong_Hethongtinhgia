"""Cross-module regression on the guarded local PostgreSQL test database."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from time import perf_counter
from unittest.mock import patch
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core import models as m
from apps.master_data.navigation import DESTINATIONS, SECTIONS
from apps.pricing.demo_scenario import verify_pricing_demo
from apps.pricing.scenario_services import calculate_scenario
from .demo_data import seed_demo
from .demo_verification import verify_demo, request_data, stored_fingerprint, VisibleText
from .run_selectors import run_list
from .run_services import create_run


class HardeningFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Fixture creation is confined to the existing guarded local test runner.
        m.Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        cls.demo = seed_demo()
        cls.costing_report = verify_demo(cls.demo, smoke=False)
        cls.pricing_report = verify_pricing_demo()
        cls.costing_run = m.CostingRun.objects.get(pk=cls.costing_report["golden"]["id"])
        cls.scenario = m.PriceScenario.objects.get(pk=cls.pricing_report["scenario_id"])
        cls.future = m.PriceScenario.objects.get(pk=cls.pricing_report["future_scenario_id"])
        cls.fx = m.FxRate.objects.create(organization=cls.demo.workspace.organization,
            from_currency_code=cls.demo.records["VND"], to_currency_code=m.Currency.objects.get(code="USD"),
            rate_type="SPOT", rate=Decimal("0.00004"), effective_at=timezone.make_aware(datetime(2026, 1, 1)), source_name="Nguồn mẫu")

    def modules(self):
        r = self.demo.records
        modules = (
            ("master_data", "cost_element", r["MATERIAL_COST"].pk),
            ("master_data", "currency", "VND"), ("master_data", "uom_category", r["g"].category_id),
            ("master_data", "uom", r["g"].pk), ("master_data", "uom_conversion", r["mass_conversion"].pk),
            ("product", "category", r["category"].pk), ("product", "item", r["coffee"].pk),
            ("product", "product", r["product"].pk), ("product", "sku", r["sku"].pk),
            ("master_data", "supplier", r["supplier"].pk), ("master_data", "supplier_price", r["coffee_price"].pk),
            ("bom", "bom", r["recipe"].pk), ("bom", "packaging", r["packaging"].pk),
            ("bom", "work_center", r["mixing"].pk), ("bom", "resource", r["mixer"].pk),
            ("bom", "resource_rate", r["mixer_rate"].pk), ("bom", "routing", r["routing"].pk),
            ("bom", "cost_pool", r["pool"].pk), ("bom", "allocation_rule", r["rule"].pk),
            ("formula_engine", "formula", r["direct_formula"].pk), ("costing", "scheme", r["scheme"].pk),
            ("pricing", "channel", self.scenario.channel_id),
            ("pricing", "channel_fee_rule", m.ChannelFeeRule.objects.order_by("pk").first().pk),
            ("pricing", "tax_rule", m.TaxRule.objects.order_by("pk").first().pk),
            ("pricing", "fx_rate", self.fx.pk), ("pricing", "scenario", self.scenario.pk),
        )
        return modules

    def assert_page(self, response, *, partial=False):
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual("<!doctype html>" in html.lower(), not partial)
        parser = VisibleText()
        parser.feed(html)
        self.assertIsNone(re.search(r"\b(Create|Edit|Save|Cancel|Search|Filter|Status|Actions|Active|Inactive|Name|Description|Login|Logout)\b", " ".join(parser.text)))
        for text in ("Traceback (most recent call last)", "IntegrityError", "OrganizationMember"):
            self.assertNotIn(text, html)
        self.assertNotIn("sessionid", response.cookies)

class HardeningTests(HardeningFixtures):
    def test_all_catalogue_routes_full_partial_history_and_no_get_writes(self):
        with patch.object(m.OrganizationMember.objects, "filter", side_effect=AssertionError("Membership query")):
            for namespace, resource, pk in self.modules():
                with self.subTest(resource=resource), CaptureQueriesContext(connection) as queries:
                    listing = reverse(f"{namespace}:{resource}_list")
                    for action in ("list", "create", "detail", "edit"):
                        url = reverse(f"{namespace}:{resource}_{action}", args=[pk] if action in ("detail", "edit") else [])
                        response = self.client.get(url, follow=True)
                        self.assert_page(response)
                        self.assertFalse(any("login" in url for url, _ in response.redirect_chain))
                    self.assert_page(self.client.get(listing, HTTP_HX_REQUEST="true"), partial=True)
                    self.assert_page(self.client.get(listing, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"))
                    self.assert_page(self.client.get(listing, {"q": "__ABSENT__", "sort": "-code", "per_page": "50"}))
                sql = " ".join(row["sql"] for row in queries)
                self.assertIsNone(re.search(r"\b(INSERT INTO|UPDATE |DELETE FROM|TRUNCATE )", sql, re.I))
                for table in ("organization_member", "approval_request", "approval_action", "audit_event", "auth_user"):
                    self.assertNotIn(table, sql.lower())

    def test_run_comparison_root_and_historical_reads_are_read_only(self):
        before = stored_fingerprint(self.costing_run)
        snapshot = deepcopy(self.scenario.output_snapshot_jsonb)
        self.assertRedirects(self.client.get("/"), reverse("master_data:cost_element_list"), fetch_redirect_response=False)
        urls = [reverse(f"costing:run_{action}", args=[self.costing_run.public_id] if action in ("detail", "snapshot", "rerun") else []) for action in ("list", "create", "detail", "snapshot", "rerun")]
        urls += [reverse("pricing:scenario_compare")]
        for url in urls:
            self.assert_page(self.client.get(url))
        with CaptureQueriesContext(connection) as queries:
            self.assert_page(self.client.get(reverse("pricing:scenario_compare"), {"scenario": [self.scenario.pk, self.future.pk], "compare": "1"}, HTTP_HX_REQUEST="true"), partial=True)
        sql = " ".join(row["sql"].lower() for row in queries)
        for table in ("channel_fee_rule", "tax_rule", "fx_rate", "supplier_price", "resource_rate"):
            self.assertNotIn(f'from "{table}"', sql)
        self.assertEqual(stored_fingerprint(self.costing_run), before)
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.output_snapshot_jsonb, snapshot)

    def test_malformed_query_values_are_controlled_across_all_lists(self):
        cases = (
            {"q": "  cà phê  ", "sort": "--code", "page": "no", "per_page": "-1"},
            {"sort": "code; DROP TABLE item", "page": "9" * 100, "per_page": "999999", "product": "9" * 100, "sku": "invalid", "item": "-2", "resource": "x", "category": "１２", "pool": "x", "group": "x"},
            {"date_from": "not-a-date", "date_to": "9999-12-31", "effective_status": "x", "status": "unknown", "active": "unknown", "currency_code": "<script>"},
        )
        urls = [reverse(f"{namespace}:{resource}_list") for namespace, resource, _ in self.modules()]
        urls += [reverse("costing:run_list"), reverse("pricing:scenario_compare")]
        for url in urls:
            for values in cases:
                with self.subTest(url=url, values=values):
                    self.assert_page(self.client.get(url, values, HTTP_HX_REQUEST="true"), partial=True)

    def test_csrf_error_is_vietnamese_traced_and_does_not_write(self):
        client = Client(enforce_csrf_checks=True)
        before = m.CostingRun.objects.count()
        url = reverse("costing:run_create")
        for headers, partial in (({}, False), ({"HTTP_HX_REQUEST": "true"}, True), ({"HTTP_HX_REQUEST": "true", "HTTP_HX_HISTORY_RESTORE_REQUEST": "true"}, False)):
            response = client.post(url, {}, **headers)
            self.assertContains(response, "Vui lòng tải lại trang", status_code=403)
            self.assertEqual(response["X-Error-Code"], "CSRF_FAILED")
            self.assertTrue(response["X-Trace-ID"])
            self.assertEqual("<!doctype html>" in response.content.decode().lower(), not partial)
            self.assertNotIn("CSRF verification failed", response.content.decode())
        self.assertEqual(m.CostingRun.objects.count(), before)

    def test_error_pages_are_generic_for_unknown_route_and_hide_internal_details(self):
        response = self.client.get("/missing-route/", HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(response, "Không tìm thấy dữ liệu.", status_code=404)
        self.assertContains(response, "<!doctype html>", status_code=404)
        response = self.client.get(reverse("master_data:cost_element_detail", args=[9223372036854775807]))
        self.assertContains(response, "Không tìm thấy phần tử chi phí.", status_code=404)
        response = self.client.get("/", HTTP_HOST="invalid.example")
        self.assertContains(response, "Yêu cầu không hợp lệ.", status_code=400)
        self.assertNotContains(response, "DisallowedHost", status_code=400)

    def test_sidebar_has_exactly_one_link_per_implemented_module(self):
        labels = [label for _, labels in SECTIONS for label in labels]
        self.assertEqual(set(labels), set(DESTINATIONS))
        self.assertEqual(len(labels), len(set(labels)))
        response = self.client.get(reverse("master_data:cost_element_list"))
        self.assertNotContains(response, "Chưa triển khai")
        navigation = response.content.decode().split('<nav aria-label="Điều hướng hệ thống"', 1)[1].split("</nav>", 1)[0]
        for label in labels:
            self.assertEqual(navigation.count(f'href="{reverse(DESTINATIONS[label][1])}"'), 1)

    def test_run_list_defers_large_snapshots_without_lazy_fetches(self):
        page, _, _ = run_list(organization=self.demo.workspace.organization, filters={})
        with CaptureQueriesContext(connection) as queries:
            rows = list(page.object_list)
            for row in rows:
                self.assertTrue({"version_snapshot_jsonb", "fx_snapshot_jsonb"} <= row.get_deferred_fields())
                self.assertTrue(row.context_jsonb["display"])
        self.assertEqual(len(queries), 1)
        self.assertNotIn('"version_snapshot_jsonb"', queries[0]["sql"])
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(reverse("costing:run_list")).status_code, 200)
        self.assertFalse(any('"version_snapshot_jsonb"' in row["sql"] for row in queries))

    def test_query_text_is_escaped_and_sort_is_allowlisted(self):
        payload = '<script>alert("x")</script>'
        response = self.client.get(reverse("product:item_list"), {"q": payload, "sort": "name; SELECT 1"})
        self.assertNotContains(response, payload)
        self.assertContains(response, "&lt;script&gt;")
        self.assertEqual(response.context["current_sort"], "code")

    def test_missing_manufacturing_sources_fail_without_partial_results(self):
        for model, key in ((m.Recipe, "recipe"), (m.Routing, "routing")):
            with self.subTest(source=key):
                model.objects.filter(pk=self.demo.records[key].pk).update(is_active=False)
                try:
                    row = create_run(workspace=self.demo.workspace, data=request_data(self.demo), idempotency_key=uuid.uuid4())
                    self.assertEqual(row.run_status, "FAILED")
                    self.assertTrue(row.context_jsonb["errors"])
                    self.assertEqual(row.version_snapshot_jsonb, {})
                    self.assertFalse(m.CostingRunLine.objects.filter(run=row).exists())
                finally:
                    model.objects.filter(pk=self.demo.records[key].pk).update(is_active=True)

    def test_missing_effective_scheme_does_not_create_partial_run(self):
        from datetime import date
        before = m.CostingRun.objects.count()
        with self.assertRaises(ValidationError):
            create_run(workspace=self.demo.workspace, data=request_data(self.demo, day=date(2026, 9, 30)), idempotency_key=uuid.uuid4())
        self.assertEqual(m.CostingRun.objects.count(), before)


class HardeningVolumeTests(HardeningFixtures):
    """Opt-in measurement: real services, bounded fixtures, no live database load."""
    def test_volume_and_execution_measurements(self):
        import os
        if os.environ.get("COSTING_HARDENING_BENCHMARK") != "1":
            self.skipTest("Enable COSTING_HARDENING_BENCHMARK=1 for local measurements")
        r, organization = self.demo.records, self.demo.workspace.organization
        def copy_rows(model, source, count, **changes):
            values = model.objects.values().get(pk=source.pk)
            values.pop(model._meta.pk.attname)
            rows = []
            for index in range(count):
                fields = deepcopy(values)
                fields.update({name: value(index) if callable(value) else value for name, value in changes.items()})
                rows.append(model(**fields))
            model.objects.bulk_create(rows)
        copy_rows(m.Item, r["coffee"], 100, code=lambda i: f"VOLUME_ITEM_{i:03}", name=lambda i: f"Vật tư kiểm thử {i}")
        copy_rows(m.SupplierPrice, r["coffee_price"], 100, status="DRAFT")
        copy_rows(m.Sku, r["sku"], 50, code=lambda i: f"VOLUME_SKU_{i:03}")
        copy_rows(m.CostingRun, self.costing_run, 50, public_id=lambda i: uuid.uuid4(), idempotency_key=lambda i: uuid.uuid4(), run_no=lambda i: f"VOLUME_RUN_{i:03}")
        copy_rows(m.PriceScenario, self.scenario, 50, code=lambda i: f"VOLUME_SCENARIO_{i:03}")
        metrics = {}
        def measure(name, function, repeats=10):
            times, counts = [], []
            for _ in range(repeats):
                with CaptureQueriesContext(connection) as queries:
                    started = perf_counter()
                    result = function()
                    times.append((perf_counter() - started) * 1000)
                counts.append(len(queries))
            ordered = sorted(times)
            metrics[name] = {"samples": repeats, "p50_ms": round(ordered[(repeats - 1) // 2], 3), "p95_ms": round(ordered[-1], 3), "queries_min": min(counts), "queries_max": max(counts)}
            return result
        for resource, url in (("item", "product:item_list"), ("supplier_price", "master_data:supplier_price_list"), ("sku", "product:sku_list"), ("run", "costing:run_list"), ("scenario", "pricing:scenario_list")):
            small = measure(resource + "_25", lambda: self.client.get(reverse(url), {"per_page": 25}))
            large = measure(resource + "_100", lambda: self.client.get(reverse(url), {"per_page": 100}))
            self.assertEqual(small.status_code, 200)
            self.assertEqual(large.status_code, 200)
            self.assertEqual(metrics[resource + "_25"]["queries_max"], metrics[resource + "_100"]["queries_max"])
        measure("run_payload_before", lambda: list(run_list(organization=organization, filters={})[0].object_list.defer(None)))
        measure("run_payload_after", lambda: list(run_list(organization=organization, filters={})[0].object_list))
        result = measure("costing_execute", lambda: create_run(workspace=self.demo.workspace, data=request_data(self.demo), idempotency_key=uuid.uuid4()))
        self.assertEqual(result.full_cost, Decimal(583000))
        def price():
            values = m.PriceScenario.objects.values().get(pk=self.scenario.pk)
            values.pop("id")
            values.update(code=str(uuid.uuid4()), status="DRAFT", output_snapshot_jsonb={}, suggested_price=None)
            return calculate_scenario(workspace=self.demo.workspace, instance=m.PriceScenario.objects.create(**values))
        result = measure("pricing_execute", price)
        self.assertEqual(Decimal(result.suggested_price), Decimal("89972.41379310"))
        selected = list(m.PriceScenario.objects.filter(status="CALCULATED").order_by("pk").values_list("pk", flat=True)[:5])
        result = measure("comparison_5", lambda: self.client.get(reverse("pricing:scenario_compare"), {"scenario": selected, "compare": "1"}))
        self.assertEqual(result.status_code, 200)
        payload = {"database": "guarded localhost test database", "scope": "Warm process, 10 sequential samples; includes ORM/service/render, excludes HTTP network and production concurrency. p95 is nearest-rank max of 10.", "fixtures": {"extra_items": 100, "extra_supplier_prices": 100, "extra_skus": 50, "extra_runs": 50, "extra_scenarios": 50}, "metrics": metrics}
        path = Path(settings.BASE_DIR) / "artifacts" / "hardening-performance.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
