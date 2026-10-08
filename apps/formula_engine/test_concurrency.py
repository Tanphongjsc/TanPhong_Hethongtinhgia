"""Concurrent editors allocate version numbers under a shared definition lock."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from django.test import TransactionTestCase
from apps.core.models import Formula, FormulaDependency, FormulaTestCase, FormulaVersion, Organization
from apps.master_data.access import Workspace
from .services import save_version


class FormulaConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="FORMULA_CONCURRENT", name="Công ty kiểm thử")
        self.formula = Formula.objects.create(organization=self.company, code="NUMBER", name="Số")
        FormulaVersion.objects.create(formula=self.formula, version_no=1, expression="1 + 2")

    def tearDown(self):
        for model in (FormulaDependency, FormulaTestCase, FormulaVersion, Formula, Organization): model.objects.all().delete()
        super().tearDown()

    def test_two_clones_allocate_distinct_versions_and_preserve_source(self):
        barrier = Barrier(2)
        def create():
            try:
                company = Organization.objects.get(pk=self.company.pk)
                formula = Formula.objects.get(pk=self.formula.pk)
                barrier.wait(timeout=10)
                return save_version(workspace=Workspace(company), formula=formula, data={"expression": "1 + 2"}).version_no
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(create) for _ in range(2)]
            self.assertEqual(sorted(future.result(timeout=20) for future in futures), [2, 3])
        self.assertEqual(list(FormulaVersion.objects.filter(formula=self.formula).order_by("version_no").values_list("expression", flat=True)), ["1 + 2"] * 3)
