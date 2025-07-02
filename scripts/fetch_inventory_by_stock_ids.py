import os
import sys
import logging
from dotenv import load_dotenv, find_dotenv
from typing import List

import pandas as pd

# Load environment variables from .env at project root BEFORE we touch the Redshift pool
load_dotenv(find_dotenv())

# Re-use the shared connection pool helper that already contains
# retry logic, circuit-breaker support, etc.
from data.connection_pool import get_connection_pool

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CUSTOMER_CSV_PATH = os.getenv("CUSTOMER_CSV_PATH", "data/customers_data_tradeup.csv")
# Size of each IN-list batch to stay well under Redshift's parameter limit.
BATCH_SIZE = int(os.getenv("IN_BATCH_SIZE", 900))

OUTPUT_PATH = os.getenv("OUTPUT_PATH", "stock_id_sku_mapping.csv")

# Column to filter on in the inventory table (change if needed)
INVENTORY_TABLE = "serving.inventory_history_temp"
STOCK_ID_COLUMN = "stock_id"
SKU_COLUMN = "sku"
# Column that marks the latest record.  Update to real column name if differs.
LATEST_FLAG_COLUMN = "is_latest"  # Fallback to "last_date" later in script


def read_stock_ids(csv_path: str) -> List[int]:
    """Read unique stock IDs from the customer CSV."""
    logger.info(f"🔍 Reading stock IDs from {csv_path} …")
    df = pd.read_csv(csv_path, usecols=["STOCK ID"], encoding="utf-8-sig")
    stock_ids = (
        df["STOCK ID"].dropna().astype(int).unique().tolist()
    )
    logger.info(f"✅ Found {len(stock_ids):,} unique stock IDs in CSV")
    return stock_ids


def chunk(lst: List[int], size: int):
    """Yield successive *size*-sized chunks from *lst*."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def fetch_inventory_for_ids(stock_ids: List[int]) -> pd.DataFrame:
    """Fetch sku for each stock id from Redshift in batches."""
    pool = get_connection_pool()
    all_rows = []
    latest_flag_column = LATEST_FLAG_COLUMN

    with pool.get_connection() as conn:
        with conn.cursor() as cur:
            # Discover column names in inventory table once
            cur.execute(
                """
                SELECT column_name
                FROM   information_schema.columns
                WHERE  table_schema = split_part(%s, '.', 1)
                  AND  table_name   = split_part(%s, '.', 2)
                """,
                (INVENTORY_TABLE, INVENTORY_TABLE),
            )
            cols = {row[0] for row in cur.fetchall()}

            has_latest_flag = False
            if latest_flag_column in cols:
                has_latest_flag = True
            elif "last_date" in cols:
                latest_flag_column = "last_date"
                has_latest_flag = True

            logger.info(
                f"Inventory columns detected. Using {'flag ' + latest_flag_column if has_latest_flag else 'window-function over updated_at_utc'} strategy"
            )

            # Ensure updated_at_utc exists for window-function; fallback to created_at if needed
            date_col = "updated_at_utc" if "updated_at_utc" in cols else None
            if not has_latest_flag and not date_col:
                raise RuntimeError(
                    "Neither latest flag column nor updated_at_utc found in inventory table. Cannot determine latest record."
                )

            for batch_num, id_batch in enumerate(chunk(stock_ids, BATCH_SIZE), start=1):
                placeholders = ",".join(["%s"] * len(id_batch))

                if has_latest_flag:
                    # Simple filter on boolean flag
                    query = (
                        f"SELECT {STOCK_ID_COLUMN}, {SKU_COLUMN} "
                        f"FROM {INVENTORY_TABLE} "
                        f"WHERE {STOCK_ID_COLUMN} IN ({placeholders}) "
                        f"  AND {latest_flag_column} = true"
                    )
                    params = id_batch
                else:
                    # Window-function to pick newest row per stock_id
                    query = (
                        f"SELECT {STOCK_ID_COLUMN}, {SKU_COLUMN} \n"
                        f"FROM (\n"
                        f"    SELECT {STOCK_ID_COLUMN}, {SKU_COLUMN},\n"
                        f"           ROW_NUMBER() OVER (PARTITION BY {STOCK_ID_COLUMN} ORDER BY {date_col} DESC) AS rn\n"
                        f"    FROM {INVENTORY_TABLE}\n"
                        f"    WHERE {STOCK_ID_COLUMN} IN ({placeholders})\n"
                        f") t\n"
                        f"WHERE rn = 1"
                    )
                    params = id_batch

                logger.debug(
                    f"Batch {batch_num}: Executing query with {len(id_batch)} IDs"
                )
                cur.execute(query, params)
                batch_rows = cur.fetchall()
                all_rows.extend(batch_rows)

    if not all_rows:
        logger.warning("⚠️ No matching rows found in inventory table.")
        return pd.DataFrame(columns=["stock_id", "sku"])

    df = pd.DataFrame(all_rows, columns=["stock_id", "sku"])
    logger.info(f"✅ Retrieved {len(df):,} inventory rows from Redshift")
    return df


def main():
    stock_ids = read_stock_ids(CUSTOMER_CSV_PATH)
    if not stock_ids:
        logger.error("❌ No stock IDs found – aborting.")
        sys.exit(1)

    inventory_df = fetch_inventory_for_ids(stock_ids)
    if inventory_df.empty:
        logger.info("No output generated – inventory query returned zero rows.")
        sys.exit(0)

    # Merge with customers CSV
    logger.info("🔀 Merging SKU mapping back into customer CSV …")
    customers_df = pd.read_csv(CUSTOMER_CSV_PATH, encoding="utf-8-sig")

    # Ensure comparable dtypes
    customers_df["STOCK ID"] = customers_df["STOCK ID"].astype(int)
    inventory_df["stock_id"] = inventory_df["stock_id"].astype(int)

    merged = customers_df.merge(
        inventory_df.rename(columns={"stock_id": "STOCK ID", "sku": "SKU"}),
        on="STOCK ID",
        how="left",
    )

    mapping_path = OUTPUT_PATH  # raw mapping file
    merged_path = os.path.splitext(CUSTOMER_CSV_PATH)[0] + "_with_sku.csv"

    inventory_df.to_csv(mapping_path, index=False)
    merged.to_csv(merged_path, index=False, encoding="utf-8-sig")

    logger.info(f"📦 Saved SKU mapping → {mapping_path}")
    logger.info(f"📦 Saved merged customers CSV → {merged_path}")


if __name__ == "__main__":
    main() 