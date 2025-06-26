# Trade-Up Engine API Documentation

## Overview

The Trade-Up Engine API provides intelligent vehicle upgrade recommendations for Kavak customers by analyzing their current loans and matching them with available inventory.

**Base URL**: `https://api.tradeup.kavak.com`  
**API Version**: `v1`  
**Documentation**: Available at `/docs` (Swagger) and `/redoc` (ReDoc)

## Authentication

All API requests require authentication using an API key in the header:

```bash
Authorization: Bearer YOUR_API_KEY
```

## Core Endpoints

### 1. Generate Offers

#### Basic Offer Generation
```http
POST /api/generate-offers-basic
```

Generates all viable trade-up offers for a single customer.

**Request Body:**
```json
{
  "customer_id": "TMCJ33A32GJ053451"
}
```

**Response:**
```json
{
  "offers": {
    "refresh": [
      {
        "car_id": "123456",
        "customer_id": "TMCJ33A32GJ053451",
        "make": "Toyota",
        "model": "Corolla 2023",
        "car_price": 450000,
        "new_monthly_payment": 8500,
        "current_monthly_payment": 8200,
        "payment_delta": 0.037,
        "payment_delta_amount": 300,
        "loan_amount": 315000,
        "term": 48,
        "interest_rate": 0.2099,
        "npv": 25000,
        "tier": "refresh"
      }
    ],
    "upgrade": [...],
    "max_upgrade": [...]
  },
  "customer": {
    "customer_id": "TMCJ33A32GJ053451",
    "name": "Juan Pérez",
    "current_monthly_payment": 8200,
    "vehicle_equity": 120000,
    "outstanding_balance": 180000
  },
  "stats": {
    "total_evaluated": 4500,
    "total_viable": 150
  }
}
```

#### Custom Configuration Offers
```http
POST /api/generate-offers-custom
```

Generates offers with custom financial parameters.

**Request Body:**
```json
{
  "customer_id": "TMCJ33A32GJ053451",
  "service_fee_pct": 3.5,
  "cxa_pct": 3.5,
  "kavak_total_amount": 25000,
  "cac_bonus": 5000,
  "gps_monthly_fee": 350,
  "gps_installation_fee": 750
}
```

#### Bulk Offer Generation
```http
POST /api/generate-offers-bulk
```

Processes multiple customers concurrently.

**Request Body:**
```json
{
  "customer_ids": ["CUST001", "CUST002", "CUST003"],
  "max_offers_per_customer": 10
}
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Processing 3 customers",
  "progress": {
    "total": 3,
    "completed": 0,
    "failed": 0
  }
}
```

### 2. Customer Operations

#### Search Customers
```http
GET /api/customers?search=juan&risk=A1&limit=20&page=1
```

**Query Parameters:**
- `search`: Search term for customer name or ID
- `risk`: Filter by risk profile
- `sort`: Sort by field (name, payment, equity, balance)
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 20, max: 100)

**Response:**
```json
{
  "customers": [...],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

### 3. Amortization Tables

#### Generate Amortization Schedule
```http
POST /api/amortization
```

Creates detailed payment schedule for an offer.

**Request Body:**
```json
{
  "loan_amount": 350000,
  "term": 48,
  "interest_rate": 0.2099,
  "service_fee_amount": 14000,
  "kavak_total_amount": 25000,
  "insurance_amount": 10999,
  "gps_monthly_fee": 350
}
```

### 4. Configuration Management

#### Get Current Configuration
```http
GET /api/config
```

Returns all configurable parameters.

#### Update Configuration
```http
PUT /api/config
```

Updates system configuration (requires admin).

### 5. Cache Management

#### Cache Status
```http
GET /api/cache/status
```

Shows cache statistics and health.

#### Invalidate Cache
```http
POST /api/cache/invalidate/pattern
```

**Request Body:**
```json
{
  "pattern": "offers_*"
}
```

### 6. Health & Monitoring

#### Health Check
```http
GET /api/health
```

Returns system health with dependency status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-30T10:30:00Z",
  "dependencies": {
    "database": "healthy",
    "cache": "healthy",
    "circuit_breaker": "closed"
  },
  "stats": {
    "connection_pool": {
      "active": 2,
      "available": 8,
      "total": 10
    }
  }
}
```

