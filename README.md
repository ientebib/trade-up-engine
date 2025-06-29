# Trade-Up Engine

Vehicle trade-up offer calculator for Kavak Mexico. Finds cars customers can upgrade to with similar monthly payments.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL/Redshift credentials
- 4GB RAM minimum

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd trade-up-engine
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.lock  # Install pinned dependencies

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run locally
./run_local.sh
# Visit http://localhost:8000
```

### Docker
```bash
docker-compose up
```

## Project Structure
```
app/
├── api/        # REST endpoints
├── services/   # Business logic
├── domain/     # Type-safe models
└── routes/     # Web pages

engine/         # Financial calculations
data/           # Database access
config/         # Configuration system
tests/          # Test suite
```

## Core Features

- **Offer Generation**: Calculates trade-up offers based on customer financial profile
- **Smart Matching**: Two-stage filtering for performance (4000+ cars → ~500)
- **Risk-Based Pricing**: Interest rates by customer risk profile (A1-Z)
- **Mexican Regulations**: IVA tax on interest, GPS tracking requirements
- **Real-time Calculations**: No pre-computed data, always fresh

## API Examples

### Generate Offers
```bash
curl -X POST http://localhost:8000/api/generate-offers-basic \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "CUST123"}'
```

### Get Customer
```bash
curl http://localhost:8000/api/customers/CUST123
```

### Search Customers
```bash
curl -X POST http://localhost:8000/api/search/customers \
  -H "Content-Type: application/json" \
  -d '{"query": "John", "limit": 20}'
```

## Configuration

All config through facade:
```python
from config.facade import get, set

# Read config
rate = get("rates.A1")  # "0.21"

# Change config (persists to JSON)
set("fees.gps.monthly", "400")
```

See `config/schema.py` for all available settings.

## Testing

```bash
# Install exact versions
pip install -r requirements.lock

# All tests
./run_tests.py

# Specific types
./run_tests.py unit
./run_tests.py integration
./run_tests.py coverage

# Specific test
./run_tests.py tests/unit/engine/test_calculator.py
```

## Development

### For AI Assistants
See [CLAUDE.md](CLAUDE.md) for comprehensive development guide.

### Key Commands
```bash
# Format code
black . --line-length 100

# Type check
mypy app/

# Lint
flake8 app/

# Run specific module
python -m app.services.offer_service
```

### Architecture Principles
1. **No Global State** - Query on demand
2. **Service Layer** - Business logic in services/
3. **Domain Models** - Use types, not dicts
4. **Config Facade** - Single source of truth
5. **Two-Stage Filter** - Database pre-filter for performance

## Environment Variables

Required:
- `REDSHIFT_HOST` - Database host
- `REDSHIFT_DATABASE` - Database name
- `REDSHIFT_USER` - Username
- `REDSHIFT_PASSWORD` - Password

Optional:
- `USE_MOCK_DATA=true` - Use mock data instead of database
- `LOG_LEVEL=INFO` - Logging level
- `CACHE_ENABLED=false` - Disable caching

## Performance

- First request: ~2s (cache warming)
- Cached requests: <50ms
- Handles 1000+ concurrent users
- 4-hour cache TTL for inventory

## Troubleshooting

### Common Issues

**422 Error**: Car ID must be string, not integer

**Customer Not Found**: Check customer exists in database

**Slow Performance**: Check cache status at `/api/cache/status`

**Wrong Calculations**: Verify IVA is applied as `* (1 + 0.16)` not `* 0.16`

## License

Proprietary - Kavak Global Holding

## Support

For issues, check logs in `server.log` or contact the development team.