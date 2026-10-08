from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase

from apps.core.models import Organization, Product, Recipe, RecipeLine, RecipeVersion, Uom, UomCategory
from apps.master_data.access import Workspace
from .services import create_version


class VersionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="CONCURRENT_BOM", name="Công ty kiểm thử")
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.unit = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        product = Product.objects.create(organization=self.company, code="PRODUCT", name="Sản phẩm", costing_uom=self.unit)
        self.recipe = Recipe.objects.create(organization=self.company, product=product, code="BOM", name="Định mức")
        RecipeVersion.objects.create(recipe=self.recipe, version_no=1, output_qty=1, output_uom=self.unit)

    def tearDown(self):
        for model in (RecipeLine, RecipeVersion, Recipe, Product, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def test_two_simultaneous_creations_get_distinct_sequential_numbers(self):
        barrier = Barrier(2)

        def create():
            try:
                barrier.wait(timeout=10)
                return create_version(workspace=Workspace(self.company), recipe=self.recipe, data={
                    "output_qty": Decimal(1), "output_uom": self.unit, "yield_rate": Decimal(1),
                    "effective_from": None, "effective_to": None, "change_reason": None,
                }).version_no
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(create) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        self.assertEqual(sorted(results), [2, 3])
        self.assertEqual(list(RecipeVersion.objects.filter(recipe=self.recipe).order_by("version_no").values_list("version_no", flat=True)), [1, 2, 3])
