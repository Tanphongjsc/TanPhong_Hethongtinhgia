"""Concurrent definition writes on isolated PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase
from apps.core.models import CostingScheme, CostingSchemeVersion, CostingSchemeLine, Organization
from apps.master_data.access import Workspace
from . import services


class SchemeConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="CONCURRENT_SCHEME", name="Công ty kiểm thử")
        self.scheme = CostingScheme.objects.create(organization=self.company, code="STD", name="Phương án", purpose="COST")
        self.version = CostingSchemeVersion.objects.create(scheme=self.scheme, version_no=1)
        self.line = CostingSchemeLine.objects.create(scheme_version=self.version, line_code="L", label="Dòng", line_type="INFO", source_mode="MANUAL", cost_scope="MANUFACTURING", display_order=10)
    def tearDown(self):
        for model in (CostingSchemeLine, CostingSchemeVersion, CostingScheme, Organization): model.objects.all().delete()
        super().tearDown()
    def simultaneous(self, action):
        barrier = Barrier(2)
        def execute():
            try:
                barrier.wait(timeout=10)
                return action()
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute) for _ in range(2)]
            return [future.result(timeout=20) for future in futures]
    def test_concurrent_clones_get_distinct_numbers_complete_lines(self):
        def clone():
            return services.save_version(workspace=Workspace(self.company), scheme=self.scheme, source=self.version,
                data={"effective_from": None, "effective_to": None, "change_reason": "Clone"}).version_no
        self.assertEqual(sorted(self.simultaneous(clone)), [2, 3])
        self.assertEqual(CostingSchemeLine.objects.filter(scheme_version__scheme=self.scheme).count(), 3)
    def test_concurrent_same_order_returns_one_friendly_error(self):
        from .constants import LINE_FIELDS
        data = {name: getattr(self.line, name) for name in LINE_FIELDS}
        data.update(line_code="NEW", display_order=20)
        def add():
            try:
                services.save_line(workspace=Workspace(self.company), scheme=self.scheme, version=self.version, data=data)
                return "saved"
            except ValidationError as error:
                self.assertIn("đã tồn tại", " ".join(error.messages))
                return "duplicate"
        self.assertEqual(sorted(self.simultaneous(add)), ["duplicate", "saved"])
        self.assertEqual(CostingSchemeLine.objects.filter(scheme_version=self.version, display_order=20).count(), 1)
