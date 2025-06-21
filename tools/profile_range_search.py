import cProfile
import pstats
from core.data_loader_dev import DevelopmentDataLoader
from core.engine import _run_range_optimization_search
from core.settings import EngineSettings

INTEREST_RATE = 0.20  # Constant for customer interest rate

def profile(mode: str = "exhaustive", force_refresh: bool = False):
    dl = DevelopmentDataLoader()
    customers = dl.load_customers(force_refresh=force_refresh)
    if customers.empty:
        print("Error: No customers found.")
        return
    inventory = dl.load_inventory(force_refresh=force_refresh)
    customer = customers.iloc[0].to_dict()
    settings = EngineSettings(use_range_optimization=True, range_search_method=mode)
    engine_config = settings.model_dump()

    def target():
        _run_range_optimization_search(
            customer,
            inventory,
            INTEREST_RATE,
            engine_config,
            customer["current_monthly_payment"],
            settings.payment_delta_tiers.model_dump(),
        )

    profiler = cProfile.Profile()
    profiler.enable()
    target()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(10)


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "exhaustive"
    profile(mode)
