import time
import numpy as np
from core.data_loader_dev import DevelopmentDataLoader
from core.engine import _run_smart_range_search
from core.settings import EngineSettings


def run_test(multiplier: int = 10):
    dl = DevelopmentDataLoader()
    customers = dl.load_customers(force_refresh=True)
    inventory = dl.load_inventory(force_refresh=True)
    customer = customers.iloc[0].to_dict()
    settings = EngineSettings(use_range_optimization=True, range_search_method="smart")
    cfg = settings.model_copy()

    # expand ranges
    cfg.service_fee_range = [0.0, 5.0 * multiplier]
    cfg.cxa_range = [0.0, 4.0 * multiplier]
    cfg.cac_bonus_range = [0.0, 10000.0 * multiplier]
    engine_config = cfg.model_dump()

    latencies = []
    for _ in range(5):
        start = time.time()
        _run_smart_range_search(
            customer,
            inventory,
            0.20,
            engine_config,
            customer["current_monthly_payment"],
            settings.payment_delta_tiers.model_dump(),
        )
        latencies.append(time.time() - start)

    latencies.sort()
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    print(f"p95 {p95:.2f}s p99 {p99:.2f}s")


if __name__ == "__main__":
    import sys

    mult = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_test(mult)
