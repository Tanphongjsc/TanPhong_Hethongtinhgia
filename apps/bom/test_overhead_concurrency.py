"""Verify database uniqueness remains the final guard in simultaneous creates."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.core.models import AllocationRule, CostPool, Organization
from apps.master_data.access import Workspace
from . import overhead_services as services


class OverheadConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="OVERHEAD_RACE", name="Công ty kiểm thử")
        self.first = CostPool.objects.create(organization=self.company, code="FIRST", name="Nhóm thứ nhất", pool_type="OTHER")
        self.second = CostPool.objects.create(organization=self.company, code="SECOND", name="Nhóm thứ hai", pool_type="OTHER")

    def tearDown(self):
        for model in (AllocationRule, CostPool, Organization):
            model.objects.all().delete()
        super().tearDown()

    def race(self, *, validator_name, action, duplicate_message):
        barrier = Barrier(2)
        validate = getattr(services, validator_name)

        def after_validation(**kwargs):
            validate(**kwargs)
            # Both requests validate before either insert; exercise the DB race.
            barrier.wait(timeout=10)

        def execute(index):
            try:
                action(index)
                return "saved"
            except ValidationError as error:
                self.assertIn(duplicate_message, " ".join(error.messages))
                return "duplicate"
            finally:
                connections.close_all()

        with patch.object(services, validator_name, side_effect=after_validation), ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(execute, index) for index in range(2)]
            self.assertEqual(sorted(result.result(timeout=20) for result in results), ["duplicate", "saved"])

    def test_cost_pool_race_returns_friendly_duplicate(self):
        self.race(validator_name="validate_cost_pool", duplicate_message="Mã nhóm chi phí đã tồn tại", action=lambda index:
            services.save_cost_pool(workspace=Workspace(self.company), data={"code": " race ", "name": "Nhóm", "pool_type": "OTHER", "description": None, "is_active": True}))
        self.assertEqual(CostPool.objects.filter(code="RACE").count(), 1)

    def test_rule_code_is_unique_across_different_pools_under_race(self):
        self.race(validator_name="validate_allocation_rule", duplicate_message="Mã quy tắc phân bổ đã tồn tại", action=lambda index:
            services.save_allocation_rule(workspace=Workspace(self.company), data={"code": " race ", "name": "Quy tắc", "pool": (self.first, self.second)[index],
                "basis_type": "UNIT", "basis_uom": None, "formula_code": None, "priority": 100, "effective_from": timezone.localdate(), "effective_to": None}))
        self.assertEqual(AllocationRule.objects.filter(code="RACE").count(), 1)
