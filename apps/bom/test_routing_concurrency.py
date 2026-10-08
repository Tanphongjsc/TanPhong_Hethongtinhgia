"""Parent locks serialize numbering and operation writes on local PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase

from apps.core.models import Organization, Product, Routing, RoutingOperation, RoutingVersion, Uom, UomCategory
from apps.master_data.access import Workspace
from .routing_services import create_version, save_operation


class RoutingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="CONCURRENT_ROUTING", name="Công ty kiểm thử")
        category = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        self.unit = Uom.objects.create(category=category, code="PC", name="Cái", symbol="cái")
        product = Product.objects.create(organization=self.company, code="PRODUCT", name="Sản phẩm", costing_uom=self.unit)
        self.routing = Routing.objects.create(organization=self.company, product=product, code="RT", name="Quy trình")
        self.version = RoutingVersion.objects.create(routing=self.routing, version_no=1, batch_size=1, batch_uom=self.unit)
        RoutingOperation.objects.create(routing_version=self.version, sequence_no=10, operation_code="FIRST", operation_name="Công đoạn đầu")

    def tearDown(self):
        for model in (RoutingOperation, RoutingVersion, Routing, Product, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def simultaneous(self, action):
        barrier = Barrier(2)

        def execute():
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute) for _ in range(2)]
            return [future.result(timeout=20) for future in futures]

    def test_simultaneous_clones_get_distinct_versions_and_complete_operations(self):
        def clone():
            return create_version(workspace=Workspace(self.company), routing=self.routing, source=self.version,
                data={"batch_size": Decimal(1), "batch_uom": self.unit, "effective_from": None, "effective_to": None, "change_reason": None}).version_no

        self.assertEqual(sorted(self.simultaneous(clone)), [2, 3])
        self.assertEqual(list(RoutingVersion.objects.filter(routing=self.routing).order_by("version_no").values_list("version_no", flat=True)), [1, 2, 3])
        for version in RoutingVersion.objects.filter(routing=self.routing):
            self.assertEqual(list(version.routingoperation_set.values_list("operation_code", flat=True)), ["FIRST"])

    def test_simultaneous_same_sequence_yields_one_friendly_validation_error(self):
        def add():
            try:
                save_operation(workspace=Workspace(self.company), routing=self.routing, version=self.version, data={
                    "sequence_no": 20, "operation_code": "NEXT", "operation_name": "Công đoạn tiếp",
                    "work_center": None, "primary_resource": None, "setup_time": Decimal(0), "run_time": Decimal(0),
                    "time_uom": None, "quantity_basis": None, "quantity_uom": None, "notes": None,
                })
                return "saved"
            except ValidationError as error:
                self.assertIn("Thứ tự công đoạn đã tồn tại", " ".join(error.messages))
                return "duplicate"

        self.assertEqual(sorted(self.simultaneous(add)), ["duplicate", "saved"])
        self.assertEqual(RoutingOperation.objects.filter(routing_version=self.version, sequence_no=20).count(), 1)
