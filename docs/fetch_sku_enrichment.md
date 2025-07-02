# Monthly SKU Enrichment Workflow

This document explains **how to refresh the `SKU` column** in
`data/customers_data_tradeup.csv` by pulling the latest SKU for every
`STOCK ID` from Redshift.

---
## 1. Purpose
Our customer CSV does **not** store the SKU that uniquely identifies each
vehicle in the catalog.  The helper script
`scripts/fetch_inventory_by_stock_ids.py` cross-references every `STOCK ID`
with `serving.inventory_history_temp` and writes the result back into the
CSV.

The process is lightweight and meant to be executed **about once per month**
(or whenever marketing/data asks for a fresh cut).

---
## 2. Prerequisites
1. A working Redshift connection.
   Either export the following variables **or** place them in a project-root
   `.env` file (the script automatically loads it):

   ```env
   REDSHIFT_HOST=******
   REDSHIFT_DATABASE=******
   REDSHIFT_USER=******
   REDSHIFT_PASSWORD=******
   # Optional – defaults to 5439
   # REDSHIFT_PORT=5439
   ```
2. Python dependencies (already in `requirements.txt`):
   - `pandas`
   - `python-dotenv`
   - `redshift-connector`

---
## 3. Running the job manually
From the repository root:

```bash
# Ensure virtualenv is active
source venv/bin/activate

# Run the helper (uses ~5–10 s with 5k IDs)
PYTHONPATH=$PWD python3 scripts/fetch_inventory_by_stock_ids.py
```

The script will:
1. Read every unique `STOCK ID` from `data/customers_data_tradeup.csv`.
2. Fetch **exactly one** row per ID — the newest record (`updated_at_utc`)
   — from `serving.inventory_history_temp`.
3. Generate two files:

   | File | Description |
   |------|-------------|
   | `stock_id_sku_mapping.csv` | Raw two-column mapping (`stock_id,sku`). |
   | `data/customers_data_tradeup_with_sku.csv` | Original CSV **plus** a new `SKU` column. |

4. Backup the previous CSV (if you choose) and replace it:

```bash
mv data/customers_data_tradeup.csv \
   data/customers_data_tradeup_$(date +%Y-%m-%d).bak
mv data/customers_data_tradeup_with_sku.csv \
   data/customers_data_tradeup.csv
```

> **Tip**  Keep the backup for diffing in case of audit questions.

---
## 4. Automating (optional)
If you'd like the file refreshed on a schedule, create a cron job or CI step:

```cron
0 2 1 * * cd /path/to/Trade-Up-Engine \
        && PYTHONPATH=$PWD /usr/bin/python3 scripts/fetch_inventory_by_stock_ids.py
```

*Runs at 02:00 on the 1st of every month.*

---
## 5. Customisation
* **Inventory table:**
  Change `INVENTORY_TABLE` at the top of the script if the table name ever
  moves.
* **Latest flag:**
  The script first looks for `is_latest`, then `last_date`; otherwise it uses
  a window-function over `updated_at_utc` (detected dynamically).
* **Batch size:**
  Set `IN_BATCH_SIZE` env-var if you run into Redshift
  `Query size exceeded` errors (900 is safe for most clusters).

---
## 6. Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `ConnectionCreationError: Incomplete Redshift configuration` | Missing env vars | Verify `.env` or export the vars. |
| "No matching rows found" warning | `STOCK ID` not in inventory | Data mismatch; confirm the ID exists in Redshift. |
| Script hangs at *Inventory columns detected…* | Redshift slow / query queue full | Re-run later or lower `IN_BATCH_SIZE`. |

---
*Last updated: 2025-07-02* 