# API Reference

## Quick Reference

Base URL: `http://localhost:8000`

### Core Endpoints

#### Generate Offers
```bash
POST /api/generate-offers-basic
{
  "customer_id": "CUST123",
  "max_offers": 10
}
```

#### Get Customer
```bash
GET /api/customers/{customer_id}
```

#### Search Customers
```bash
POST /api/search/customers
{
  "query": "search term",
  "limit": 20
}
```

#### Cache Management
```bash
GET /api/cache/status
POST /api/cache/refresh
POST /api/cache/toggle?enabled=false
```

#### Health Check
```bash
GET /api/health
```

## Full Documentation

For complete API documentation with all endpoints, request/response schemas, and examples:

1. Start the server: `./run_local.sh`
2. Visit: http://localhost:8000/docs (Swagger UI)
3. Or visit: http://localhost:8000/redoc (ReDoc)

## Common Response Codes

- `200` - Success
- `404` - Customer/Resource not found
- `422` - Invalid request data (check types)
- `500` - Server error (check logs)

## Authentication

Currently no authentication required for development. Production uses API keys.

## Rate Limits

- Standard endpoints: 100 requests/minute
- Bulk endpoints: 10 requests/minute
- Health checks: No limit