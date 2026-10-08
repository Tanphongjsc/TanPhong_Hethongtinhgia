"""Two actual PostgreSQL transactions calculate one draft only once."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import close_old_connections
from django.test import TransactionTestCase
from apps.core.models import Organization, PriceScenario
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run, stored_fingerprint
from apps.costing.run_test_data import cleanup
from .demo_scenario import verify_pricing_demo
from .scenario_forms import ScenarioForm
from .scenario_services import save_scenario, calculate_scenario


class PricingScenarioConcurrencyTests(TransactionTestCase):
    def setUp(self):
        cleanup()
        Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        self.demo = seed_demo()
        self.costing_run = create_golden_run(self.demo)
        verify_pricing_demo()

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_duplicate_simultaneous_calculate_returns_one_identical_snapshot(self):
        source = PriceScenario.objects.get(code="DEMO_PRICING_GOLDEN")
        form = ScenarioForm(workspace=self.demo.workspace, instance=source)
        payload = form.initial | {"code": "CONCURRENT"}
        form = ScenarioForm(payload, workspace=self.demo.workspace)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        draft = save_scenario(workspace=self.demo.workspace, data=form.cleaned_data)
        before = stored_fingerprint(self.costing_run)
        from .engine.runner import execute
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                result = calculate_scenario(workspace=self.demo.workspace, instance=draft)
                return result.status, result.output_snapshot_jsonb
            finally: close_old_connections()
        with patch("apps.pricing.scenario_services.execute", wraps=execute) as execution, ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(worker) for _ in range(2)]
            results = [task.result(timeout=30) for task in tasks]
        self.assertEqual(execution.call_count, 1)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], "CALCULATED")
        self.assertEqual(before, stored_fingerprint(self.costing_run))
