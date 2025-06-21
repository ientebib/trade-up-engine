# System Architecture

This repository contains a FastAPI server (`main.py`) that loads data via `DataLoader` and exposes HTTP endpoints under `app/`.  Engine logic lives in `core/` and includes calculations and settings.  Customers and inventory data are stored in CSVs or retrieved from Redshift.  Some global variables (`customers_df`, `inventory_df`) are used to cache loaded data.

```text
[Client] -> HTTP -> [FastAPI App] -> [Engine/Calculator]
                               |-> [DataLoader] -> [CSV/Redshift]
                               |-> [Cache / Redis]
```

Areas of tight coupling include the global data loader instance in `core/data_loader.py` and global state in `main.py`.  These could be refactored into dependency-injected components.

# Threat Model

User data arrives via HTTP requests (external surface).  Data is persisted in memory and optionally in Redis.  Redshift credentials are loaded from environment variables.

```text
+--------------------+      +------------------+
|   Browser/Client   | ---> | FastAPI Endpoints |
+--------------------+      +------------------+
         ^                        |
         |                        v
   External network           Data Loader
                                |
                                v
                            Redshift DB
```

Trust zones:
- Internet-facing FastAPI server
- Internal Redis/Redshift access
- Local file storage for CSVs

Data in flight is protected via HTTPS if deployed behind a secure proxy.  Data at rest lives in CSV files and Redshift.
