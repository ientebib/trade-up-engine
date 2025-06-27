# Trade-Up Engine

A sophisticated financial calculation engine for automotive trade-up opportunities with a modern web interface.

## 🚀 Features

- **Real-time Offer Generation**: Calculate optimal trade-up opportunities for customers
- **Redshift Integration**: Direct connection to production data warehouse
- **Mexican Loan Calculations**: Accurate amortization with IVA (16% tax) handling
- **Configurable Business Rules**: Adjust fees, rates, and tiers through the UI
- **Modern Web Interface**: Clean, responsive design with real-time updates
- **Performance Optimized**: Parallel processing for fast offer generation

## 📋 Prerequisites

- Python 3.8 or higher
- Access to Redshift database
- Virtual environment tool (venv recommended)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/trade-up-engine.git
cd trade-up-engine
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Redshift credentials:
```
REDSHIFT_HOST=your-redshift-host.amazonaws.com
REDSHIFT_DATABASE=prod
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password
REDSHIFT_PORT=5439
```

## 🚀 Running the Application

### Development Mode

```bash
./run_local.sh
```

Or manually:

```bash
source venv/bin/activate
export PYTHONPATH=$PWD
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at: http://localhost:8000

### Mock Data Mode (GitHub Codespaces)

For testing without Redshift access (e.g., in GitHub Codespaces):

```bash
./run_codespaces.sh
```

This will:
- Enable mock data mode with 50 test customers and 100 inventory cars
- Skip Redshift connection requirements
- Create a `.env` file with mock settings
- Run the application with hot-reload enabled

You can also manually enable mock mode:

```bash
export USE_MOCK_DATA=true
./run_local.sh
```

### Production Mode

```bash
export ENVIRONMENT=production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📁 Project Structure

```
trade-up-engine/
├── app/                    # FastAPI application
│   ├── api/               # API endpoints
│   ├── routes/            # Web page routes
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JS, images
├── engine/                # Core business logic
│   ├── basic_matcher.py   # Offer matching algorithm
│   ├── calculator.py      # Financial calculations
│   └── payment_utils.py   # Payment helpers
├── config/                # Configuration
│   └── config.py         # Business rules & rates
├── data/                  # Data management
│   └── loader.py         # Redshift data loader
└── tests/                 # Test suite
```

## 🧪 Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=engine --cov=app
```

## 🔧 Configuration

### Business Rules

Edit `config/config.py` to adjust:
- Interest rates by risk profile
- Down payment percentages
- Service fees and charges
- Payment tier thresholds

### Runtime Configuration

Use the web interface at `/config` to adjust:
- Service fee percentage
- CXA percentage
- CAC bonus
- Kavak Total toggle
- GPS fees
- Insurance amounts

## 📊 API Documentation

### Key Endpoints

- `GET /api/health` - Health check
- `GET /api/customers` - List customers
- `POST /api/generate-offers-basic` - Generate offers for a customer
- `POST /api/amortization-table` - Get detailed amortization schedule
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration

### Interactive API Docs

Visit http://localhost:8000/docs for interactive API documentation.

## 🔒 Security

- Never commit `.env` files
- Use environment variables for sensitive data
- Redshift credentials are encrypted in transit
- All financial calculations happen server-side

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   export PYTHONPATH=$PWD
   ```

2. **Redshift Connection Failed**
   - Verify credentials in `.env`
   - Check network connectivity
   - Ensure Redshift security group allows your IP

3. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests to ensure nothing broke
4. Submit a pull request

## 📝 License

Proprietary - Kavak Global Holding

## 🆘 Support

For issues or questions:
- Check existing GitHub issues
- Contact the development team
- Review logs in `server.log`
