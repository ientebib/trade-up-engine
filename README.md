# Kavak Trade-Up Engine

This project contains the backend services and frontend UI for the Kavak Trade-Up Engine, a tool for calculating optimal trade-up offers for customers.

## Overview

The system is built with FastAPI and provides a web interface for running simulations, configuring engine parameters, and viewing results.

## Key Features

- **Offer Generation**: Calculates trade-up offers based on customer data and vehicle inventory.
- **Financial Projections**: Includes NPV, profit, and payment schedule calculations.
- **Configurable Engine**: Tune engine parameters like fees and subsidies through a web UI.
- **Scenario Analysis**: Run batch analyses to test different configurations.
- **Dual-Mode Operation**: Supports both a `development` mode (with mock data) and a `production` mode (with live data).

## Getting Started

### Installation

The project uses a simple shell script to manage setup and execution. To prepare the environment (install dependencies into a virtual environment), run:

```bash
./run_local.sh setup
```

### Running the Application

The application can be run in two modes: `dev` and `prod`.

- **Development**: Uses local CSV files for data and disables external network calls. This is the default mode.
  ```bash
  ./run_local.sh
  ```

- **Production**: Connects to live data sources like Redshift.
  ```bash
  ./run_local.sh prod
  ```

For detailed instructions on server modes, configuration, and troubleshooting, please see the **[Execution Guide](EXECUTION_GUIDE.md)**.

## Project Structure

- `app/`: Contains the FastAPI web application, including API routes, static files (CSS, JS), and HTML templates.
- `core/`: Houses the main business logic for the trade-up engine, including the calculator, data loaders, and configuration management.
- `data/`: Holds local data files, such as `customer_data.csv`.
- `docs/`: Project documentation.
- `main.py`: The entry point for the production server.
- `main_dev.py`: The entry point for the development server.
- `run_local.sh`: The main script for setting up and running the application.

## Prerequisites

- Python 3.8+
- Virtual environment management tool (venv recommended)
- Node.js and npm (for frontend assets)
- Access to Redshift database (optional)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/Trade-Up-Engine.git
cd Trade-Up-Engine
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env_variables.txt .env
# Edit .env with your configuration
```

## Running the Application

1. Start the development server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

2. Access the web interface at: http://localhost:8000

## Development Mode

For development without external dependencies:

1. Set environment variables:
```bash
export DISABLE_EXTERNAL_CALLS=true
export USE_MOCK_DATA=true
```

2. Run the development version:
```bash
uvicorn main_dev:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

The engine can be configured through:
- `engine_config.json` - Core engine parameters
- `.env` - Environment variables
- Web interface at `/config`

Key configuration parameters:
- Service Fee Range: 0-5%
- CXA Range: 0-4%
- CAC Bonus Range: 0-10,000 MXN
 - GPS Installation Fee: 750 MXN
 - GPS Monthly Fee: 350 MXN
 - Max Combinations: 1,000
 - Early Stop Offers: 100
- Minimum NPV Threshold: 5,000 MXN
- See [docs/range_optimization.md](docs/range_optimization.md) for full details.

### Scenario Analysis Metrics
For an explanation of how offer counts and portfolio NPV are extrapolated from a customer sample see
[docs/scenario_metrics.md](docs/scenario_metrics.md).

## API Endpoints

- `/api/customers` - List all customers
- `/api/generate-offers` - Generate trade-up offers
- `/api/save-config` - Save engine configuration
- `/customer/{customer_id}` - View customer details

## Data Structure

- Customer IDs are VIN numbers (e.g., "TMCJ33A32GJ053451")
- Customer data is loaded from CSV (4,829 records)
- Inventory data from Redshift with local fallback
- Payment tiers: Refresh (-5% to 5%), Upgrade (5.01% to 25%), Max Upgrade (25.01% to 100%)

## Running Tests

Install required packages before executing the test suite:

```bash
pip install -r requirements.txt
```

Alternatively run the setup step of the helper script which also installs the
dependencies:

```bash
./run_local.sh setup
```

Then execute:

```bash
pytest
```
## Common Connection Failures

1. **Missing `.env` or incorrect Redshift credentials**
   - Ensure the `.env` file exists in the project root.
   - Double-check `REDSHIFT_HOST`, `REDSHIFT_USER`, `REDSHIFT_PASSWORD`, and related values.
   - Restart the application and visit `/health` to verify a successful connection.
2. **File permission issues for configuration or scenario result files**
   - Verify read/write permissions on `engine_config.json` and `scenario_results.json`.
   - Adjust permissions with `chmod` or run the server with a user that has access.
   - The `/health` endpoint will report errors if these files cannot be opened.
3. **Redis not running or unreachable**
   - Check that the Redis service is running and the `REDIS_URL` in `.env` is correct.
   - If Redis is unavailable, the system falls back to in-memory caching.
   - Use `/health` to confirm whether Redis connectivity is active.


## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]

## Support

For support, please open an issue in the GitHub repository. 