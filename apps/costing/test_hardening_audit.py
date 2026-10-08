"""Exercise the read-only audit against real, deliberately inconsistent fixtures."""
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from apps.core import models as m
from scripts.audit_demo_integrity import audit_integrity
from .demo_data import seed_demo
from .run_test_data import cleanup


class IntegrityAuditTests(TransactionTestCase):
    def setUp(self):
        cleanup()
        m.Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        self.demo = seed_demo()

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_clean_demo_audit_is_read_only_and_does_not_query_membership(self):
        with CaptureQueriesContext(connection) as queries:
            report = audit_integrity()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["errors"], [])
        self.assertGreater(report["checks"], 100)
        for row in queries:
            self.assertNotIn("organization_member", row["sql"].lower())
            self.assertFalse(row["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "TRUNCATE")))

    def test_product_sku_mismatch_reported_without_repair(self):
        values = m.Product.objects.values().get(pk=self.demo.records["product"].pk)
        values.pop("id")
        values["code"] = "OTHER_PRODUCT"
        other = m.Product.objects.create(**values)
        m.Sku.objects.filter(pk=self.demo.records["sku"].pk).update(product=other)
        report = audit_integrity()
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("SKU_PRODUCT_MISMATCH", [error["code"] for error in report["errors"]])
        self.assertEqual(m.Sku.objects.get(pk=self.demo.records["sku"].pk).product_id, other.pk)
