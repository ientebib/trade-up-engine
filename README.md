# 🚗 Kavak Trade-Up Engine Dashboard

A comprehensive web-based dashboard for analyzing vehicle trade-up opportunities and generating personalized offers for customers.

## 🏗️ Project Structure

```
Trade-Up-Engine/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── README.md                 # This file
├── core/                     # Core business logic
│   ├── engine.py            # Main trade-up engine
│   ├── calculator.py        # Financial calculations
│   ├── config.py           # Configuration constants
│   └── test_complete_system.py # System tests
├── app/                     # Web application
│   ├── templates/          # HTML templates
│   │   ├── main_dashboard.html
│   │   ├── customer_view.html
│   │   └── global_config.html
│   └── static/            # Static assets
│       ├── css/style.css  # Styling
│       └── js/main.js     # JavaScript functionality
├── customer_data.csv        # Customer dataset
├── inventory_data.csv       # Vehicle dataset
├── data/ (optional)        # Alternate location for data files
├── docs/                   # Documentation
│   ├── project-charter.md
│   └── fee_configuration_review.md
└── venv/                   # Virtual environment
```

## ✨ Features

### 📊 Main Dashboard
- **Portfolio Overview**: 30,000-foot view with key performance indicators
- **Interactive Charts**: Tier distribution and top performing vehicles
- **Real-time Metrics**: Live data from 150+ customers and 350+ vehicles
- **Beautiful Visualizations**: Chart.js powered interactive charts

### 👤 Customer Deep Dive
- **Individual Analysis**: Detailed customer profiles and financial data
- **Dynamic Selection**: Dropdown to browse all customers
- **Real-time Offer Generation**: Generate personalized offers on-demand
- **Tier-based Results**: Organized by Refresh, Upgrade, and Max Upgrade tiers
- **Interactive Cards**: Hover effects and detailed financial breakdowns

### ⚙️ Global Configuration
- **Scenario Analysis**: "What if" testing for business rule changes
- **Interactive Controls**: Sliders, toggles, and form inputs
- **Impact Comparison**: Before/after metrics visualization
- **Portfolio-wide Simulation**: Test configuration changes across all customers

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Virtual environment (recommended)

### Installation

1. **Clone and setup**:
```bash
cd Trade-Up-Engine
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Start the dashboard**:
```bash
python main.py
```

4. **Open your browser**:
Navigate to `http://localhost:8000`

## 📱 Usage

### Main Dashboard
- View portfolio-wide KPIs and metrics
- Explore tier distribution charts
- Analyze top performing vehicles

### Customer Analysis
1. Click "Customer Deep Dive" in the sidebar
2. Select any customer from the dropdown (1001-1150)
3. Click "🔄 Generate Offers" to see personalized results
4. Browse offers organized by tier with detailed financial data

### Configuration Testing
1. Navigate to "Global Config"
2. Adjust engine parameters using the form controls
3. Click "🧪 Run Scenario Analysis"
4. Review the impact comparison metrics

## 🔧 Technical Details

### Backend
- **FastAPI**: Modern, fast web framework
- **Pandas**: Data manipulation and analysis
- **NumPy Financial**: Financial calculations
- **SciPy**: Optimization algorithms
- **Jinja2**: Template rendering

### Frontend
- **Pure HTML/CSS/JavaScript**: No framework dependencies
- **Chart.js**: Interactive data visualizations
- **Modern CSS**: Responsive design with CSS Grid/Flexbox
- **Inter Font**: Clean, professional typography

### Data
- **150 Customers**: Realistic risk profiles and financial data
- **350 Vehicles**: 4 categories with market-appropriate pricing
- **Risk Profiles**: AAA through E1 with realistic distributions
- **Current Car Models**: Upgrade path visualization

## 🎯 API Endpoints

### Web Pages
- `GET /` - Main dashboard
- `GET /customer/{id}` - Customer analysis page
- `GET /config` - Configuration page

### API Endpoints
- `GET /api/customers` - List all customers
- `GET /api/inventory` - List all vehicles
- `POST /api/generate-offers` - Generate offers for a customer
- `POST /api/scenario-analysis` - Run configuration impact analysis

## 🧪 Testing

Run the comprehensive system test:
```bash
python core/test_complete_system.py
```

This validates:
- All web pages load correctly
- API endpoints function properly
- Data integration works
- Offer generation operates as expected

## 📊 Data Schema

### Customer Data
- `customer_id`: Unique identifier
- `current_monthly_payment`: Current loan payment
- `vehicle_equity`: Current vehicle value minus outstanding loan
- `current_car_price`: Market value of current vehicle
- `current_car_model`: Make/model for upgrade path visualization
- `risk_profile_name`: Credit risk category (AAA, A1, A2, B1, B2, C1, C2, D1, E1)
- `risk_profile_index`: Numeric risk index

### Inventory Data
- `car_id`: Unique vehicle identifier
- `model`: Vehicle make and model with year
- `sales_price`: Market price

## 🎨 Design Philosophy

The dashboard prioritizes:
- **Clean, Modern Aesthetics**: Professional appearance suitable for business use
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **User Experience**: Intuitive navigation and clear information hierarchy
- **Performance**: Fast loading and smooth interactions
- **Accessibility**: Proper contrast ratios and semantic HTML

## 🔄 Development

### Adding New Features
1. Core logic goes in `core/`
2. Web templates in `app/templates/`
3. Styling in `app/static/css/`
4. JavaScript in `app/static/js/`

### Data Updates
- Replace `customer_data.csv`, `inventory_data.csv`, and other CSVs in the repository root (or in a `data/` folder if you move them)
- Ensure column names match expected schema
- Restart the application to reload data

## 📝 License

This project is part of the Kavak Trade-Up Engine system.

---

**Built with ❤️ for automotive finance innovation** 
