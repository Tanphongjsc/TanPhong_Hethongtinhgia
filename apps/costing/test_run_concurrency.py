from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from decimal import Decimal
import uuid
from unittest.mock import patch
from django.db import connections
from django.test import TransactionTestCase
from apps.core.models import CostingRun, CostingRunLine, SupplierPrice
from apps.master_data.access import Workspace
from .run_services import create_run
from .engine.runner import execute
from .run_test_data import golden_data, seal, request_data, cleanup


class RunConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.data = golden_data(); seal(self.data)
    def tearDown(self):
        cleanup(); super().tearDown()
    def test_double_submit_race_returns_same_complete_run(self):
        token, barrier = uuid.uuid4(), Barrier(2)
        def calculate():
            try:
                barrier.wait(timeout=10)
                return create_run(workspace=Workspace(self.data.company), data=request_data(self.data), idempotency_key=token).pk
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(calculate) for _ in range(2)]
            ids = [future.result(timeout=30) for future in futures]
        self.assertEqual(ids[0], ids[1]); self.assertEqual(CostingRun.objects.count(), 1)
        self.assertEqual(CostingRunLine.objects.count(), 5)
        self.assertEqual(CostingRun.objects.get().full_cost, 60000)
    def test_source_change_during_run_uses_one_repeatable_snapshot(self):
        ready, changed = Event(), Event()
        def paused(context, scheme_id):
            ready.set()
            if not changed.wait(timeout=10): raise RuntimeError("timeout")
            return execute(context, scheme_id)
        def calculate():
            try:
                with patch("apps.costing.run_services.execute", side_effect=paused):
                    return create_run(workspace=Workspace(self.data.company), data=request_data(self.data), idempotency_key=uuid.uuid4()).pk
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(calculate)
            self.assertTrue(ready.wait(timeout=10))
            SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=20000)
            changed.set()
            run = CostingRun.objects.get(pk=future.result(timeout=30))
        self.assertEqual(run.full_cost, Decimal(60000))
        self.assertEqual(run.version_snapshot_jsonb["sources"][f"supplier_price:{self.data.prices[0].pk}"]["fields"]["unit_price"], "10000.00000000")
