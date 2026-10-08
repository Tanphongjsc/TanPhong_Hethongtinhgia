from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase

from apps.core.models import Organization, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Uom, UomCategory
from apps.master_data.access import Workspace
from .packaging_services import create_version


class PackagingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="PACK_CONCURRENT", name="Công ty kiểm thử")
        category = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        unit = Uom.objects.create(category=category, code="PC", name="Cái", symbol="cái")
        product = Product.objects.create(organization=self.company, code="PRODUCT", name="Sản phẩm", costing_uom=unit)
        self.config = PackagingConfig.objects.create(organization=self.company, product=product, code="PACK", name="Bao bì")
        PackagingConfigVersion.objects.create(packaging_config=self.config, version_no=1)

    def tearDown(self):
        for model in (PackagingLine, PackagingConfigVersion, PackagingConfig, Product, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def test_concurrent_version_numbers_are_serialized(self):
        barrier = Barrier(2)

        def create():
            try:
                barrier.wait(timeout=10)
                return create_version(workspace=Workspace(self.company), config=self.config, data={}).version_no
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=15) for future in (pool.submit(create), pool.submit(create))]
        self.assertEqual(sorted(results), [2, 3])
