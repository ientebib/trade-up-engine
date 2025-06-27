"""
Vehicle domain model
"""
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class VehicleClass(str, Enum):
    """Vehicle classification"""
    SEDAN = "Sedan"
    SUV = "SUV"
    HATCHBACK = "Hatchback"
    PICKUP = "Pickup"
    MINIVAN = "Minivan"
    COUPE = "Coupe"
    CONVERTIBLE = "Convertible"
    WAGON = "Wagon"
    VAN = "Van"
    OTHER = "Other"


class VehicleStatus(str, Enum):
    """Vehicle availability status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


@dataclass
class Vehicle:
    """
    Vehicle domain model representing an available car in inventory
    
    This model encapsulates all vehicle-related data and business rules,
    providing a strongly-typed alternative to dictionary-based vehicles.
    """
    car_id: str
    brand: str
    model: str
    year: int
    price: Decimal
    sales_price: Decimal
    kilometers: int
    region: str
    color: str
    vehicle_class: VehicleClass
    
    # Optional fields
    status: VehicleStatus = VehicleStatus.AVAILABLE
    vin: Optional[str] = None
    plate: Optional[str] = None
    features: List[str] = None
    photos: List[str] = None
    promotion_price: Optional[Decimal] = None
    has_promotion: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate and convert types after initialization"""
        # Ensure decimals
        self.price = Decimal(str(self.price))
        self.sales_price = Decimal(str(self.sales_price))
        
        if self.promotion_price is not None:
            self.promotion_price = Decimal(str(self.promotion_price))
        
        # Initialize lists if None
        if self.features is None:
            self.features = []
        if self.photos is None:
            self.photos = []
        
        # Validate vehicle class
        if isinstance(self.vehicle_class, str):
            try:
                self.vehicle_class = VehicleClass(self.vehicle_class)
            except ValueError:
                self.vehicle_class = VehicleClass.OTHER
        
        # Validate status
        if isinstance(self.status, str):
            try:
                self.status = VehicleStatus(self.status)
            except ValueError:
                self.status = VehicleStatus.AVAILABLE
        
        # Validate year
        current_year = datetime.now().year
        if not 1900 <= self.year <= current_year + 1:
            raise ValueError(f"Invalid vehicle year: {self.year}")
        
        # Validate kilometers
        if self.kilometers < 0:
            raise ValueError(f"Invalid kilometers: {self.kilometers}")
    
    @property
    def effective_price(self) -> Decimal:
        """Get the effective price (considering promotions)"""
        if self.has_promotion and self.promotion_price:
            return self.promotion_price
        return self.sales_price
    
    @property
    def age_years(self) -> int:
        """Calculate vehicle age in years"""
        return datetime.now().year - self.year
    
    @property
    def is_new(self) -> bool:
        """Check if vehicle is considered new (0 km or current/next year)"""
        current_year = datetime.now().year
        return self.kilometers == 0 or self.year >= current_year
    
    @property
    def is_available(self) -> bool:
        """Check if vehicle is available for sale"""
        return self.status == VehicleStatus.AVAILABLE
    
    def price_difference_from(self, other_price: Decimal) -> Decimal:
        """Calculate price difference from another price"""
        return self.effective_price - other_price
    
    def is_more_expensive_than(self, other_price: Decimal) -> bool:
        """Check if this vehicle is more expensive than a given price"""
        return self.effective_price > other_price
    
    def matches_criteria(self, 
                        min_price: Optional[Decimal] = None,
                        max_price: Optional[Decimal] = None,
                        brands: Optional[List[str]] = None,
                        min_year: Optional[int] = None,
                        max_year: Optional[int] = None,
                        max_km: Optional[int] = None,
                        regions: Optional[List[str]] = None,
                        vehicle_classes: Optional[List[VehicleClass]] = None) -> bool:
        """Check if vehicle matches search criteria"""
        if min_price and self.effective_price < min_price:
            return False
        if max_price and self.effective_price > max_price:
            return False
        if brands and self.brand not in brands:
            return False
        if min_year and self.year < min_year:
            return False
        if max_year and self.year > max_year:
            return False
        if max_km and self.kilometers > max_km:
            return False
        if regions and self.region not in regions:
            return False
        if vehicle_classes and self.vehicle_class not in vehicle_classes:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return {
            "car_id": self.car_id,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "car_price": float(self.price),
            "sales_price": float(self.sales_price),
            "price": float(self.price),  # Alias for compatibility
            "km": self.kilometers,
            "kilometers": self.kilometers,  # Alias
            "region": self.region,
            "color": self.color,
            "vehicle_class": self.vehicle_class.value,
            "status": self.status.value,
            "vin": self.vin,
            "plate": self.plate,
            "features": self.features,
            "photos": self.photos,
            "promotion_price": float(self.promotion_price) if self.promotion_price else None,
            "has_promotion": self.has_promotion,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vehicle":
        """Create Vehicle from dictionary (for migration)"""
        # Handle different key names
        kilometers = data.get("km", data.get("kilometers", 0))
        car_price = data.get("car_price", data.get("price", 0))
        sales_price = data.get("sales_price", car_price)
        
        return cls(
            car_id=str(data["car_id"]),
            brand=data.get("brand", "Unknown"),
            model=data.get("model", "Unknown"),
            year=data.get("year", datetime.now().year),
            price=car_price,
            sales_price=sales_price,
            kilometers=kilometers,
            region=data.get("region", "Unknown"),
            color=data.get("color", "Unknown"),
            vehicle_class=data.get("vehicle_class", "Other"),
            status=data.get("status", "available"),
            vin=data.get("vin"),
            plate=data.get("plate"),
            features=data.get("features", []),
            photos=data.get("photos", []),
            promotion_price=data.get("promotion_price"),
            has_promotion=data.get("has_promotion", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )