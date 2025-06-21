import cProfile
import pstats
from core.data_loader_dev import DevelopmentDataLoader
from core.engine import _run_range_optimization_search
from core.settings import EngineSettings


def profile(mode: str = "exhaustive"):
    dl = DevelopmentDataLoader()
    customers = dl.load_customers(force_refresh=True)
    inventory = dl.load_inventory(force_refresh=True)
    customer = customers.iloc[0].to_dict()
    settings = EngineSettings(use_range_optimization=True, range_search_method=mode)
    engine_config = settings.model_dump()

    def target():
        _run_range_optimization_search(
            customer,
            inventory,
            0.20,
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