#### Metrics
```http
GET /api/metrics
```

Returns performance metrics and statistics.

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "CUSTOMER_NOT_FOUND",
  "message": "Customer not found: CUST999",
  "details": {
    "customer_id": "CUST999"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `CUSTOMER_NOT_FOUND` | 404 | Customer ID does not exist |
| `NO_VIABLE_OFFERS` | 404 | No offers meet criteria |
| `INVALID_INPUT` | 400 | Request validation failed |
| `BULK_REQUEST_LIMIT` | 429 | Too many customers in bulk request |
| `DATABASE_CONNECTION_FAILED` | 503 | Database unavailable |
| `CIRCUIT_BREAKER_OPEN` | 503 | Service temporarily disabled |
| `REQUEST_TIMEOUT` | 504 | Request exceeded time limit |

## Rate Limits

| Endpoint Type | Limit | Window |
|--------------|-------|---------|
| Standard | 100 req/min | Per IP |
| Bulk Operations | 10 req/min | Per IP |
| Health/Metrics | Unlimited | - |

## Best Practices

### 1. Pagination
Always use pagination for list endpoints:
```bash
GET /api/customers?page=1&limit=50
```

### 2. Bulk Processing
For multiple customers, use bulk endpoints:
```bash
# Good: Single bulk request
POST /api/generate-offers-bulk
{"customer_ids": ["C1", "C2", "C3"]}

# Bad: Multiple individual requests
POST /api/generate-offers-basic {"customer_id": "C1"}
POST /api/generate-offers-basic {"customer_id": "C2"}
POST /api/generate-offers-basic {"customer_id": "C3"}
```

### 3. Cache Usage
Monitor cache hit rates and invalidate strategically:
```bash
# Check cache status
GET /api/cache/status

# Invalidate specific patterns
POST /api/cache/invalidate/pattern
{"pattern": "customer_CUST001_*"}
```

### 4. Error Handling
Always check for specific error codes:
```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
except requests.HTTPError as e:
    error_data = e.response.json()
    if error_data['error'] == 'CUSTOMER_NOT_FOUND':
        # Handle missing customer
    elif error_data['error'] == 'DATABASE_CONNECTION_FAILED':
        # Retry after delay
```

## SDK Examples

### Python
```python
from tradeup_sdk import TradeUpClient

client = TradeUpClient(api_key="YOUR_KEY")

# Generate offers
offers = client.generate_offers(
    customer_id="TMCJ33A32GJ053451",
    custom_config={
        "service_fee_pct": 3.5,
        "kavak_total_amount": 25000
    }
)

# Search customers
customers = client.search_customers(
    search="juan",
    risk_profile="A1",
    limit=10
)
```

### JavaScript
```javascript
const TradeUpAPI = require('tradeup-api');
const client = new TradeUpAPI({ apiKey: 'YOUR_KEY' });

// Generate offers
const offers = await client.generateOffers({
  customerId: 'TMCJ33A32GJ053451'
});

// Bulk processing
const bulkResult = await client.generateOffersBulk({
  customerIds: ['C1', 'C2', 'C3'],
  maxOffersPerCustomer: 10
});
```

## Changelog

### v2.0.0 (December 2024)
- Added API versioning with v1 prefix
- Implemented connection pooling
- Added circuit breaker pattern
- Enhanced error handling
- Added comprehensive metrics
- Improved bulk processing

### v1.0.0 (November 2024)
- Initial release
- Basic offer generation
- Customer search
- Configuration management