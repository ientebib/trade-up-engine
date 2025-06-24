"""
Global data storage and initialization
"""
import pandas as pd
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

# Data storage
customers_df = pd.DataFrame()
inventory_df = pd.DataFrame()

# Thread pool executor
cpu_count = multiprocessing.cpu_count()
executor = ThreadPoolExecutor(max_workers=cpu_count)