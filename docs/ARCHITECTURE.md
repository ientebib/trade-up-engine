# Architecture Overview

## System Design

Trade-Up Engine follows a **service-oriented architecture** with clear separation of concerns:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Services   │────▶│  Database   │────▶│   Engine    │
│   Routes    │     │   Layer     │     │   Layer     │     │    Layer    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     ↓                    ↓                    ↓                    ↓
   HTTP I/O         Business Logic      Data Access         Calculations
```

## Key Principles

### 1. No Global State
- All data queried on-demand
- No dataframes loaded at startup
- Supports horizontal scaling

### 2. Service Layer Pattern
- Business logic in `app/services/`
- Routes are thin controllers
- Services orchestrate operations

### 3. Two-Stage Filtering
- Database pre-filters (4000→500 cars)
- Engine applies business rules
- 85-92% performance improvement

### 4. Smart Caching
- 4-hour TTL for inventory
- Customer data always fresh
- Cache invalidation APIs

## Core Components

### API Layer (`app/api/`)
- RESTful endpoints
- Request validation
- Response formatting
- Error handling

### Service Layer (`app/services/`)
- `offer_service.py` - Offer generation logic
- `customer_service.py` - Customer operations
- `search_service.py` - Search functionality
- `config_service.py` - Configuration management

### Data Layer (`data/`)
- `database.py` - Query functions (no ORM)
- `cache_manager.py` - TTL-based caching
- `connection_pool.py` - Connection management
- `circuit_breaker.py` - Fault tolerance

### Engine Layer (`engine/`)
- `basic_matcher.py` - Core matching algorithm
- `calculator.py` - Financial calculations
- `payment_utils.py` - Payment formulas
- `smart_search.py` - Advanced search

### Configuration (`config/`)
- `schema.py` - Configuration schema (source of truth)
- `facade.py` - Configuration access API
- `registry.py` - Multi-source loader
- `engine_config.json` - Runtime overrides

## Data Flow

### Offer Generation Flow
```
1. API receives request with customer_id
2. Service layer fetches customer data
3. Database queries eligible inventory (pre-filtered)
4. Engine calculates offers for each vehicle
5. Service categorizes offers by payment tier
6. API returns formatted response
```

### Configuration Loading
```
Priority: Database (future) → JSON files → Environment → Defaults
```

## Performance Optimizations

### Two-Stage Filtering
```python
# Stage 1: Database (SQL)
SELECT * FROM inventory 
WHERE price > customer_current_price 
AND region = customer_region
LIMIT 500

# Stage 2: Engine (Python)
for vehicle in pre_filtered:
    calculate_offer(customer, vehicle)
```

### Parallel Processing
- ThreadPoolExecutor for offer calculations
- CPU count based thread pool
- Futures processed as completed

### Memory Management
- Stream processing for large datasets
- No global dataframe storage
- Garbage collection after batch operations

## Security Considerations

- Input sanitization middleware
- SQL injection prevention
- No credentials in code
- Request ID tracking
- Rate limiting

## Scalability

### Horizontal Scaling
- Stateless application
- Database connection pooling
- Shared cache (Redis ready)
- Load balancer compatible

### Vertical Scaling
- Configurable thread pools
- Adjustable cache sizes
- Database query optimization
- Memory-efficient algorithms

## Monitoring

### Health Checks
- `/api/health` - Basic health
- `/api/health/detailed` - Dependencies
- Circuit breaker status
- Cache hit rates

### Metrics
- Request duration
- Cache performance
- Database query time
- Offer generation stats

## Future Enhancements

1. **Event-Driven Architecture**
   - Async offer generation
   - Event sourcing for audit

2. **Microservices Split**
   - Separate calculation service
   - Independent search service

3. **Advanced Caching**
   - Redis integration
   - Distributed cache

4. **Real-time Updates**
   - WebSocket support
   - Live inventory updates