# API Documentation

## Base URL

Development: `http://localhost:8000`
Production: `https://your-domain.com`

## Authentication

Currently, the API does not require authentication. This should be implemented before production deployment.

## Endpoints

### Health Check

```http
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-06-24T12:00:00Z",
  "data_source": "redshift",
  "customers_loaded": 4829,
  "inventory_loaded": 4112
}
```

### Customers

#### List Customers

```http
GET /api/customers?page=1&limit=20&search=juan
```

Query Parameters:
- `page` (int, optional): Page number, default 1
- `limit` (int, optional): Items per page, default 20, max 100
- `search` (string, optional): Search by customer ID or name

Response:
```json
{
  "customers": [
    {
      "customer_id": "TMCJ33A32GJ053451",
      "customer_name": "Juan Pérez",
      "current_monthly_payment": 5332.0,
      "vehicle_equity": 244896.0,
      "risk_profile": "A1",
      "months_on_book": 24
    }
  ],
  "total": 4829,
  "page": 1,
  "pages": 242
}
```

#### Get Customer Detail

```http
GET /api/customers/{customer_id}
```

Response:
```json
{
  "customer_id": "TMCJ33A32GJ053451",
  "customer_name": "Juan Pérez",
  "current_monthly_payment": 5332.0,
  "vehicle_equity": 244896.0,
  "outstanding_balance": 125000.0,
  "risk_profile": "A1",
  "months_on_book": 24,
  "current_car_value": 254999.0,
  "current_car_model": "Nissan Sentra 2020"
}
```

### Offer Generation

#### Generate Basic Offers

```http
POST /api/generate-offers-basic
```

Request Body:
```json
{
  "customer_id": "TMCJ33A32GJ053451",
  "max_offers": 50
}
```

Response:
```json
{
  "success": true,
  "offers": {
    "refresh": [
      {
        "car_id": "123456",
        "make": "Nissan",
        "model": "Versa",
        "year": 2021,
        "monthly_payment": 5150.0,
        "payment_delta_pct": -0.034,
        "total_financed": 195000.0,
        "npv": 45000.0
      }
    ],
    "upgrade": [...],
    "max_upgrade": [...]
  },
  "summary": {
    "total_offers": 150,
    "refresh_count": 50,
    "upgrade_count": 60,
    "max_upgrade_count": 40
  }
}
```

#### Generate Custom Offers

```http
POST /api/generate-offers-custom
```

Request Body:
```json
{
  "customer_id": "TMCJ33A32GJ053451",
  "kavak_total_enabled": true,
  "service_fee_pct": 0.04,
  "cxa_pct": 0.04,
  "cac_bonus": 5000,
  "gps_monthly_fee": 350,
  "gps_installation_fee": 750,
  "insurance_amount": 10999,
  "term_months": 72,
  "max_offers": 50
}
```

### Amortization Table

```http
POST /api/amortization-table
```

Request Body:
```json
{
  "loan_amount": 195000.0,
  "interest_rate": 0.225,
  "term_months": 72,
  "service_fee": 7800.0,
  "kavak_total": 25000.0,
  "insurance_amount": 10999.0,
  "gps_monthly_fee": 350.0,
  "gps_installation_fee": 750.0
}
```

Response:
```json
{
  "schedule": [
    {
      "month": 1,
      "beginning_balance": 238799.0,
      "payment": 5150.0,
      "principal": 2579.40,
      "interest": 1906.45,
      "cargos": 350.0,
      "iva": 361.03,
      "ending_balance": 236219.60
    }
  ],
  "summary": {
    "total_payments": 370800.0,
    "total_interest": 132001.0,
    "total_principal": 238799.0,
    "effective_rate": 0.261
  }
}
```

### Configuration

#### Get Configuration

```http
GET /api/config
```

Response:
```json
{
  "service_fee_pct": 0.04,
  "cxa_pct": 0.04,
  "cac_bonus": 0,
  "kavak_total_enabled": true,
  "kavak_total_amount": 25000,
  "gps_monthly_fee": 350,
  "gps_installation_fee": 750,
  "insurance_amount": 10999,
  "payment_tiers": {
    "refresh": [-0.05, 0.05],
    "upgrade": [0.05, 0.25],
    "max_upgrade": [0.25, 1.0]
  }
}
```

#### Update Configuration

```http
POST /api/config
```

Request Body:
```json
{
  "service_fee_pct": 0.045,
  "cxa_pct": 0.035,
  "cac_bonus": 10000
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Customer not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "error_id": 123456789
}
```

## Rate Limiting

Currently not implemented. Should be added before production deployment.

## Webhooks

Not currently supported.

## WebSocket

Not currently supported. Real-time updates use Server-Sent Events (SSE) on specific endpoints.