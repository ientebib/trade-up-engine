# Trade-Up Engine

A sophisticated trade-up calculation engine for automotive customer upgrades with web interface.

## Overview

The Trade-Up Engine is a FastAPI-based application that calculates optimal trade-up offers for automotive customers. It features:

- Real-time customer data processing (4,829 customers supported)
- Fallback inventory system with 5 default vehicles
- Configurable fee structures and optimization parameters
- Web interface for customer management and offer generation
- Redshift integration capability (with local fallback)

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