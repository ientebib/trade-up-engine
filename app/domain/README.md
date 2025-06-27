# Domain Models Usage Guide

## Overview

The domain models provide strongly-typed, validated representations of core business concepts, replacing the error-prone dictionary-based approach.

## Benefits

1. **Type Safety**: Catch errors at development time, not runtime
2. **Validation**: Business rules enforced automatically
3. **IntelliSense**: Better IDE support with auto-completion
4. **Documentation**: Self-documenting code with clear field types
5. **Refactoring**: Easier to rename fields or change structure

## Core Models

### Customer
Represents a Kavak customer with their current vehicle and financial information.

```python
from app.domain.customer import Customer, CurrentVehicle, RiskProfile

# Create a customer
current_vehicle = CurrentVehicle(
    price=Decimal('250000'),
    brand="Toyota",
    model="Corolla",
    year=2020,
    outstanding_balance=Decimal('150000'),
    equity=Decimal('100000')
)

customer = Customer(
    customer_id="CUST123",
    current_monthly_payment=Decimal('15000'),
    vehicle_equity=Decimal('100000'),
    risk_profile=RiskProfile.A1,
    risk_profile_index=3,
    current_vehicle=current_vehicle,
    region="CDMX"
)

# Use computed properties
print(f"Loan to value: {customer.loan_to_value}")
print(f"Eligible: {customer.is_eligible_for_tradeup}")
print(f"Risk score: {customer.calculate_risk_score()}")
```

### Vehicle
Represents an available vehicle in inventory.

```python
from app.domain.vehicle import Vehicle, VehicleClass, VehicleStatus

vehicle = Vehicle(
    car_id="VEH456",
    brand="Toyota",
    model="Camry",
    year=2022,
    price=Decimal('350000'),
    sales_price=Decimal('350000'),
    kilometers=15000,
    region="CDMX",
    color="Silver",
    vehicle_class=VehicleClass.SEDAN
)

# Check availability
if vehicle.is_available and vehicle.is_more_expensive_than(customer.current_vehicle.price):
    print(f"Vehicle available for upgrade: {vehicle.brand} {vehicle.model}")

# Search criteria matching
if vehicle.matches_criteria(
    min_price=Decimal('300000'),
    max_price=Decimal('400000'),
    brands=["Toyota", "Honda"],
    max_km=20000
):
    print("Vehicle matches search criteria")
```

### Offer
Represents a complete trade-up offer.

```python
from app.domain.offer import Offer, LoanTerms, PaymentDetails, OfferTier

# Create from calculation result
offer = Offer.from_calculation_result(
    customer=customer,
    vehicle=vehicle,
    calculation={
        "term": 48,
        "interest_rate": 0.21,
        "monthly_payment": 16500.0,
        "payment_delta": 0.10,
        "loan_amount": 250000.0,
        "effective_equity": 100000.0,
        "cxa_amount": 14000.0,
        "service_fee_amount": 14000.0,
        "npv": 26000.0,
        # ... other fields
    }
)

# Check offer viability
if offer.is_viable and offer.tier == OfferTier.UPGRADE:
    print(f"Viable upgrade offer: +{offer.payment_increase_amount} MXN/month")
```

## Migration Strategy

### Phase 1: Parallel Usage (Current)
Use migration helpers to work with both formats:

```python
from app.domain.migration import migrate_customer, legacy_format

# Accept both formats
def process_customer(customer_data):
    # Convert to domain model if needed
    customer = migrate_customer(customer_data)
    
    # Work with domain model
    if customer.is_eligible_for_tradeup:
        # ... process
        pass
    
    # Convert back to dict if needed for legacy code
    return legacy_format(customer)
```

### Phase 2: Decorator-Based Migration
Use decorators for automatic conversion:

```python
from app.domain.migration import accepts_domain_models, returns_legacy_format

@accepts_domain_models
def calculate_offer(customer: Customer, vehicle: Vehicle) -> Offer:
    # Function always receives domain models
    if not customer.is_eligible_for_tradeup:
        return None
    
    # ... calculate offer
    return offer

# Can be called with either format
calculate_offer(customer_dict, vehicle_dict)  # Dicts converted automatically
calculate_offer(customer_obj, vehicle_obj)    # Domain models passed through
```

### Phase 3: Full Migration
Eventually remove dictionary usage entirely:

```python
# Future state - only domain models
def generate_offers(customer: Customer, inventory: List[Vehicle]) -> List[Offer]:
    eligible_vehicles = [
        v for v in inventory 
        if v.is_more_expensive_than(customer.current_vehicle.price)
    ]
    
    offers = []
    for vehicle in eligible_vehicles:
        offer = calculate_offer(customer, vehicle)
        if offer and offer.is_viable:
            offers.append(offer)
    
    return offers
```

## Best Practices

1. **Always validate at boundaries**: When receiving data from APIs or databases, convert to domain models immediately
2. **Use type hints**: Always specify domain model types in function signatures
3. **Leverage computed properties**: Use model methods instead of calculating in business logic
4. **Handle conversion errors**: Use try/except when converting from dictionaries
5. **Test with domain models**: Write new tests using domain models, not dictionaries

## Common Patterns

### Repository Pattern
```python
class CustomerRepository:
    def get_by_id(self, customer_id: str) -> Customer:
        # Fetch from database
        data = database.get_customer_by_id(customer_id)
        # Return domain model
        return Customer.from_dict(data)
    
    def save(self, customer: Customer) -> None:
        # Convert to dict for database
        data = customer.to_dict()
        database.save_customer(data)
```

### Service Layer
```python
class OfferService:
    def generate_offers(self, customer: Customer) -> List[Offer]:
        # Work entirely with domain models
        inventory = self.vehicle_repo.get_eligible_vehicles(customer)
        offers = []
        
        for vehicle in inventory:
            if vehicle.is_available:
                offer = self.calculate_offer(customer, vehicle)
                if offer.is_viable:
                    offers.append(offer)
        
        return offers
```

### API Layer
```python
@router.post("/offers")
def create_offers(request: OfferRequest) -> Dict:
    # Convert request to domain model
    customer = customer_service.get_customer(request.customer_id)
    
    # Generate offers using domain models
    offers = offer_service.generate_offers(customer)
    
    # Convert to API response format
    return {
        "offers": [offer.to_dict() for offer in offers],
        "count": len(offers)
    }
```

## Testing

Domain models make testing much cleaner:

```python
def test_customer_eligibility():
    # Create test data with clear intent
    customer = Customer(
        customer_id="TEST123",
        current_monthly_payment=Decimal('10000'),
        vehicle_equity=Decimal('-5000'),  # Negative equity
        risk_profile=RiskProfile.C3,
        risk_profile_index=8,
        current_vehicle=CurrentVehicle(
            price=Decimal('200000'),
            outstanding_balance=Decimal('205000'),
            equity=Decimal('-5000'),
            # ... other fields
        ),
        region="CDMX"
    )
    
    # Test business rules
    assert not customer.is_eligible_for_tradeup
    assert customer.loan_to_value > Decimal('1.0')
    assert customer.calculate_risk_score() > 80
```

## Troubleshooting

### Common Issues

1. **Decimal vs Float**: Always use Decimal for money
```python
# Wrong
price = 100.50  # Float

# Right
price = Decimal('100.50')  # Decimal
```

2. **Missing Fields**: Handle optional fields gracefully
```python
# Safe access
vehicle_year = vehicle.year if vehicle else datetime.now().year
```

3. **Type Mismatches**: Use migration helpers
```python
# Ensure correct type
customer = migrate_customer(unknown_data)
```