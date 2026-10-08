"""Resolvers can execute without views, HTTP requests, user sessions or globals."""
from decimal import Decimal
from django.test import TestCase
from .run_test_data import golden_data, seal
from .engine.context import ExecutionContext
from .engine.resolvers.scheme import resolve_scheme
from .engine.resolvers.uom import UomResolver
from .engine.resolvers.prices import PriceResolver, ResourceRateResolver
from .engine.resolvers.manufacturing import ManufacturingResolver
from .engine.resolvers.allocation import allocate
from .engine.runner import execute


class RunResolverTests(TestCase):
    def setUp(self):
        self.data = golden_data(); seal(self.data)
        d = self.data
        self.context = ExecutionContext(d.company, d.product, d.sku, d.day, Decimal(1), d.box, d.currency, packaging_quantity=Decimal(1), packaging_uom=d.box)
        self.units = UomResolver(self.context)
        self.prices = PriceResolver(self.context, self.units)
        self.rates = ResourceRateResolver(self.context, self.units)
        self.manufacturing = ManufacturingResolver(self.context, self.units, self.prices, self.rates)
    def test_scheme(self):
        self.assertEqual(resolve_scheme(self.context, self.data.scheme.pk).pk, self.data.scheme_version.pk)
    def test_bom(self):
        self.assertEqual(self.manufacturing.material().value, Decimal(40000))
    def test_packaging(self):
        self.assertEqual(self.manufacturing.packaging().value, Decimal(5000))
    def test_supplier_price(self):
        self.assertEqual(self.prices.cost(self.data.items[0], Decimal("0.5"), self.data.kg).value, Decimal(5000))
    def test_uom_identity(self):
        self.assertEqual(self.units.convert(Decimal("0.12345678"), self.data.kg, self.data.kg)[0], Decimal("0.12345678"))
    def test_routing(self):
        self.assertEqual(self.manufacturing.routing().value, Decimal(10000))
    def test_resource_rate(self):
        self.assertEqual(self.rates.cost(self.data.resource, Decimal("1.5"), self.data.h).value, Decimal(15000))
    def test_allocation(self):
        self.assertEqual(allocate(self.context, self.units, "OVERHEAD", output_quantity=self.manufacturing.output_quantity).value, Decimal(5000))
    def test_safe_formula_pipeline_without_http(self):
        self.assertEqual(execute(self.context, self.data.scheme.pk).total, Decimal(60000))
