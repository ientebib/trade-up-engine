import time
import numpy as np
from core.data_loader_dev import DevelopmentDataLoader
from core.engine import _run_smart_range_search
from core.settings import EngineSettings
import logging

logger = logging.getLogger(__name__)

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

    # Warm-up runs
    for _ in range(3):
        try:
            _run_smart_range_search(
                customer,
                inventory,
                0.20,
                engine_config,
                customer["current_monthly_payment"],
                settings.payment_delta_tiers.model_dump(),
            )
        except Exception as e:
            logger.warning("Warm-up run failed: %s", e)

    latencies = []
    for _ in range(15):
        start = time.time()
        try:
            _run_smart_range_search(
                customer,
                inventory,
                0.20,
                engine_config,
                customer["current_monthly_payment"],
                settings.payment_delta_tiers.model_dump(),
            )
            latencies.append(time.time() - start)
        except Exception as e:
            logger.error("Test iteration failed: %s", e, exc_info=True)

    if not latencies:
        print("All test iterations failed.")
        return

    latencies.sort()
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    print(f"p95 {p95:.2f}s p99 {p99:.2f}s")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        try:
            mult = int(sys.argv[1])
            if mult <= 0:
                print("Error: Multiplier must be a positive integer.", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print("Error: Invalid multiplier. Please provide an integer.", file=sys.stderr)
            sys.exit(1)
    else:
        mult = 10

    run_test(mult)
