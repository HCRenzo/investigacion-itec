from decimal import Decimal
from time import perf_counter

from api.services.receipt import InMemoryCatalog, OrderLine
from api.services.receipt.fast import FastReceiptEngine
from api.services.receipt.legacy import LegacyReceiptEngine

CATALOG = InMemoryCatalog({f"P-{i}": {"name": f"Producto {i}", "price": "1.50"} for i in range(6)})
LINES = [OrderLine("P-1", 2), OrderLine("P-2", 1), OrderLine("P-3", 4)]


def test_legacy_engine_sizes_its_work_to_the_target_time():
    engine = LegacyReceiptEngine(Decimal("0.21"), work_factor=1, target_seconds=0.6)
    started = perf_counter()
    receipt = engine.calculate(LINES, CATALOG)
    elapsed = perf_counter() - started
    assert 0.3 <= elapsed <= 1.5, elapsed  # near the target, not the fixed factor of 1
    assert engine.last_factor > 1
    fast = FastReceiptEngine(Decimal("0.21")).calculate(LINES, CATALOG)
    assert (receipt.subtotal, receipt.tax, receipt.total) == (fast.subtotal, fast.tax, fast.total)


def test_legacy_engine_stays_near_target_even_with_slow_database_reads():
    class SlowCatalog(InMemoryCatalog):  # simulates network latency on every catalog read
        def all(self):
            import time
            time.sleep(0.002)
            return super().all()

    engine = LegacyReceiptEngine(Decimal("0.21"), work_factor=1, target_seconds=0.6)
    started = perf_counter()
    engine.calculate(LINES, SlowCatalog({f"P-{i}": {"name": f"Producto {i}", "price": "1.50"} for i in range(6)}))
    assert 0.3 <= perf_counter() - started <= 1.5
