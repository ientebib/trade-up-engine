# Trade-Up Engine Execution Guide

This guide provides instructions for running the Trade-Up Engine in its different modes.

## 1. Environment Setup

Before running the application for the first time, you need to set up the Python environment and install the required dependencies.

```bash
# This script creates a virtual environment in ./venv 
# and installs all packages from requirements.txt
./run_local.sh setup
```

## 2. Running the Development Server

The development server is designed for local testing and agent-based environments. It uses mock data from CSV files and disables all external network calls (e.g., to Redshift).

To start the development server:

```bash
# This is the default mode
./run_local.sh
```

Or explicitly:

```bash
./run_local.sh dev
```

The server will be available at `http://localhost:8000`. It will automatically reload when code changes are detected.

## 3. Running the Production Server

The production server is designed to run with live data, connecting to external services like Redshift as configured in your environment.

To start the production server:

```bash
./run_local.sh prod
```

The server will be available at `http://localhost:8000`. It will also hot-reload on code changes.

### Production Configuration

The production server uses environment variables for configuration. You can place these in a `.env` file in the project root. The `run_local.sh` script will automatically load it.

Example `.env` file:
```
# .env
REDSHIFT_USER=your_user
REDSHIFT_PASSWORD=your_password
# ... other credentials
```

## 4. Troubleshooting

### "Address already in use" Error

If you see an error like `[Errno 48] Address already in use`, it means another process is already running on port 8000.

To fix this, find and stop the existing process. On macOS or Linux:

```bash
# Find the Process ID (PID) using port 8000
lsof -t -i:8000

# Kill the process (replace <PID> with the number from the command above)
kill -9 <PID>
```

A faster way is to combine the commands:

```bash
lsof -t -i:8000 | xargs kill -9
```

After stopping the old process, try starting the server again. 